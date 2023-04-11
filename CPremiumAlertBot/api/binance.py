import traceback
import requests

from consts import *
import util
import asyncio
import websockets
import json
import socket
from datetime import datetime


# Docs : https://binance-docs.github.io/apidocs/spot/en/
exchange = BINANCE


def get_all_ticker():

    # requests.get 을 이용해 요청.
    res = requests.get('https://api.binance.com/api/v3/exchangeInfo')

    # 응답이 오면 응답을 json 형태로 변환
    res = res.json()

    # @miniTicker 를 붙이는 이유
    # : 웹소켓에서 데이터를 요청할 때, 페어명을 이처럼 붙여서 보내달라고 하기 때문
    return [s['symbol'].lower() + '@miniTicker' for s in res['symbols'] if 'USDT' in s['symbol']]


# 거래대금 정보를 리턴하는 함수
# 해외 거래소는 파라미터를 하나 더 받음 -> exchange_price : 거래소 별로 코인 가격을 저장하고 있을 예정
# exchange_price 파라미터가 필요한 이유? -> 해외 거래소에 상장된 코인들은 USDT로 구매 가능한 USDT 페어들을 대상으로 프리미엄을 확인
# 원 달러 가격을 exchange_price 에 저장하고 조회
def get_exchange_accum_trade_price(exchange_accum_trade_price, exchange_price):
    print(exchange + " get_exchange_accum_trade_price")

    # 'exchange_price' 에서 USD 를 키로 갖고, 딕셔너리로 'base' 라는 곳에 달러 가격을 저장
    # 만약에 달러 가격이 저장되어 있지 않다고 하면(연동되어 있지 않으면), 계산이 불가하기 때문에 0
    USD = exchange_price['USD']['base'] if 'USD' in exchange_price else 0

    # 'exchange_price' 에서 USDT 를 키로 갖고, 딕셔너리로 'base' 라는 곳에 USDT 가격을 저장
    # 만약에 달러 가격이 저장되어 있지 않다고 하면(연동되어 있지 않으면), 에러없이 계산되기 위해서 1
    USDT = exchange_price['USDT']['base'] if 'USDT' in exchange_price else 1

    # API 주소로 요청을 보내면 바이낸스에 상장된 현물의 24시간 거래누적 대금을 조회하여 'res' 에 저장
    res = requests.get('https://api.binance.com/api/v3/ticker/24hr').json()

    for i in res:
        if i['symbol'].endswith('USDT'):
            ticker = i['symbol'].split('USDT')[0]

            # ticker(코인 정보)가 아직 딕셔너리에 저장되어 있지 않다고 하면 초기화
            if ticker not in exchange_accum_trade_price:
                # ex) exchange_accum_trade_price[symbol] = {'Upbit': None, 'Binance': None, 'Bybit': None, 'OKX': None, 'Bitget': None}
                exchange_accum_trade_price[ticker] = dict.fromkeys(EXCHANGE_LIST, None)

            # 누적 거래대금(quoteVolume)에 USD(달러) 가격을 곱해주고, USD와 USDT 간의 가격의 격차를 줄이기 위하여 USDT 를 곱함
            exchange_accum_trade_price[ticker][exchange] = round(float(i['quoteVolume']) * USD * USDT / MILLION, 2)


# 소켓 연결 후, 실시간 가격까지 저장하는 함수
# exchange_price : 거래소별 가격 데이터를 저장할 딕셔너리
async def connect_websocket(exchange_price):
    while True:
        try:
            util.send_to_telegram('[{}] Creating new connection...'.format(exchange))
            util.clear_exchange_price(exchange, exchange_price)
            start_time = datetime.now()

            # Connect(연결)
            async with websockets.connect('wss://stream.binance.com:9443/ws', ping_interval=None, ping_timeout=None) as websocket:

                # 수신하고 싶은 시세 정보를 나열하는 필드(포맷)
                params_ticker = []
                tickers = get_all_ticker()

                for idx, ticker in enumerate(tickers):
                    params_ticker.append(ticker)

                    # 한꺼번에 데이터를 보내면 에러가 나기 때문에, 50개씩 나눠서 웹소켓에 요청
                    if len(params_ticker) > 50 or idx == len(tickers) - 1:
                        subscribe_fmt = {
                            'method': 'SUBSCRIBE',
                            'params': params_ticker,
                            'id': 1
                        }

                        # 데이터를 json 포맷으로 변환
                        subscribe_data = json.dumps(subscribe_fmt)

                        # Send(송신)를 통해 웹소켓 서버에서 어떤 데이터를 요청하는지 알 수 있음
                        await websocket.send(subscribe_data)
                        await asyncio.sleep(1)
                        params_ticker = []

                # Receive(수신)를 통해 데이터를 받아올 수 있음
                while True:
                    try:
                        data = await websocket.recv()
                        data = json.loads(data)

                        ticker = data['s'].replace('USDT', '') if 's' in data else None

                        if not ticker:  # ticker 가 없는 데이터의 경우 저장 불가
                            continue

                        # print(ticker, data)             # 결과 출력 테스트 (※ 프로그램을 실행할 때에는 주석처리 필수)
                        # print(ticker, exchange_price)   # 딕셔너리 출력 테스트 (※ 프로그램을 실행할 때에는 주석처리 필수)

                        if ticker not in exchange_price:  # 'exchange_price' 에 코인이 존재하지 않다면 거래소 코인 초기화
                            exchange_price[ticker] = {exchange: None}

                        exchange_price[ticker][exchange] = float(data['c']) * (exchange_price['USD']['base'] if 'USD' in exchange_price else 0) \
                                                                * (exchange_price['USDT']['base'] if 'c' in data and 'USDT' in exchange_price else 1)

                        if util.is_need_reset_socket(start_time):  # 매일 아침 9시에 소켓 재연결
                            util.send_to_telegram('[{}] Time to new connection...'.format(exchange))
                            break

                    # 만약에 에러가 발생하면 에러를 출력하고, 'SOCKET_RETRY_TIME' 만큼 대기를 했다가 break 후, 처음부터 다시 진행
                    except Exception as e:
                        print(traceback.format_exc())
                        await asyncio.sleep(SOCKET_RETRY_TIME)
                        break
                await websocket.close()
        except Exception as e:
            print(traceback.format_exc())
            await asyncio.sleep(SOCKET_RETRY_TIME)


if __name__ == '__main__':
    exchange_accum_trade_price = {}
    exchange_price = {'USD': {'base': USD_PRICE}, 'USDT': {'base': 1}}
    get_exchange_accum_trade_price(exchange_accum_trade_price, exchange_price)
    print(exchange_accum_trade_price)
