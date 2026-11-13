import requests
import json
import datetime
import time
import yaml
import holidays
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np
import pandas as pd
import yfinance as yf
import FinanceDataReader as fdr

with open('C:\\git\\HappyBot\\Korea\\config.yaml', encoding='UTF-8') as f:    
    _cfg = yaml.load(f, Loader=yaml.FullLoader)
APP_KEY = _cfg['APP_KEY']
APP_SECRET = _cfg['APP_SECRET']
ACCESS_TOKEN = ""
CANO = _cfg['CANO']
ACNT_PRDT_CD = _cfg['ACNT_PRDT_CD']
DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']
URL_BASE = _cfg['URL_BASE']

def send_message(msg):
    """디스코드 메세지 전송"""
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
    requests.post(DISCORD_WEBHOOK_URL, data=message)
    print(message)

def get_access_token():
    """토큰 발급"""
    headers = {"content-type":"application/json"}
    body = {"grant_type":"client_credentials",
    "appkey":APP_KEY, 
    "appsecret":APP_SECRET}
    PATH = "oauth2/tokenP"
    URL = f"{URL_BASE}/{PATH}"
    res = requests.post(URL, headers=headers, data=json.dumps(body))
    ACCESS_TOKEN = res.json()["access_token"]
    return ACCESS_TOKEN
    
def hashkey(datas):
    """암호화"""
    PATH = "uapi/hashkey"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
    'content-Type' : 'application/json',
    'appKey' : APP_KEY,
    'appSecret' : APP_SECRET,
    }
    res = requests.post(URL, headers=headers, data=json.dumps(datas))
    hashkey = res.json()["HASH"]
    return hashkey

def get_current_price(code="005935"):
    """현재가 조회"""
    #[국내주식]기본시세 - 주식현재가 시세, output : Object
    PATH = "uapi/domestic-stock/v1/quotations/inquire-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"FHKST01010100"}
    params = {
    "fid_cond_mrkt_div_code":"J",
    "fid_input_iscd":code,
    }
    res = requests.get(URL, headers=headers, params=params)
    return int(res.json()['output']['stck_prpr'])

def get_stock_balance():
    """주식 잔고조회"""
    #[국내주식]주문/계좌 - 주식잔고조회, output1,2 : Array
    PATH = "uapi/domestic-stock/v1/trading/inquire-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC8434R",
        "custtype":"P",
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "AFHR_FLPR_YN": "N",
        "OFL_YN": "",
        "INQR_DVSN": "02",
        "UNPR_DVSN": "01",
        "FUND_STTL_ICLD_YN": "N",
        "FNCG_AMT_AUTO_RDPT_YN": "N",
        "PRCS_DVSN": "01",
        "CTX_AREA_FK100": "",
        "CTX_AREA_NK100": ""
    }
    res = requests.get(URL, headers=headers, params=params)
    stock_list = res.json()['output1']
    evaluation = res.json()['output2']
    stock_dict = {}
    buy_prices = {}
    send_message(f"====주식 보유잔고====")
    for stock in stock_list:
        if int(stock['hldg_qty']) > 0:
            stock_dict[stock['pdno']] = stock['hldg_qty']
            buy_prices[stock['pdno']] = stock['pchs_avg_pric'] # 매수 가격 기록
            send_message(f"{stock['prdt_name']}({stock['pdno']}): {stock['hldg_qty']}주({stock['pchs_avg_pric']}원)")
            time.sleep(0.1)
    send_message(f"주식 평가 금액: {evaluation[0]['scts_evlu_amt']}원")
    time.sleep(0.1)
    send_message(f"평가 손익 합계: {evaluation[0]['evlu_pfls_smtl_amt']}원")
    time.sleep(0.1)
    send_message(f"총 평가 금액: {evaluation[0]['tot_evlu_amt']}원")
    time.sleep(0.1)
    send_message(f"=================")
    return stock_dict, buy_prices

def get_bollinger_band(code="005935", period=20):
    """블린저밴드 상/하단 계산"""
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "Content-Type":"application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"FHKST01010400"
    }
    params = {
        "fid_cond_mrkt_div_code":"J",
        "fid_input_iscd":code,
        "fid_org_adj_prc":"1",
        "fid_period_div_code":"D"
    }

    res = requests.get(URL, headers=headers, params=params)
    data = res.json().get('output', [])

    if len(data) < period + 1:
        return None, None, None, None

    closes = [int(item['stck_clpr']) for item in data[:period]]
    prev_closes = [int(item['stck_clpr']) for item in data[1:period+1]]

    mean = np.mean(closes)
    std = np.std(closes)
    lower = int(mean - (2 * std))
    upper = int(mean + (2 * std))

    prev_mean = np.mean(prev_closes)
    prev_std = np.std(prev_closes)
    prev_lower = int(prev_mean - (2 * prev_std))
    prev_upper = int(prev_mean + (2 * prev_std))

    return lower, upper, prev_lower, prev_upper

def get_prev_close_price(code="005935"):
    """전일 종가 조회"""
    # 국내주식 기본시세 - 주식현재가 일자별, output : Array
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "FHKST01010400"
    }
    params = {
        "fid_cond_mrkt_div_code": "J",  # 시장 구분 코드 (J: 코스피)
        "fid_input_iscd": code,          # 주식 코드
        "fid_org_adj_prc": "1",          # 수정주가 반영
        "fid_period_div_code": "D"       # 기간 구분 코드 (D: 일별)
    }
    
    # 데이터 요청
    res = requests.get(URL, headers=headers, params=params)
    data = res.json().get('output', [])
    
    # 주식 현재가 정보를 얻기 위한 최소 데이터 확인
    if len(data) < 2:
        raise ValueError(f"{code} 데이터가 부족합니다. 최소 2일 이상의 데이터가 필요합니다. (get_prev_close_price)")
    
    # 전일 종가: 전일 데이터 (1번 인덱스)의 'stck_clpr' 필드
    prev_close_price = int(data[1]['stck_clpr'])
    
    return prev_close_price

def get_data_count(code="005935", days=5):
    """데이터 보유건수(일) 조회"""
    # 국내주식 기본시세 - 주식현재가 일자별, output : Array
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "FHKST01010400"
    }
    params = {
        "fid_cond_mrkt_div_code": "J",
        "fid_input_iscd": code,
        "fid_org_adj_prc": "1",
        "fid_period_div_code": "D"
    }
    # 데이터 요청
    res = requests.get(URL, headers=headers, params=params)
    res.raise_for_status()  # HTTP 에러 발생 시 예외 발생
    data = res.json().get('output', [])
        
    return len(data)

# 전역 캐시
_STOCK_CACHE = {}
def load_market(market):
    if market not in _STOCK_CACHE:
        print(f"[LOAD] {market} 다운로드")
        _STOCK_CACHE[market] = fdr.StockListing(market)
    return _STOCK_CACHE[market]

def get_stock_name(code):
    code = code.upper()

    # 한국
    try:
        krx = load_market('KRX')
        row = krx[krx['Code'] == code]
        if not row.empty:
            return row['Name'].values[0]
    except Exception as e:
        print(f"[WARN] KRX load error: {e}")

    # 한국 ETF
    try:
        etf = load_market('ETF/KR')
        row = etf[etf['Symbol'] == code]
        if not row.empty:
            return row['Name'].values[0]
    except Exception as e:
        print(f"[WARN] ETF/KR load error: {e}")

    # 미국
    for market in ['NASDAQ', 'NYSE', 'AMEX']:
        try:
            us = load_market(market)
            row = us[us['Symbol'] == code]
            if not row.empty:
                return row['Name'].values[0]
        except Exception as e:
            print(f"[WARN] {market} load error: {e}")
            continue

    return 'Not Found'

# 파일에서 매수 기록을 불러오는 함수
def load_bought_stock_dates():
    try:
        with open('C:\\git\\HappyBot\\Korea\\bought_stock_dates.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}
def count_trading_days(buy_date, end_date=None):
    # 공휴일 목록 정의 (예시로 몇 가지 추가, 필요 시 추가 가능)
    kr_holidays = holidays.KR()  # 한국 공휴일 자동 로드
    # 현재 날짜를 기준으로 계산할 경우
    if end_date is None:
        end_date = datetime.datetime.now()
    # 주말 제외한 영업일 목록 만들기
    total_days = pd.date_range(start=buy_date, end=end_date, freq='B')  # B는 영업일(business days)을 의미
    # 공휴일 제외하기
    trading_days = [day for day in total_days if day not in kr_holidays]
    # 영업일 수 반환
    return len(trading_days)
    
def process_and_sell_first_record(sym):

    bought_stock_dates = load_bought_stock_dates()

    if sym in bought_stock_dates and len(bought_stock_dates[sym]) > 0:

        stock_name = get_stock_name(sym)
        current_price = get_current_price(sym)
        lower, upper, prev_lower, prev_upper = get_bollinger_band(sym)

        for record in bought_stock_dates[sym][:]:

            buy_qty = record["BUY_CNT"]
            today = datetime.datetime.now()
            buy_price = float(record["BUY_PRICE"])
            seq = record["SEQ"]
            buy_date = datetime.datetime.strptime(
                record["BUY_DATE"], "%Y-%m-%d"
            )
            days_held = count_trading_days(buy_date)

            profit_rate = (current_price - buy_price) / buy_price * 100

            is_december = today.month == 12
            is_year_end = today.month == 12 and today.day >= 28

            bb_upper_cross = False
            if prev_upper is not None:
                prev_close_price = get_prev_close_price(sym)
                if prev_close_price > prev_upper and current_price < upper:
                    bb_upper_cross = True

            # 🔥 수익률이 마이너스면 매도 금지
            if profit_rate > 0:
                send_message(
                    f"{sym}({stock_name}) SEQ:{seq} | ({buy_qty}주)(가격:{buy_price}) |"
                    f"보유 {days_held}일 | 수익률 {profit_rate:.2f}%"
                )
            elif profit_rate <= 0:
                send_message(
                    f"{sym}({stock_name}) SEQ:{seq} | ({buy_qty}주)(가격:{buy_price}) |"
                    f"보유 {days_held}일 | 수익률 {profit_rate:.2f}% → 매도 보류"
                )
                continue
            
            # 1️⃣ 12월 + BB 상단 골드크로스
            if is_december and bb_upper_cross:
                send_message(f"{sym}({stock_name}) 12월 BB상단 골드크로스 매도")
                # sell(sym, buy_qty)
                time.sleep(1)
                bought_stock_dates[sym].remove(record)

            # 2️⃣ 12월 말일 강제 매도
            elif is_year_end:
                send_message(f"{sym}({stock_name}) 12월말 강제 매도")
                # sell(sym, buy_qty)
                time.sleep(1)
                bought_stock_dates[sym].remove(record)

        save_bought_stock_dates(bought_stock_dates)

# 매수 기록을 파일에 저장하는 함수
def save_bought_stock_dates(bought_stock_dates):
    with open('C:\\git\\HappyBot\\Korea\\bought_stock_dates.json', 'w') as f:
        json.dump(bought_stock_dates, f, ensure_ascii=False, indent=4)

# 자동매매 시작
try:
    ACCESS_TOKEN = get_access_token()
    # 코스닥, 코스피 TOP 20위 중 수익률 높은 종목(5년간 300% 이상)
    # symbol_list = ["465580","381180","457480","438080","438100"]
    symbol_list = ["465580","381180","457480","005930","000660"]
                
    symbols_set = set(symbol_list) # 중복 방지를 위한 set
    added_set = set(symbol_list) # 한 번 추가된 값을 기록하기 위한 set
    send_message("===국내 주식 BB하단돌파 자동알람 프로그램 시작===")
    send_message("-----------------------------------------------")
    target_buy_count = 10 # 매수할 종목 수
    soldout = False
    count_cnt = 0
      
    while True:
        # 한국의 공휴일 설정
        kr_holidays = holidays.KR()
        t_now = datetime.datetime.now()
        t_9 = t_now.replace(hour=9, minute=0, second=0, microsecond=0)
        t_start = t_now.replace(hour=9, minute=0, second=0, microsecond=0)
        t_buy = t_now.replace(hour=15, minute=0, second=0, microsecond=0)
        t_sell = t_now.replace(hour=15, minute=15, second=0, microsecond=0)
        t_exit = t_now.replace(hour=15, minute=20, second=0,microsecond=0)
        today = datetime.datetime.today().weekday()
        
        if t_now in kr_holidays:
            send_message(f"{t_now}은(는) 공휴일: {kr_holidays[t_now]} ==> 프로그램 종료.")
            break
        if today == 5 or today == 6:  # 토요일이나 일요일이면 자동 종료
            send_message("주말이므로 프로그램을 종료.")
            break

        if t_start < t_now < t_buy :  # AM 09:30 ~ PM 03:00 : 손절 체크
            if t_now.hour % 2 == 0 and t_now.minute == 10: 
            
                # send_message(f"---------------------------")
                # send_message(f"0-1. Symbol체크(매수대상): ")
                # send_message(f"---------------------------")
                for sym in symbol_list:
                    data_count = get_data_count(sym,21)
                    stock_name = get_stock_name(sym)
                    if data_count < 25:
                        continue
                    current_price = get_current_price(sym) #현재가
                    prev_close_price = get_prev_close_price(sym)
                    lower, upper, prev_lower, prev_upper = get_bollinger_band(sym)
                    
                    time.sleep(1) #휴식시간 : 매우중요
                    if prev_close_price < prev_lower and current_price > lower:
                        send_message(f"{sym}({stock_name}) BB하단 골드크로스 매수 대상. 현재가:{current_price}, prev_lower: {prev_lower}, lower: {lower}, 종가(직전): {prev_close_price}")
                    if current_price < lower and prev_close_price < prev_lower:
                        send_message(f"{sym}({stock_name}) 종가(직전) < 전일BB하단 AND 현재가 < BB하단. 현재가:{current_price}, lower: {lower}, 종가(직전): {prev_close_price}, prev_lower: {prev_lower}")
                    elif current_price < lower:
                        send_message(f"{sym}({stock_name}) 현재가 < BB하단. 현재가:{current_price}, lower: {lower}")
                time.sleep(60)

        if t_buy < t_now < t_sell :  # PM 03:00 ~ PM 03:15
            time.sleep(1)

        if t_sell < t_now < t_exit:  # PM 03:15 ~ PM 03:20
            if soldout == False:
                stock_dict, buy_prices = get_stock_balance()
                time.sleep(1)
                send_message(f"4. 보유기간:")
                for sym in stock_dict.keys():
                    # 종목 매도 로직
                    process_and_sell_first_record(sym)
                soldout = True                
            time.sleep(1)

        if t_exit < t_now:  # PM 03:20 ~ :프로그램 종료
            # send_message("프로그램 종료.")
            break

except IndexError as e:
    send_message(f"IndexError: {e}")
except Exception as e:
    send_message(f"[오류 발생]{e}")
    time.sleep(1)
