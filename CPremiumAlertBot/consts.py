import os

# USD (달러 환율)
USD_PRICE = 1308.75     # 2023-03.19.

# Exchanges (거래소 이름)
UPBIT   =     'Upbit'
BINANCE =   'Binance'
BYBIT   =     'Bybit'
OKX     =       'OKX'
BITGET  =    'Bitget'

# All Exchanges (거래소 리스트)
EXCHANGE_LIST = [UPBIT, BINANCE]                        # 업비트와 바이낸스만 불러올 경우
# EXCHANGE_LIST = [UPBIT, BINANCE, BYBIT, OKX, BITGET]    # 5종 거래소 모두 불러올 경우

# API KEYS (API KEY 정보)
UPBIT_API_KEY       = os.getenv('UPBIT_API_KEY')
UPBIT_SECRET_KEY    = os.getenv('UPBIT_SECRET_KEY')

BINANCE_API_KEY     = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET_KEY  = os.getenv('BINANCE_SECRET_KEY')

BYBIT_API_KEY       = os.getenv('BYBIT_API_KEY')
BYBIT_SECRET_KEY    = os.getenv('BYBIT_SECRET_KEY')

OKX_API_KEY         = os.getenv('OKX_API_KEY')
OKX_SECRET_KEY      = os.getenv('OKX_SECRET_KEY')
OKX_PASS            = os.getenv('OKX_PASS')

BITGET_API_KEY      = os.getenv('BITGET_API_KEY')
BITGET_SECRET_KEY   = os.getenv('BITGET_SECRET_KEY')
BITGET_PASS         = os.getenv('BITGET_PASS')

# TELEGRAM (텔레그램 정보)
TELEGRAM_BOT_TOKEN          = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID            = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_MESSAGE_MAX_SIZE   = 4095  # 텔레그램 메시지 최대길이

# SOCKET (웹소켓)
SOCKET_PING_INTERVAL        = 20    # 20초
SOCKET_RETRY_TIME           = 30    # 30초
SOCKET_PING_TIMEOUT         = 30    # 30초

# DELAY (딜레이, 주기)
DOLLAR_UPDATE               = 60 * 60   # 달러 가격 업데이트 주기 (1시간)
ACCUM_TRADE_PRICE_DELAY     = 3 * 60    # 누적 거래 대금조회 최초 실행대기 (3분)
ACCUM_TRADE_PRICE_UPDATE    = 60 * 60   # 누적 거래 대금조회 업데이트 주기 (1시간)
COMPARE_PRICE_DELAY         = 5 * 60    # 가격 비교 최초 실행대기 (5분)
TIME_DIFF_CHECK_DELAY       = 30 * 60   # 바이낸스 서버와 시간비교 주기 (30분)

# ETC (누적 거래 대금)
MILLION             = 100000000     # 억 (단위)
NOTI_GAP_STANDARD   = 1.0           # 거래소간 차이가 발생할 때 알림을 보낼 기준(%)
