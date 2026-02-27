import requests
import json
import datetime
import pytz
import time
import yaml
import holidays
import statistics
import pandas as pd
import FinanceDataReader as fdr
import exchange_calendars as xcals

with open('C:\\git\\HappyBot\\America\\config.yaml', encoding='UTF-8') as f:
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

def get_current_price(market="NAS", code="NVDA"):
    """현재가 조회"""
    #[해외주식]기본시세 - 해외주식 현재체결가, output : Object
    PATH = "uapi/overseas-price/v1/quotations/price"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"HHDFS00000300"}
    params = {
        "AUTH": "",
        "EXCD":market,
        "SYMB":code,
    }
    res = requests.get(URL, headers=headers, params=params)
    return float(res.json()['output']['last'])

def get_moving_average(market="NAS", code="NVDA", days=5):
    """이동평균선 조회"""
    #[해외주식]기본시세 - 해외주식 기간별시세, output2 : Object Array
    PATH = "uapi/overseas-price/v1/quotations/dailyprice"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"HHDFS76240000"}
    params = {
        "AUTH":"",
        "EXCD":market,
        "SYMB":code,
        "GUBN":"0",
        "BYMD":"",
        "MODP":"0"
    }
    res = requests.get(URL, headers=headers, params=params)
    prices = [float(item['clos']) for item in res.json()['output2'][:days]]
    moving_average = sum(prices) / len(prices)
    return moving_average

def get_stock_balance():
    """주식 잔고조회"""
    #[해외주식]주문/계좌 - 해외주식 잔고 - output1 : Array output2 : Object
    PATH = "uapi/overseas-stock/v1/trading/inquire-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"JTTT3012R",
        "custtype":"P"
    }
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "OVRS_EXCG_CD": "NASD",
        "TR_CRCY_CD": "USD",
        "CTX_AREA_FK200": "",
        "CTX_AREA_NK200": ""
    }
    res = requests.get(URL, headers=headers, params=params)
    stock_list = res.json()['output1']
    evaluation = res.json()['output2']
    stock_dict = {}
    buy_prices = {}
    send_message(f"====주식 보유잔고====")
    for stock in stock_list:
        if int(stock['ovrs_cblc_qty']) > 0:
            stock_dict[stock['ovrs_pdno']] = stock['ovrs_cblc_qty']
            buy_prices[stock['ovrs_pdno']] = stock['pchs_avg_pric'] # 매수 가격 기록
            send_message(f"{stock['ovrs_item_name']}({stock['ovrs_pdno']}): {stock['ovrs_cblc_qty']}주(${stock['pchs_avg_pric']})")
            time.sleep(0.1)
    send_message(f"주식 평가 금액: ${evaluation['tot_evlu_pfls_amt']}")
    time.sleep(0.1)
    send_message(f"평가 손익 합계: ${evaluation['ovrs_tot_pfls']}")
    time.sleep(0.1)
    send_message(f"실현 수익율: ${evaluation['rlzt_erng_rt']}")
    time.sleep(0.1)
    send_message(f"총 수익율: ${evaluation['tot_pftrt']}")
    time.sleep(0.1)
    send_message(f"=================")
    return stock_dict, buy_prices, evaluation['tot_pftrt']

def get_balance():
    """현금 잔고조회"""
    # NOT Found
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
        "PDNO": "005930",
        "ORD_UNPR": "65500",
        "ORD_DVSN": "01",
        "CMA_EVLU_AMT_ICLD_YN": "Y",
        "OVRS_ICLD_YN": "Y"
    }
    res = requests.get(URL, headers=headers, params=params)
    cash = res.json()['output']['ord_psbl_cash']
    amt = res.json()['output']['nrcvb_buy_amt']  #미수없는매수금액
    # send_message(f"주문 가능 현금 잔고: {cash}원({amt}원)")
    send_message(f"주문 가능 현금 잔고: {round(int(cash)/exchange_rate,4)}$({round(int(amt)/exchange_rate,4)}$)")
    return int(int(amt)/exchange_rate)

def buy(market="NASD", code="NVDA", qty="1", price="0"):
    """미국 주식 지정가 매수"""
    #[해외주식]주문/계좌 - 해외주식 주문 - Output : object
    PATH = "uapi/overseas-stock/v1/trading/order"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "OVRS_EXCG_CD": market,
        "PDNO": code,
        "ORD_DVSN": "00",
        "ORD_QTY": str(int(qty)),
        "OVRS_ORD_UNPR": f"{round(price,2)}",
        "ORD_SVR_DVSN_CD": "0"
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTT1002U",
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

def sell(market="NASD", code="NVDA", qty="1", price="0"):
    """미국 주식 지정가 매도"""
    #[해외주식]주문/계좌 - 해외주식 주문 - Output : object
    PATH = "uapi/overseas-stock/v1/trading/order"
    URL = f"{URL_BASE}/{PATH}"
    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "OVRS_EXCG_CD": market,
        "PDNO": code,
        "ORD_DVSN": "00",
        "ORD_QTY": str(int(qty)),
        "OVRS_ORD_UNPR": f"{round(price,2)}",
        "ORD_SVR_DVSN_CD": "0"
    }
    headers = {"Content-Type":"application/json", 
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTT1006U",
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

def get_exchange_rate():
    """환율 조회"""
    #[해외주식]주문/계좌 - 체결기준현재잔고 - output2 : array
    PATH = "uapi/overseas-stock/v1/trading/inquire-present-balance"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
            "authorization": f"Bearer {ACCESS_TOKEN}",
            "appKey":APP_KEY,
            "appSecret":APP_SECRET,
            "tr_id":"CTRP6504R"}
    params = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "OVRS_EXCG_CD": "NASD",
        "WCRC_FRCR_DVSN_CD": "01",
        "NATN_CD": "840",
        "TR_MKET_CD": "01",
        "INQR_DVSN_CD": "00"
    }
    res = requests.get(URL, headers=headers, params=params)
    exchange_rate = 1460.0
    #res.json()['output1'][0]['bass_exrt']
    if len(res.json()['output1']) > 0:
        exchange_rate = float(res.json()['output1'][0]['bass_exrt'])
    return exchange_rate

def get_prev_moving_average(market="NAS", code="NVDA", days=5):
    """직전 이동평균선 조회"""
    # [해외주식] 기본시세 - 해외주식 기간별시세, output2 : Object Array
    PATH = "uapi/overseas-price/v1/quotations/dailyprice"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "HHDFS76240000"
    }
    params = {
        "AUTH": "",
        "EXCD": market,
        "SYMB": code,
        "GUBN": "0",
        "BYMD": "",
        "MODP": "0"
    }
    res = requests.get(URL, headers=headers, params=params)
    prices = [float(item['clos']) for item in res.json()['output2']]
    if len(prices) < days + 1:
        raise ValueError(f"Not enough data to calculate {days}-day previous moving average.")
    # 직전 이동평균선: 당일을 제외한 전일의 종가 기준으로 days개를 사용
    prev_prices = prices[1:days + 1]
    prev_moving_average = sum(prev_prices) / len(prev_prices)
    return prev_moving_average

def get_previous_close_price(market="NAS", code="NVDA"):
    """전일 종가 조회"""
    # [해외주식] 기본시세 - 해외주식 기간별시세, output2 : Object Array
    PATH = "uapi/overseas-price/v1/quotations/dailyprice"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "HHDFS76240000"
    }
    params = {
        "AUTH": "",
        "EXCD": market,
        "SYMB": code,
        "GUBN": "0",  # 0: 일봉, 1: 주봉, 2: 월봉
        "BYMD": "",  # ""로 입력하면 최근 100개 일봉 데이터 조회
        "MODP": "0"  # 수정주가 반영 여부
    }
    res = requests.get(URL, headers=headers, params=params)
    if res.status_code != 200 or 'output2' not in res.json():
        raise ValueError(f"Failed to retrieve data for {code} in {market}.")
    # 전일 종가는 두 번째 항목에 있음
    previous_close = float(res.json()['output2'][1]['clos'])
    return previous_close

def get_us_daily_volume(market="NAS", code="NVDA", days=2):
    """미국 주식의 최근 `days` 일 동안의 거래량 조회 (기본: 2일 -> 오늘, 어제)"""
    PATH = "uapi/overseas-price/v1/quotations/dailyprice"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "Content-Type": "application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "HHDFS76240000"
    }
    params = {
        "AUTH": "",
        "EXCD": market,  # 시장 코드 (e.g., NAS: 나스닥, NYS: 뉴욕증권거래소)
        "SYMB": code,    # 종목 코드 (e.g., NVDA)
        "GUBN": "0",     # 0: 일봉
        "BYMD": "",      # 최근 데이터를 조회
        "MODP": "0"      # 수정주가 반영 여부
    }
    # API 요청
    res = requests.get(URL, headers=headers, params=params)
    if res.status_code != 200 or 'output2' not in res.json():
        raise ValueError(f"{market}의 {code}에 대한 데이터를 가져오지 못했습니다.")
    # 최근 거래량 데이터 추출 (오늘과 어제)
    data = res.json().get('output2', [])
    # 데이터가 충분하지 않은 경우 예외 처리
    if len(data) < days:
        raise ValueError(f"거래량 데이터를 가져오는데 실패했습니다. 최소 {days}일의 데이터가 필요합니다.")
    # 오늘의 거래량 (첫 번째 데이터)
    today_volume = float(data[0]['tvol'])
    # 어제의 거래량 (두 번째 데이터)
    yesterday_volume = float(data[1]['tvol'])
    return today_volume, yesterday_volume

def get_us_moving_volume(market="NAS", code="NVDA", days=10):
    """미국 주식의 10일 평균 거래량 조회"""
    PATH = "uapi/overseas-price/v1/quotations/dailyprice"
    URL = f"{URL_BASE}/{PATH}"
    headers = {
        "Content-Type": "application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey": APP_KEY,
        "appSecret": APP_SECRET,
        "tr_id": "HHDFS76240000"
    }
    params = {
        "AUTH": "",
        "EXCD": market,  # 시장 구분 (e.g., NAS: 나스닥)
        "SYMB": code,    # 주식 코드 (e.g., NVDA: NVIDIA)
        "GUBN": "0",     # 0: 일봉, 1: 주봉, 2: 월봉
        "BYMD": "",      # 빈칸이면 최근 데이터 조회
        "MODP": "0"      # 수정주가 반영 여부
    }
    # API 요청
    res = requests.get(URL, headers=headers, params=params)
    if res.status_code != 200 or 'output2' not in res.json():
        raise ValueError(f"{market}의 {code}에 대한 데이터를 가져오지 못했습니다.")
    # 응답에서 거래량 데이터 추출
    data = res.json().get('output2', [])
    # 데이터가 충분하지 않은 경우 예외 처리
    if len(data) < days:
        raise ValueError(f"데이터가 부족합니다. 최소 {days}일 이상의 데이터가 필요합니다.")
    # 최근 `days`일 동안의 거래량 데이터 리스트
    volumes = [float(day['tvol']) for day in data[:days]]
    # 거래량 평균 계산
    moving_volume = sum(volumes) / len(volumes)
    return moving_volume

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
        with open('C:\\git\\Happybot\\America\\bought_stock_dates.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

# 매수 기록을 파일에 저장하는 함수
def save_bought_stock_dates(bought_stock_dates):
    with open('C:\\git\\HappyBot\\America\\bought_stock_dates.json', 'w') as f:
        json.dump(bought_stock_dates, f, ensure_ascii=False, indent=4)

def count_trading_days(buy_date, end_date=None):
    # 미국 공휴일 목록 정의
    us_holidays = holidays.US()
    # 현재 날짜를 기준으로 계산할 경우
    if end_date is None:
        end_date = datetime.datetime.now()
    # 주말 제외한 영업일 목록 만들기
    total_days = pd.date_range(start=buy_date, end=end_date, freq='B')  # B는 영업일(business days)을 의미
    # 공휴일 제외하기
    trading_days = [day for day in total_days if day not in us_holidays]
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
        market1 = "NASD"
        market2 = "NAS"
        if sym in nyse_symbol_list:
            market1 = "NYSE"
            market2 = "NYS"
        if sym in amex_symbol_list:
            market1 = "AMEX"
            market2 = "AMS"
        current_price = get_current_price(market2, sym)
        profit_rate = (current_price - buy_price) / buy_price * 100
        days_held = count_trading_days(buy_date)
        send_message(
            f"{sym}({stock_name}) SEQ:{seq} | ({buy_qty}주)(가격: {buy_price}) |"
            f"보유 {days_held}일 | 수익률 {profit_rate:.2f}%"
        )
        # =====================================================
        # 3️⃣ 수익률 마이너스 → BUY_DATE 변경
        # =====================================================
        if profit_rate < 0 and days_held >= 13:
            # ❗ 12월 8일 이후 BUY_DATE 변경 금지
            if buy_date.month == 12 and buy_date.day >= 8:
                send_message(
                    f"{sym}({stock_name}) SEQ:{seq} | "
                    f"12월 8일 이후 → BUY_DATE 변경 안함"
                )
                continue
            # next buy_date 결정
            # next buy_date 결정
            next_buy_date = None

            # 🔹 idx+1 부터 마지막까지 모두 탐색
            for next_idx in range(idx + 1, len(records)):
                candidate_date = datetime.datetime.strptime(
                    records[next_idx]["BUY_DATE"], "%Y-%m-%d"
                )
                send_message(f"Nextdate idx:{next_idx}, candidate:{candidate_date}")

                # 🔹 현재 buy_date보다 이후의 날짜인 경우에만 사용
                if candidate_date > buy_date:
                    next_buy_date = candidate_date
                    break   # 기존 구조 유지 (처음 발견되는 날짜 사용)

            # 이후 날짜가 없으면 13영업일 후 계산
            if next_buy_date is None:
                send_message(f"Nextdate None after full scan, idx:{idx}")
                next_buy_date = get_next_buy_date(buy_date, 13)


            send_message(
                f"{sym}({stock_name}) SEQ:{seq} | "
                f"손실 → BUY_DATE 변경 "
                f"{record['BUY_DATE']} → "
                f"{next_buy_date.strftime('%Y-%m-%d')}"
            )
            record["BUY_DATE"] = next_buy_date.strftime("%Y-%m-%d")
    # 🔹 파일 저장
    bought_stock_dates[sym] = records
    save_bought_stock_dates(bought_stock_dates)

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
    
# 종목별 날자별, 10일 이상 경과한 경우 매도 후 해당 레코드 삭제하는 함수
def process_and_sell_first_record(sym):
    # 매수 기록 불러오기
    bought_stock_dates = load_bought_stock_dates()
    # 해당 종목이 기록에 있는지 확인
    if sym in bought_stock_dates and len(bought_stock_dates[sym]) > 0:
        stock_name = get_stock_name(sym)
        market1 = "NASD"
        market2 = "NAS"
        if sym in nyse_symbol_list:
            market1 = "NYSE"
            market2 = "NYS"
        if sym in amex_symbol_list:
            market1 = "AMEX"
            market2 = "AMS"
        current_price = get_current_price(market2, sym)
        ma20 = get_moving_average(market2, sym, 20)
        # 각 SEQ 레코드 확인
        for record in bought_stock_dates[sym][:]:  # 리스트 복사본 사용 (리스트 수정 중 반복)
            buy_date_str = record["BUY_DATE"]
            seq = record["SEQ"]
            buy_date = datetime.datetime.strptime(buy_date_str, "%Y-%m-%d")
            days_held = count_trading_days(buy_date)  # 매수 후 경과 일수 계산
            buy_qty = record["BUY_CNT"]
            buy_price = float(record["BUY_PRICE"])
            profit_rate = (current_price - buy_price) / buy_price * 100
            # 매수 후 경과된 일수 출력
            # send_message(f"{sym}({stock_name})({buy_qty}주)(가격: {buy_price})(수익률: {profit_rate:.2f}%) 보유 {days_held}일")
            
            # 매수 후 13일 이상 경과 시 매도
            if days_held >= 13 and current_price > buy_price:
                send_message(f"{sym}({stock_name})({buy_qty}주) 매수 후 {days_held}일 경과되어 자동 매도 진행.")
                market1 = "NASD"
                market2 = "NAS"
                if sym in nyse_symbol_list:
                    market1 = "NYSE"
                    market2 = "NYS"
                if sym in amex_symbol_list:
                    market1 = "AMEX"
                    market2 = "AMS"
                sell(market=market1, code=sym, qty=buy_qty, price=get_current_price(market=market2, code=sym))
                time.sleep(1)
                # 기록 삭제
                bought_stock_dates[sym].remove(record)
        # 변경된 기록을 파일에 저장
        save_bought_stock_dates(bought_stock_dates)

def get_trading_times():
    global t_now_ny
    global t_9
    global t_start
    global t_buy
    global t_sell
    global t_exit
    # 1. 미국 동부 시간대(America/New_York)와 한국 시간대(Asia/Seoul) 설정
    ny_tz = pytz.timezone('America/New_York')
    kr_tz = pytz.timezone('Asia/Seoul')

    # 2. 오늘 날짜를 뉴욕 시간 기준으로 가져오기
    t_now_ny = datetime.datetime.now(ny_tz)
    today_date_ny = t_now_ny.date()
    # 3. NYSE 캘린더 불러오기 (NASDAQ도 동일한 시간 적용)
    nyse = xcals.get_calendar("XNYS")

    # 4. 오늘이 거래일인지 확인하고, 거래 시간을 가져옴
    if nyse.is_session(today_date_ny):
        # schedule은 pandas DataFrame 형태로 반환됩니다.
        schedule = nyse.schedule.loc[nyse.schedule.index.date == today_date_ny]
        if not schedule.empty:
            # schedule에서 오늘의 폐장 시간 (UTC)
            close_time_utc = schedule.iloc[0]['close'].to_pydatetime()
            # UTC → 뉴욕 시간 변환
            close_time_ny = close_time_utc.astimezone(ny_tz)
           
            # 6. 폐장 시간을 기준으로 t_buy, t_sell, t_exit 시간 계산
            # 조기폐장일에는 폐장 30분 전부터 시작
            t_9 = t_now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
            t_start = t_now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
            t_buy = close_time_ny - datetime.timedelta(minutes=30)
            t_sell = close_time_ny - datetime.timedelta(minutes=15)
            t_exit = close_time_ny - datetime.timedelta(minutes=10)  # 종료는 폐장 10분 전으로 설정

            # 7. 뉴욕 시간과 한국 시간으로 변환하여 출력
            close_time_kr = close_time_ny.astimezone(kr_tz)
            t_9_kr = t_9.astimezone(kr_tz)
            t_start_kr = t_start.astimezone(kr_tz)
            t_buy_kr = t_buy.astimezone(kr_tz)
            t_sell_kr = t_sell.astimezone(kr_tz)
            t_exit_kr = t_exit.astimezone(kr_tz)
            t_now_kr = t_now_ny.astimezone(kr_tz)
            
# 자동매매 시작
try:
    ACCESS_TOKEN = get_access_token()    
        
    nasd_symbol_list = ["TQQQ"]
    nyse_symbol_list = [] 
    amex_symbol_list = [] # 
    symbol_list = nasd_symbol_list + nyse_symbol_list + amex_symbol_list
    send_message("===해외 주식 자동매매 프로그램을 시작합니다===")
    send_message("--------------------------------------------")
    exchange_rate = get_exchange_rate() # 환율 조회
    total_cash = get_balance() # 보유 현금 조회
    stock_dict, buy_prices, tot_profit = get_stock_balance() # 보유 주식 조회 및 매수 가격 기록
    target_buy_count = 3 # 매수할 종목 수
    buy_amount = 3000000 / exchange_rate # 종목당 매수 금액(40만원 * 1.3 * 7 = 400만원)
    soldout = False
    count_cnt = 0
    time_cnt = 0
                     
    while True:
        t_now_ny = None
        t_9 = None
        t_start = None
        t_buy = None
        t_sell = None
        t_exit = None
        us_holidays = holidays.US()

        get_trading_times()

        time_cnt += 1
        if time_cnt <= 3:
            send_message(f"0. 뉴욕 현재시간: {t_now_ny.strftime('%Y-%m-%d %H:%M:%S')}, COUNT:{time_cnt}")
        
        # t_9 = t_now_ny.replace(hour=1, minute=30, second=0, microsecond=0)
        # t_start = t_now_ny.replace(hour=1, minute=30, second=0, microsecond=0)
        # t_buy = t_now_ny.replace(hour=3, minute=29, second=0, microsecond=0)
        # t_sell = t_now_ny.replace(hour=3, minute=31, second=0, microsecond=0)
        # t_exit = t_now_ny.replace(hour=3, minute=32, second=0, microsecond=0)

        if t_now_ny in us_holidays:
            holiday_name = us_holidays[t_now_ny]
            send_message(f"{t_now_ny} (미국 공휴일: {holiday_name}) ⇒ 프로그램 종료")
            break
        if t_now_ny.weekday() >= 5:  # 토요일이나 일요일이면 자동 종료
            send_message("주말!!! 프로그램 종료.")
            break
                
        if t_start < t_now_ny < t_buy :  # AM 9:30 ~ PM 03:30 : 모니터링
            if t_now_ny.minute == 10 or t_now_ny.minute == 40: 
                send_message(f"0. Symbol체크(매수대상): ")
                for sym in symbol_list:
                    market1 = "NASD"
                    market2 = "NAS"
                    if sym in nyse_symbol_list:
                        market1 = "NYSE"
                        market2 = "NYS"
                    if sym in amex_symbol_list:
                        market1 = "AMEX"
                        market2 = "AMS"
                    stock_name = get_stock_name(sym)
                    
                    current_price = get_current_price(market2, sym)
                    ma10 = get_moving_average(market2, sym, 10)
                    prev_close_price = get_previous_close_price(market2, sym)
                    ma10_prev = get_prev_moving_average(market2, sym, 10)
                    ma20 = get_moving_average(market2, sym, 20)
                    ma20_prev = get_prev_moving_average(market2, sym, 20)
                    today_vol, prev_vol = get_us_daily_volume(market2, sym, 2)
                    time.sleep(1) #매우중요
                    if current_price*today_vol > 1000000 and ((prev_close_price < ma10_prev and current_price > ma10) or (prev_close_price < ma20_prev and current_price > ma20) ):
                        send_message(f"{sym}({stock_name}) 10일 or 이평 돌파 매수 대상. 현재가:{current_price}, 10일: {ma10}, 이평: {ma20}, 종가(직전): {prev_close_price}, 10일(직전):{ma10_prev}, 이평(직전):{ma20_prev}")
                time.sleep(1)

                for sym in stock_dict.keys():
                    market1 = "NASD"
                    market2 = "NAS"
                    if sym in nyse_symbol_list:
                        market1 = "NYSE"
                        market2 = "NYS"
                    if sym in amex_symbol_list:
                        market1 = "AMEX"
                        market2 = "AMS"
                    current_price = get_current_price(market2, sym)
                    ma10 = get_moving_average(market2, sym, 10)
                    if sym in buy_prices:
                        stock_name = get_stock_name(sym)
                        send_message(f"1. 보유종목: {sym}({stock_name})")
                        buy_price = float(buy_prices[sym])
                        percentage = round((current_price / buy_price) * 100, 2)
                        if current_price >= buy_price * 1.05:  # 
                            send_message(f"{sym}({stock_name}) 수익실현매도 Signal. 매수가 {buy_price}, 현재가 {current_price}({percentage}%)")
                        if current_price <= buy_price * 0.97:  # 
                            send_message(f"{sym}({stock_name}) 손절매도 Signal. 매수가 {buy_price}, 현재가 {current_price}({percentage}%)")  
                time.sleep(60)

            if  t_now_ny.hour % 2 == 0 and t_now_ny.minute == 30: 
                send_message(f"2. 주식/현금 조회: ")
                stock_dict, buy_prices, tot_profit = get_stock_balance() # 보유주 조회 및 매수 가격 기록
                total_cash = get_balance() # 보유 현금 조회
                time.sleep(60)

        if t_buy <  t_now_ny < t_sell :  # # PM 03:30 ~ PM 03:45 : 매수
            count_cnt += 1
            if count_cnt <= 3:
                send_message(f"3-1. 뉴욕 현재시간: {t_now_ny.strftime('%Y-%m-%d %H:%M:%S')}, COUNT:{count_cnt}")
            for sym in symbol_list:
                if len(stock_dict) < target_buy_count:
                    market1 = "NASD"
                    market2 = "NAS"
                    if sym in nyse_symbol_list:
                        market1 = "NYSE"
                        market2 = "NYS"
                    if sym in amex_symbol_list:
                        market1 = "AMEX"
                        market2 = "AMS"
                    stock_name = get_stock_name(sym)
                    if count_cnt <= 1:
                        send_message(f"3-2. 매수체크: {sym}({stock_name}), COUNT:{count_cnt}")
                    current_price = get_current_price(market2, sym)
                    ma10 = get_moving_average(market2, sym, 10)
                    prev_close_price = get_previous_close_price(market2, sym)
                    ma10_prev = get_prev_moving_average(market2, sym, 10)
                    today_vol, prev_vol = get_us_daily_volume(market2, sym, 2)
                    mv10 = get_us_moving_volume(market2, sym, 10)
                    ma20 = get_moving_average(market2, sym, 20)
                    ma20_prev = get_prev_moving_average(market2, sym, 20)
                    time.sleep(1) #매우중요
                    if current_price*today_vol > 1000000 and ((prev_close_price < ma10_prev and current_price > ma10) or (prev_close_price < ma20_prev and current_price > ma20)):
                        if total_cash < current_price and count_cnt <= 3:
                            send_message(f"{sym}({stock_name}) 종목 매수하기에 금액이 부족합니다.")
                            continue
                        buy_qty = 0  # 매수할 수량 초기화
                        if total_cash < buy_amount: # 보유금액이 1종목 매수할 금액보다 적을 경우 보유금액으로 종목의 현재가를 나누어 매수할 수량을 구한다.
                            buy_amount = total_cash
                        buy_qty = int(buy_amount // current_price)
                        if buy_qty > 0:
                            send_message(f"{sym}({stock_name}) 이평선 돌파하여  ({buy_qty})개 매수를 시도합니다. 현재가:{current_price}, 10일: {ma10}, 이평: {ma20}, 종가(직전): {prev_close_price}, 10일(직전):{ma10_prev}, 이평(직전):{ma20_prev} ")
                            market = "NASD"
                            if sym in nyse_symbol_list:
                                market = "NYSE"
                            if sym in amex_symbol_list:
                                market = "AMEX"
                            result = buy(market=market1, code=sym, qty=buy_qty, price=get_current_price(market=market2, code=sym))
                            time.sleep(5) #매우 중요할 듯
                            if result:
                                soldout = False
                                symbol_list.remove(sym)
                                # 새로운 매수 기록 업데이트
                                update_bought_stock(sym, buy_qty, current_price)
                                stock_dict, buy_prices, tot_profit = get_stock_balance()
                                total_cash = get_balance() # 보유 현금 조회
            time.sleep(10)

        if t_sell < t_now_ny < t_exit:  # PM 03:45 ~ PM 03:50 : 일괄 매도
            if soldout == False:
                stock_dict, buy_prices, tot_profit = get_stock_balance()
                total_cash = get_balance() # 보유 현금 조회
                time.sleep(1)
                send_message(f"4. 보유기간:")
                for sym in stock_dict.keys():
                    # 수익률이 마이너스일 경우 buy_date 수정
                    process_and_modify_first_record(sym)
                    # 종목 매수 후 첫 번째 기록 가져오기 및 10일 경과 시 매도
                    process_and_sell_first_record(sym)
                soldout = True
                time.sleep(1)

        if t_exit < t_now_ny:  # PM 03:50 ~ :프로그램 종료
            send_message("프로그램을 종료합니다.")
            break
except IndexError as e:
    send_message(f"IndexError: {e}")        
except Exception as e:
    send_message(f"[오류 발생]{e}")
    time.sleep(1)