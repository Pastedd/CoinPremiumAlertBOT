import traceback
import pyupbit
import requests

from consts import *
import util
import asyncio
import websockets
import json
import socket
from datetime import datetime
import uuid
import pandas as pd


# Docs : https://pyupbit.readthedocs.io/en/latest/
exchange = UPBIT


# 원화(KRW) 마켓과 BTC 마켓간의 중복된 정보를 삭제하고, 하나의 리스트로 통합하여 리턴하는 함수
def get_all_ticker():

    # 원화 마켓의 코인 정보를 로드
    krw_ticker = pyupbit.get_tickers(fiat='KRW')

    # BTC 마켓의 코인 정보를 로드
    btc_ticker = pyupbit.get_tickers(fiat='BTC')

    # BTC 마켓에 있는 코인목록 중에 원화 마켓에 있는 정보를 삭제
    only_in_btc = [ticker for ticker in btc_ticker if 'KRW-' + ticker.split('-')[1] not in krw_ticker]

    # 중복없는 코인목록을 만들기 위해 원화 마켓에 있는 코인목록과 'only_in_btc' 코인목록을 합쳐서 반환
    return krw_ticker + only_in_btc


# 거래대금 정보를 리턴하는 함수
def get_exchange_accum_trade_price(exchange_accum_trade_price):
    print(exchange + " get_exchange_accum_trade_price")

    # BTC 가격 불러오기.
    btc_price = pyupbit.get_current_price('KRW-BTC')

    # 전체 누적 거래대금 조회.
    res = requests.get('https://api.upbit.com/v1/ticker', {'markets': get_all_ticker()}).json()

    for i in res:
        ticker = i['market'].split('-')[1]  # 코인 티커 (KRW-BTC 중 BTC)
        currency = i['market'].split('-')[0]  # 코인 티커 (KRW-BTC 중 KRW)

        # ticker(코인 정보)가 아직 Dictionary 에 저장되어 있지 않다고 하면 초기화
        if ticker not in exchange_accum_trade_price:
            # ex) exchange_accum_trade_price[symbol] = {'Upbit': None, 'Binance': None, 'Bybit': None, 'OKX': None, 'Bitget': None}
            exchange_accum_trade_price[ticker] = dict.fromkeys(EXCHANGE_LIST, None)

        # currency(기준 통화)가 만약에 'BTC'이면 값을 저장할 때
        if currency == 'BTC':

            # 누적 거래대금에 BTC 가격을 곱하고, 억 단위로 표현하기 위해서 나누기 억을하고 반올림
            exchange_accum_trade_price[ticker][exchange] = round(i['acc_trade_price_24h'] * btc_price / MILLION, 2)

        # currency(기준 통화)가 'BTC'가 아니면 / KRW(원화)일 때
        else:

            # 누적 거래대금에 BTC 가격을 곱하지 않음
            exchange_accum_trade_price[ticker][exchange] = round(i['acc_trade_price_24h'] / MILLION, 2)

# 웹소켓 연결 이후, 수신한 가격 데이터를 'exchange_price'에 저장하는 함수
async def connect_websocket(exchange_price):
    while True:
        try:
            util.send_to_telegram('[{}] Creating new connection...'.format(exchange))
            util.clear_exchange_price(exchange, exchange_price)
            start_time = datetime.now()

            # Connect(연결)
            async with websockets.connect('wss://api.upbit.com/websocket/v1', ping_interval=None, ping_timeout=None) as websocket:

                # 수신하고 싶은 시세 정보를 나열하는 필드(포맷)
                subscribe_fmt = [
                    {'ticket':  str(uuid.uuid4())[:6]},
                    {
                        'type': 'ticker',
                        'codes': get_all_ticker(),
                        'isOnlyRealtime': True
                    },
                ]

                # 데이터를 json 포맷으로 변환
                subscribe_data = json.dumps(subscribe_fmt)

                # Send(송신)를 통해 웹소켓 서버에서 어떤 데이터를 요청하는지 알 수 있음
                await websocket.send(subscribe_data)

                # Receive(수신)를 통해 데이터를 받아올 수 있음
                while True:
                    try:
                        data = await websocket.recv()
                        data = json.loads(data)

                        if 'code' not in data:  # 응답 데이터(딕셔너리)에 code가 없는 경우 제외
                            print('[Data error]', data)
                            continue

                        currency = data['code'].split('-')[0]   # KRW-BTC -> KRW(기준 통화)
                        ticker = data['code'].split('-')[1]     # KRW-BTC -> BTC(시세조회 대상 코인)

                        # print(ticker, data)               # 결과 출력 테스트 (※ 프로그램을 실행할 때에는 주석처리 필수)
                        # print(ticker, exchange_price)     # 딕셔너리 출력 테스트 (※ 프로그램을 실행할 때에는 주석처리 필수)

                        if ticker not in exchange_price:    # 'exchange_price' 에 코인이 존재하지 않다면 거래소 코인 초기화
                            exchange_price[ticker] = {exchange: None}

                        if currency == 'BTC':   # 기준 통화가 BTC인 경우는 "현재 가격 * BTC 가격" = 원화 환산 가격
                            if 'BTC' in exchange_price:

                                # 변수 데이터중에 'trade_price' 에 현재 가격이 있으므로 아래와 같이 저장
                                # 만약에 'exchange_price' 에 비트코인 가격이 있다면 비트코인 가격과 같이 곱해주고,
                                # 비트코인 가격이 없다고 하면, 계산을 할 수 없으므로 0을 곱해 가격을 0으로 만듬
                                exchange_price[ticker][exchange] = float(data['trade_price']) * \
                                float(exchange_price['BTC'][exchange]) if exchange_price['BTC'] and exchange in exchange_price['BTC'] else 0

                        else:   # 기준 통화가 원화인 경우, 현재 가격(trade_price) 그대로 저장
                            exchange_price[ticker][exchange] = float(data['trade_price'])

                        if util.is_need_reset_socket(start_time):   # 매일 아침 9시(지정된 시간)에 소켓 재연결
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
    get_exchange_accum_trade_price(exchange_accum_trade_price)
    print(exchange_accum_trade_price)
