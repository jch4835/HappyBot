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
DISCORD_WEBHOOK_URL_BB = _cfg['DISCORD_WEBHOOK_URL_BB']
URL_BASE = _cfg['URL_BASE']

def send_message(msg):
    """디스코드 메세지 전송"""
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
    requests.post(DISCORD_WEBHOOK_URL, data=message)
    print(message)

def send_message_bb(msg):
    """디스코드 메세지 전송"""
    now = datetime.datetime.now()
    message = {"content": f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] {str(msg)}"}
    requests.post(DISCORD_WEBHOOK_URL_BB, data=message)
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

def get_moving_average(code="005935", days=5):
    """이동평균선 조회"""
    #[국내주식]기본시세 - 주식현재가 일자별, output : Array
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"FHKST01010400"}
    params = {
        "fid_cond_mrkt_div_code":"J",
        "fid_input_iscd":code,
        "fid_org_adj_prc":"1",
        "fid_period_div_code":"D"
    }
    res = requests.get(URL, headers=headers, params=params)
    prices = [int(item['stck_clpr']) for item in res.json()['output'][:days]]
    moving_average = sum(prices) / len(prices)
    return moving_average

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

def get_balance():
    """현금 잔고조회"""
    #[국내주식]주문/계좌 - 매수가능조회, output : Object
    PATH = "uapi/domestic-stock/v1/trading/inquire-psbl-order"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC8908R",
        "custtype":"P",
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": "005935",
        "ORD_UNPR": "65500",
        "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "Y",
        "OVRS_ICLD_YN": "Y"
    }
    res = requests.get(URL, headers=headers, params=params)
    cash = res.json()['output']['ord_psbl_cash']
    amt = res.json()['output']['nrcvb_buy_amt']  #미수없는매수금액
    send_message(f"주문 가능 현금 잔고: {cash}원({amt}원)")
    #return int(cash) 
    return int(amt) // 1.3 # 증거금 30% 반영

def get_moving_volume(code="005935", days=5):
    """거래량 이동평균선 조회"""
    #[국내주식]기본시세 - 주식현재가 일자별, output : Array
    PATH = "uapi/domestic-stock/v1/quotations/inquire-daily-price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"FHKST01010400"}
    params = {
        "fid_cond_mrkt_div_code":"J",
        "fid_input_iscd":code,
        "fid_org_adj_prc":"1",
        "fid_period_div_code":"D"
    }
    res = requests.get(URL, headers=headers, params=params)
    volumes = [int(item['acml_vol']) for item in res.json()['output'][:days]]
    moving_volume = sum(volumes) / len(volumes)
    return moving_volume

def buy(code="005935", qty="1"):
    """주식 시장가 매수"""  
    #[국내주식]주문/계좌 - 주식주문(현금), output : Array
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": code,
        "ORD_DVSN": "01",
        "ORD_QTY": str(int(qty)),
        "ORD_UNPR": "0",
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC0802U",
        "custtype":"P",
        "hashkey" : hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        send_message(f"[매수 성공]{str(res.json())}")
        return True
    else:
        send_message(f"[매수 실패]{str(res.json())}")
        return False

def sell(code="005935", qty="1"):
    """주식 시장가 매도"""
    #[국내주식]주문/계좌 - 주식주문(현금), output : Array
    PATH = "uapi/domestic-stock/v1/trading/order-cash"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "PDNO": code,
        "ORD_DVSN": "01",
        "ORD_QTY": qty,
        "ORD_UNPR": "0",
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC0801U",
        "custtype":"P",
        "hashkey" : hashkey(data)
    }
    res = requests.post(URL, headers=headers, data=json.dumps(data))
    if res.json()['rt_cd'] == '0':
        send_message(f"[매도 성공]{str(res.json())}")
        return True
    else:
        send_message(f"[매도 실패]{str(res.json())}")
        return False

def get_tday_rltv(code="005935"):
    """체결강도 조회"""
    #[국내주식]기본시세 - 주식현재가 체결, output : Array
    PATH = "uapi/domestic-stock/v1/quotations/inquire-ccnl"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"FHKST01010300"}
    params = {
    "fid_cond_mrkt_div_code":"J",
    "fid_input_iscd":code,
    }
    res = requests.get(URL, headers=headers, params=params)
    return float(res.json()['output'][0]['tday_rltv']) #당일체결강도

def get_total_rsqn(code="005935"):
    """총 매도/매수 호가 잔량 수량 조회"""
    # [국내주식]기본시세 - 주식현재가 호가/예상체결
    PATH = "uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"FHKST01010200"}
    params = {
    "fid_cond_mrkt_div_code":"J",
    "fid_input_iscd":code,
    }
    res = requests.get(URL, headers=headers, params=params)
    total_askp_rsqn = int(res.json()['output1']['total_askp_rsqn']) # 총매도호가잔량
    total_bidp_rsqn = int(res.json()['output1']['total_bidp_rsqn']) # 총매수호가잔량
    return total_askp_rsqn, total_bidp_rsqn

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

def get_prev_moving_average(code="005935", days=5):
    """직전 이동평균선 조회"""
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
    data = res.json().get('output', [])
    # 주식 현재가 정보를 얻기 위한 최소 데이터 확인
    if len(data) < days + 1:
        raise ValueError(f"{code} 데이터가 부족합니다. {days + 1}일 이상의 데이터가 필요합니다.(prev_moving_average)")
    # 직전 이동평균선 계산: [1:days+1] 범위의 종가 사용
    prices = [int(item['stck_clpr']) for item in data[1:days + 1]]
    previous_moving_average = sum(prices) / len(prices)
    return previous_moving_average

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

# 매수 기록을 파일에 저장하는 함수
def save_bought_stock_dates(bought_stock_dates):
    with open('C:\\git\\HappyBot\\Korea\\bought_stock_dates.json', 'w') as f:
        json.dump(bought_stock_dates, f, ensure_ascii=False, indent=4)

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

# 매수 기록을 업데이트하는 함수
def update_bought_stock(sym, buy_qty, buy_price):
    # 기존 매수 기록 불러오기
    bought_stock_dates = load_bought_stock_dates()
    stock_name = get_stock_name(sym)
    # 종목 코드가 이미 있는 경우
    if sym in bought_stock_dates:
        # 리스트가 비어 있지 않은 경우에만 마지막 순번을 가져옴
        if len(bought_stock_dates[sym]) > 0:
            last_record = bought_stock_dates[sym][-1]
            next_seq = last_record["SEQ"] + 1
        else:
            # 리스트가 비어 있을 경우 첫 번째 순번을 1로 설정
            next_seq = 1
    else:
        # 새로운 종목 코드인 경우 첫 번째 순번
        bought_stock_dates[sym] = []
        next_seq = 1
    # 새로운 매수 기록 추가
    new_record = {
        "SEQ": next_seq,
        "BUY_DATE": datetime.datetime.now().strftime("%Y-%m-%d"),
        "BUY_CNT": buy_qty,
        "BUY_PRICE": buy_price
    }
    bought_stock_dates[sym].append(new_record)
    # 변경된 매수 기록을 파일에 저장
    save_bought_stock_dates(bought_stock_dates)

def process_and_modify_first_record(sym):
    """
    [종목 단위 처리 함수]
    1. 수익률이 마이너스인 경우
       - next buy_date 존재 → buy_date 변경
       - 없으면 buy_date + 13 거래일
    2. 12월 8일 이후에는 buy_date 변경 금지
    """
    bought_stock_dates = load_bought_stock_dates()
    # 🔹 해당 종목이 없으면 종료
    if sym not in bought_stock_dates or not bought_stock_dates[sym]:
        return
    stock_name = get_stock_name(sym)
    records = bought_stock_dates[sym]
    # BUY_DATE 기준 정렬 (next buy_date 탐색용)
    records.sort(key=lambda r: r["BUY_DATE"])
    for idx, record in enumerate(records[:]):  # 리스트 복사본 loop
        seq = record["SEQ"]
        buy_date = datetime.datetime.strptime(
            record["BUY_DATE"], "%Y-%m-%d"
        )
        buy_price = float(record["BUY_PRICE"])
        buy_qty = record["BUY_CNT"]
        # 현재가 기준 수익률
        current_price = get_current_price(sym)
        profit_rate = (current_price - buy_price) / buy_price * 100
        days_held = count_trading_days(buy_date)
        send_message(
            f"{sym}({stock_name}) SEQ:{seq} | ({buy_qty}주)(가격:{buy_price}) |"
            f"보유 {days_held}일 | 수익률 {profit_rate:.2f}%"
        )
    #     # =====================================================
    #     # 3️⃣ 수익률 마이너스 → BUY_DATE 변경
    #     # =====================================================
    #     if profit_rate < 0 and days_held >= 13:
    #         # ❗ 12월 8일 이후 BUY_DATE 변경 금지
    #         if buy_date.month == 12 and buy_date.day >= 8:
    #             send_message(
    #                 f"{sym}({stock_name}) SEQ:{seq} | "
    #                 f"12월 8일 이후 → BUY_DATE 변경 안함"
    #             )
    #             continue
    #         # next buy_date 결정
    #         next_buy_date = None
    #         # 🔹 idx+1 부터 마지막까지 모두 탐색
    #         for next_idx in range(idx + 1, len(records)):
    #             candidate_date = datetime.datetime.strptime(
    #                 records[next_idx]["BUY_DATE"], "%Y-%m-%d"
    #             )
    #             send_message(f"Nextdate idx:{next_idx}, candidate:{candidate_date}")

    #             # 🔹 현재 buy_date보다 이후의 날짜인 경우에만 사용
    #             if candidate_date > buy_date:
    #                 next_buy_date = candidate_date
    #                 break   # 기존 구조 유지 (처음 발견되는 날짜 사용)

    #         # 이후 날짜가 없으면 13영업일 후 계산
    #         if next_buy_date is None:
    #             send_message(f"Nextdate None after full scan, idx:{idx}")
    #             next_buy_date = get_next_buy_date(buy_date, 13)

    #         send_message(
    #             f"{sym}({stock_name}) SEQ:{seq} | "
    #             f"손실 → BUY_DATE 변경 "
    #             f"{record['BUY_DATE']} → "
    #             f"{next_buy_date.strftime('%Y-%m-%d')}"
    #         )
    #         record["BUY_DATE"] = next_buy_date.strftime("%Y-%m-%d")
    # # 🔹 파일 저장
    # bought_stock_dates[sym] = records
    # save_bought_stock_dates(bought_stock_dates)

def get_next_buy_date(start_date, add_days):
    # 1. 입력받은 start_date가 문자열이면 datetime으로 변환, 이미 객체면 그대로 사용
    if isinstance(start_date, str):
        current_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    else:
        current_date = start_date
        
    # 2. 주말 제외 13일 계산
    days_added = 0
    while days_added < add_days:
        current_date += datetime.timedelta(days=1)
        if current_date.weekday() < 5:  # 월~금요일만 카운트
            days_added += 1
            
    # 3. 객체(datetime) 상태 그대로 반환 (그래야 밖에서 .strftime() 사용 가능)
    return current_date

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
                send_message_bb(f"{sym}({stock_name}) 12월 BB상단 골드크로스 매도")
                sell(sym, buy_qty)
                time.sleep(1)
                bought_stock_dates[sym].remove(record)

            # 2️⃣ 12월 말일 강제 매도
            elif is_year_end:
                send_message(f"{sym}({stock_name}) 12월말 강제 매도")
                send_message_bb(f"{sym}({stock_name}) 12월말 강제 매도")
                sell(sym, buy_qty)
                time.sleep(1)
                bought_stock_dates[sym].remove(record)

        save_bought_stock_dates(bought_stock_dates)


# 자동매매 시작
try:
    ACCESS_TOKEN = get_access_token()
    # 코스닥, 코스피 TOP 20위 중 수익률 높은 종목(5년간 300% 이상)
    symbol_list = ["465580","381180","457480","438080","438100"]
                
    symbols_set = set(symbol_list) # 중복 방지를 위한 set
    added_set = set(symbol_list) # 한 번 추가된 값을 기록하기 위한 set
    send_message("===국내 주식 BB하단돌파 자동매매 프로그램 시작===")
    send_message("-----------------------------------------------")
    total_cash = get_balance() # 보유 현금 조회
    stock_dict, buy_prices = get_stock_balance() # 보유 주식 조회 및 매수 가격 기록
    target_buy_count = 10 # 매수할 종목 수
    buy_amount = 3000000 # 종목당 매수 금액(40만원 * 1.3 * 10 = 520만원)
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
            if t_now.minute == 10 or t_now.minute == 40: 
            
                send_message(f"---------------------------")
                send_message(f"0-1. Symbol체크(매수대상): ")
                send_message(f"---------------------------")
                for sym in symbol_list:
                    #if len(stock_dict) < target_buy_count:
                    data_count = get_data_count(sym,21)
                    stock_name = get_stock_name(sym)
                    if data_count < 25:
                        continue
                    current_price = get_current_price(sym) #현재가
                    mv10 = get_moving_volume(sym, 10) #평균거래량(10일)
                    prev_close_price = get_prev_close_price(sym)
                    # ma10 = get_moving_average(sym, 10)
                    ma10_prev = get_prev_moving_average(sym, 10)
                    # ma20 = get_moving_average(sym, 20)
                    ma20_prev = get_prev_moving_average(sym, 20)
                    lower, upper, prev_lower, prev_upper = get_bollinger_band(sym)
                    
                    time.sleep(1) #휴식시간 : 매우중요
                    if prev_close_price < prev_lower and current_price > lower:
                        send_message(f"{sym}({stock_name}) BB하단 골드크로스 매수 대상. 현재가:{current_price}, prev_lower: {prev_lower}, lower: {lower}, 종가(직전): {prev_close_price}, 10일(직전):{ma10_prev}, 20일(직전):{ma20_prev}")
                        send_message_bb(f"{sym}({stock_name}) BB하단 골드크로스 매수 대상. 현재가:{current_price}, prev_lower: {prev_lower}, lower: {lower}, 종가(직전): {prev_close_price}, 10일(직전):{ma10_prev}, 20일(직전):{ma20_prev}")
                time.sleep(1) #발굴한 종목 매수 후 1초 휴식 
                
                for sym in stock_dict.keys():
                    current_price = get_current_price(sym)
                    total_askp_rsqn, total_bidp_rsqn = get_total_rsqn(sym) #총매도호가,매수호가 잔량
                    stock_name = get_stock_name(sym)
                    send_message(f"1. 보유종목: {sym}({stock_name})")
                    if sym in buy_prices:
                        buy_price = float(buy_prices[sym])
                        percentage = round((current_price / buy_price) * 100, 2)
                        if current_price >= buy_price * 1.05:  
                            send_message(f"{sym}({stock_name}) 수익실현 매도 Signal. 매수가 {buy_price}, 현재가 {current_price}({percentage}%), 총매도잔량:{total_askp_rsqn}, 총매수잔량:{total_bidp_rsqn}")
                        if current_price <= buy_price * 0.97:  
                            send_message(f"{sym}({stock_name}) 손절매도 Signal. 매수가 {buy_price}, 현재가 {current_price}({percentage}%), 총매도잔량:{total_askp_rsqn}, 총매수잔량:{total_bidp_rsqn}")    
                time.sleep(60)

            if t_now.minute == 30: 
                send_message(f"2. 주식/현금 조회: ")
                time.sleep(1) 
                stock_dict, buy_prices = get_stock_balance() # 보유주 조회 및 매수 가격 기록
                time.sleep(1) 
                total_cash = get_balance() # 보유 현금 조회
                time.sleep(60)        
        
        if t_buy < t_now < t_sell :  # PM 03:00 ~ PM 03:15 : 매수 및 손절 체크
            count_cnt += 1
            if count_cnt <= 3:
                send_message(f"3-1. 현재시간: {t_now.strftime('%Y-%m-%d %H:%M:%S')}, COUNT:{count_cnt}")
            for sym in symbol_list:
                if len(stock_dict) < target_buy_count:
                    data_count = get_data_count(sym,21)
                    stock_name = get_stock_name(sym)
                    if count_cnt <= 1:
                        send_message(f"3-2. 매수체크: {sym}({stock_name}), COUNT:{count_cnt} ")
                    if data_count < 25:
                       continue
                    current_price = get_current_price(sym) #현재가
                    mv10 = get_moving_volume(sym, 10) #평균거래량(10일)
                    prev_close_price = get_prev_close_price(sym)
                    ma10 = get_moving_average(sym, 10)
                    ma10_prev = get_prev_moving_average(sym, 10)
                    ma20 = get_moving_average(sym, 20)
                    ma20_prev = get_prev_moving_average(sym, 20)
                    lower, upper, prev_lower, prev_upper = get_bollinger_band(sym)
                    
                    time.sleep(1) #휴식시간 : 매우중요
                    if prev_close_price < prev_lower and current_price > lower:
                        if total_cash < current_price and count_cnt <= 3:
                            send_message(f"{sym}({stock_name}) 매수 금액 부족.")
                            continue
                        buy_qty = 0  # 매수할 수량 초기화
                        if total_cash < buy_amount: # 보유금액이 1종목 매수할 금액보다 적을 경우 보유금액으로 종목의 현재가를 나누어 매수할 수량을 구한다.
                            buy_amount = total_cash
                        buy_qty = int(buy_amount // current_price)
                        if buy_qty > 0:
                            send_message(f"{sym}({stock_name}) 10억이상, BB하단 골드크로스 돌파 ({buy_qty})개 매수 시도.")
                            result = buy(sym, buy_qty)
                            time.sleep(5) #매우 중요할 듯
                            if result:
                                soldout = False
                                symbol_list.remove(sym)
                                # 새로운 매수 기록 업데이트
                                update_bought_stock(sym, buy_qty, current_price)
                                stock_dict, buy_prices = get_stock_balance()
                                total_cash = get_balance() # 보유 현금 조회
                        time.sleep(1)
            time.sleep(1) #발굴한 종목 매수 후 1초 휴식  

        if t_sell < t_now < t_exit:  # PM 03:15 ~ PM 03:20 : 일괄 매도
            if soldout == False:
                stock_dict, buy_prices = get_stock_balance()
                total_cash = get_balance() # 보유 현금 조회
                time.sleep(1)
                send_message(f"4. 보유기간:")
                for sym in stock_dict.keys():
                    # 수익률 display
                    # process_and_modify_first_record(sym)
                    # 종목 매도 로직
                    process_and_sell_first_record(sym)
                soldout = True                
            time.sleep(1)

        if t_exit < t_now:  # PM 03:20 ~ :프로그램 종료
            send_message("프로그램 종료.")
            break

except IndexError as e:
    send_message(f"IndexError: {e}")
except Exception as e:
    send_message(f"[오류 발생]{e}")
    time.sleep(1)
