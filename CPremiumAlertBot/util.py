from consts import *
import telegram
import time
from datetime import datetime, timedelta


bot = None


# 텔레그램 봇을 통해 메시지를 전송하는 함수
def send_to_telegram(message):
    global bot
    if not bot:
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        else:
            raise Exception('TELEGRAM_PATH Undefined.')

    retries = 0
    max_retries = 3

    while retries < max_retries and bot:
        try:
            print(message)
            bot.send_message(text=message[:TELEGRAM_MESSAGE_MAX_SIZE], chat_id=TELEGRAM_CHAT_ID)
            return True

        except telegram.error.TimedOut as timeout:
            time.sleep(5 * retries)
            retries += 1
            print('Telegram got a error! retry...')

        except Exception as e:
            bot = None
            retries = max_retries

        if retries == max_retries:
            bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
            print('Telegram failed to retry...')


# 소켓 연결이 끊어진 경우, 이전까지 받아온 데이터들은 더이상 유효하지 않기 때문에 데이터를 삭제하는 역할을 하는 함수 (데이터 중복 삭제)
# 'exchange_price' 내의 데이터를 삭제
def clear_exchange_price(exchange, exchange_price):
    for ticker in exchange_price:
        if exchange in exchange_price[ticker]:
            del exchange_price[ticker][exchange]


# 매일 오전 9시(지정된 시간)인지 확인하여 시간이 넘었다면 소켓 초기화 (websocket 재연결 목적)
def is_need_reset_socket(start_time):
    now = datetime.now()
    start_date_base_time = start_time.replace(hour=9, minute=0, second=0, microsecond=0)
    next_base_time = (start_time + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)

    if start_time < start_date_base_time:
        if start_date_base_time < now:
            return True
        else:
            return

    if next_base_time < now:
        return True
    else:
        return
