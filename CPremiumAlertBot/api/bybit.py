import traceback
import requests

from consts import *
import util
import asyncio
import websockets
import json
import socket
from datetime import datetime
import time


# Docs: https://bybit-exchange.github.io/docs/account_asset/#t-coin_info_query


exchange = BYBIT


# 데이터를 수신할 TICKER 목록
def get_all_ticker():
    res = requests.get('https://api.bybit.com/spot/v1/symbols').json()
    return [item['name'] for item in res['result']]


# 누적 거래대금(단위 금액: 억) 조회 및 저장
# exchange_accum_trade_price : 거래소별 거래대금 데이터를 저장할 딕셔너리
# exchange_price : 거래소별 가격 데이터를 저장할 딕셔너리
def get_exchange_accum_trade_price(exchange_accum_trade_price, exchange_price):
    print(exchange + " get_exchange_accum_trade_price")

    USD = exchange_price['USD']['base'] if 'USD' in exchange_price else 0
    USDT = exchange_price['USDT']['base'] if 'USDT' in exchange_price else 1

    for ticker in get_all_ticker():
        res = requests.get('https://api.bybit.com/spot/quote/v1/ticker/24hr', params={'symbol': ticker}).json()
        ticker = ticker.split("USDT")[0]
        if ticker not in exchange_accum_trade_price:
            # ex) exchange_accum_trade_price[symbol] = {'Upbit': None, 'Binance': None, 'Bybit': None, 'OKX': None, 'Bitget': None}
            exchange_accum_trade_price[ticker] = dict.fromkeys(EXCHANGE_LIST, None)

        exchange_accum_trade_price[ticker][exchange] = round(float(res['result']['quoteVolume']) * USD * USDT / MILLION, 2)


# 소켓 연결 후 실시간 가격까지 저장하는 함수
# exchange_price : 거래소별 가격 데이터를 저장할 딕셔너리
async def connect_websocket(exchange_price):
    while True:
        try:
            util.send_to_telegram('[{}] Creating new connection...'.format(exchange))
            util.clear_exchange_price(exchange, exchange_price)
            start_time = datetime.now()
            ping_time = time.time()

            async with websockets.connect('wss://stream.bybit.com/spot/quote/ws/v1', ping_interval=None, ping_timeout=None) as websocket:
                for ticker in get_all_ticker():
                    subscribe_fmt = {
                        "topic": "realtimes",
                        "event": "sub",
                        "symbol": ticker,
                        "params": {
                            "binary": False
                        }
                    }

                    subscribe_data = json.dumps(subscribe_fmt)
                    await websocket.send(subscribe_data)
                await asyncio.sleep(3)
                while True:
                    try:
                        data = await websocket.recv()
                        data = json.loads(data)
                        ticker = data['symbol'].split('USDT')[0] if data and 'pong' not in data and 'desc' not in data and data['symbol'] else None

                        if not ticker:  # ticker가 없는 데이터의 경우 저장 불가
                            continue

                        if ticker not in exchange_price:
                            exchange_price[ticker] = {exchange: None}

                        # print(ticker, data)             # 결과 출력 테스트 (※ 프로그램을 실행할 때에는 주석처리 필수)
                        # print(ticker, exchange_price)   # 딕셔너리 출력 테스트 (※ 프로그램을 실행할 때에는 주석처리 필수)

                        # 해외거래소 코인의 가격은 (가격 * USD(환율) * USDT/USD)
                        exchange_price[ticker][exchange] = float(data['data'][0]['c']) * exchange_price['USD']['base'] if 'USD' in exchange_price else 0 \
                                                                * exchange_price['USDT']['base'] if 'c' in data and 'USDT' in exchange_price else 1

                        # send ping
                        time_diff = time.time() - ping_time
                        if time_diff > SOCKET_PING_INTERVAL:
                            ping_time = time.time()
                            await websocket.send(json.dumps({"ping": 1535975085052}))

                        if util.is_need_reset_socket(start_time):  # 매일 아침 9시 소켓 재연결
                            util.send_to_telegram('[{}] Time to new connection...'.format(exchange))
                            break

                    except Exception as e:
                        util.send_to_telegram('[{}] Receiving error. retrying connection'.format(exchange, SOCKET_RETRY_TIME))
                        print(traceback.format_exc())
                        await asyncio.sleep(SOCKET_RETRY_TIME)
                        break
                await websocket.close()
        except Exception as e:
            util.send_to_telegram('[{}] Retrying connection in {} sec (Ctrl-C to quit)'.format(exchange, SOCKET_RETRY_TIME))
            print(traceback.format_exc())
            await asyncio.sleep(SOCKET_RETRY_TIME)


if __name__ == "__main__":
    print(len(get_all_ticker()))
