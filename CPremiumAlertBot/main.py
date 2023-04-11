import asyncio

# 거래소 5종 모두 이용할 경우 -> , bybit, okx, bitget 추가
from api import upbit, binance

import util
import traceback
import time
import platform
import requests
import json
import os
from consts import *


class Premium:
    def __init__(self):
        self.exchange_price = {}                # 거래소별 가격 데이터를 저장할 딕셔너리
        self.exchange_accum_trade_price = {}    # 거래소별 거래대금 데이터를 저장할 딕셔너리

    # 해외 거래소의 USD/USDT 가격을 저장하는 함수
    # while 문을 통해 일정 주기를 기준으로 무한히 반복
    async def get_usd_price(self):
        while True:
            try:
                data = requests.get('https://quotation-api-cdn.dunamu.com/v1/forex/recent?codes=FRX.KRWUSD').json()
                self.exchange_price['USD'] = {'base':data[0]['basePrice']}

                # BUSD/USDT -> USDT/BUSD -> (USDT) 역수를 취함
                res = requests.get('https://api.binance.com/api/v3/ticker/price?symbol=BUSDUSDT')
                self.exchange_price['USDT'] = {'base': 1 / float(res.json()['price'])}
                await asyncio.sleep(DOLLAR_UPDATE)  # 달러 가격 업데이트 주기 (1시간)

            except Exception as e:
                util.send_to_telegram(traceback.format_exc())


    # 거래소별 코인의 누적 거래대금을 조회하여 self.exchange_accum_trade_price 에 저장하는 함수
    # while 문을 통해 일정 주기를 기준으로 무한히 반복
    async def check_exchange_accum_trade_price(self):
        while True:
            try:
                # 거래소별 connect_socket 을 통해 가져와야 할 코인 정보가 있어서 대기
                await asyncio.sleep(ACCUM_TRADE_PRICE_DELAY)

                # 1. Upbit 누적 거래대금 확인
                upbit.get_exchange_accum_trade_price(self.exchange_accum_trade_price)

                # 2. Binance 누적 거래대금 확인
                binance.get_exchange_accum_trade_price(self.exchange_accum_trade_price, self.exchange_price)

                # # 3. Bybit 누적 거래대금 확인
                # bybit.get_exchange_accum_trade_price(self.exchange_accum_trade_price, self.exchange_price)
                #
                # # 4. OKX 누적 거래대금 확인
                # okx.get_exchange_accum_trade_price(self.exchange_accum_trade_price, self.exchange_price)
                #
                # # 5. Bitget 누적 거래대금 확인
                # bitget.get_exchange_accum_trade_price(self.exchange_accum_trade_price, self.exchange_price)

                await asyncio.sleep(ACCUM_TRADE_PRICE_UPDATE)

            except Exception as e:
                util.send_to_telegram(traceback.format_exc())


    # self.exchange_price 에 저장된 거래소별 코인 정보를 비교하고 특정 수치(%)이상 격차 발생시 알림을 전달하는 함수
    async def compare_price(self):
        while True:
            try:
                await asyncio.sleep(COMPARE_PRICE_DELAY)    # 거래소별 connect_socket 을 통해 가져와야 할 코인 정보가 있어서 대기
                util.send_to_telegram('✅')
                base_message = '🔥 프리미엄 정보 🔥\n\n'
                exchange_price = self.exchange_price.copy() # 거래소에서 얻어온 가격 데이터 복사
                message_dict = {}                           # 격차 발생시 알람을 보낼 메시지를 저장해둘 딕셔너리
                message_list = ['']                         # message_dict 에 저장했던 메시지들을 보낼 순서대로 저장한 리스트

                # 버블정렬을 이용하여 데이터를 오름차 순으로 정렬하고 코인 정보를 보여주는 과정
                for key in exchange_price:
                    if key in ['USD', 'USDT']:
                        continue

                    # 거래소 목록 리스트를 생성
                    exchange_list = list(exchange_price[key])

                    # 'exchange_list[i]' = 기준 거래소명, 'base_exchange' = 가격
                    for i in range(0, len(exchange_list) - 1):
                        base_exchange = exchange_list[i]

                        # 가격 데이터가 들어있는 'exchange_price'에 코인이 키 값으로 있고, 거래소 명이 'base_exchange' 에 키 값으로 있는 형태
                        base_exchange_price = round(float(exchange_price[key][base_exchange]), 2) if float(
                            exchange_price[key][base_exchange]) > 0 else float(exchange_price[key][base_exchange])

                        if not base_exchange_price:
                            continue

                        for j in range(i + 1, len(exchange_list)):

                            # 비교 거래소의 가격, 코인의 가격을 저장
                            # 데이터를 꺼내오는 키 값이 'base_exchange' -> 'compare_exchange' 로 바뀌고, 변수명이 변경
                            compare_exchange = exchange_list[j]
                            compare_exchange_price = round(float(exchange_price[key][compare_exchange]), 2) if float(
                                exchange_price[key][compare_exchange]) > 0 else float(exchange_price[key][compare_exchange])

                            # 가격 데이터가 존재하지 않다면 비교할 수 없으므로 넘어감
                            if not compare_exchange_price:
                                continue

                            # 거래소간의 가격 차이(%)
                            diff = round((base_exchange_price - compare_exchange_price) /
                                         base_exchange_price * 100, 3) if base_exchange_price else 0

                            if abs(diff) > NOTI_GAP_STANDARD:
                                message = f'{key}, {base_exchange}_{compare_exchange} 프리미엄({diff}%)\n'
                                message += f'현재가격:{base_exchange_price:,.2f}원/{compare_exchange_price:,.2f}원\n'
                                if self.exchange_accum_trade_price[key][base_exchange] and \
                                        self.exchange_accum_trade_price[key][
                                            compare_exchange]:  # 거래대금 데이터가 있는 경우에만 알림 추가
                                    message += f'거래대금:{self.exchange_accum_trade_price[key][base_exchange]:,.2f}억원/{self.exchange_accum_trade_price[key][compare_exchange]:,.2f}억원\n'
                                message_dict[diff] = message

                # 알림을 보내기 전에 메시지를 정렬
                message_dict = dict(sorted(message_dict.items(), reverse=True))  # 메시지 격차 발생 순으로 정렬
                for i in message_dict:
                    if len(message_list[len(message_list) - 1]) + len(message_dict[i]) < TELEGRAM_MESSAGE_MAX_SIZE:
                        message_list[len(message_list) - 1] += message_dict[i] + '\n'
                    else:
                        message_list.append(message_dict[i] + '\n')

                message_list[0] = base_message + message_list[0]  # 알림 첫줄 구분용 문구 추가

                # 정렬한 메시지를 순서대로 텔레그램 알림 전송
                for message in message_list:
                    util.send_to_telegram(message)

            except Exception as e:
                util.send_to_telegram(traceback.format_exc())


    async def run(self):
        await asyncio.wait([                                                        # 태스크들을 비동기 실행하고 결과를 기다림
            asyncio.create_task(self.get_usd_price()),                              # USD(달러) 데이터 조회/저장
            asyncio.create_task(upbit.connect_websocket(self.exchange_price)),      # Upbit websocket 연결 및 가격정보 조회/저장
            asyncio.create_task(binance.connect_websocket(self.exchange_price)),    # Binance websocket 연결 및 가격정보 조회/저장
            # asyncio.create_task(bybit.connect_websocket(self.exchange_price)),      # Bybit websocket 연결 및 가격정보 조회/저장
            # asyncio.create_task(okx.connect_websocket(self.exchange_price)),        # OKX websocket 연결 및 가격정보 조회/저장
            # asyncio.create_task(bitget.connect_websocket(self.exchange_price)),     # Bitget websocket 연결 및 가격정보 조회/저장
            asyncio.create_task(self.check_exchange_accum_trade_price()),           # 누적 거래대금 조회/저장
            asyncio.create_task(self.compare_price())                               # 가격비교 알림
        ])

if __name__ == '__main__':
    premium = Premium()
    asyncio.run(premium.run())  # 비동기 함수 호출