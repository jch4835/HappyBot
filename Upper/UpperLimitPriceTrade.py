import requests
import json
import datetime
import time
import yaml
import holidays
import FinanceDataReader as fdr
import pandas as pd
from pykrx import stock

with open('C:\\git\\HappyBot\\Upper\\config.yaml', encoding='UTF-8') as f:    
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

def get_acml_vol(code="005935"):
    """거래량 조회"""
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
    return int(res.json()['output']['acml_vol'])

def get_bidp_rsqn1(code="005935"):
    """매수 1호가 대기 수량 조회"""
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
    return int(res.json()['output1']['bidp_rsqn1']) # 1호가 매수 대기 수량

def get_highprice_symbols():
    """상한가 종목 리스트 조회"""
    PATH = "/uapi/domestic-stock/v1/quotations/capture-uplowprice"
    URL = f"{URL_BASE}/{PATH}"
    headers = {"Content-Type":"application/json", 
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"FHKST130000C0",
        "custtype":"P"}
    params = {
        'FID_COND_MRKT_DIV_CODE':'J',
        'FID_COND_SCR_DIV_CODE':'11300',
        'FID_PRC_CLS_CODE':'0',
        'FID_DIV_CLS_CODE':'0',
        'FID_INPUT_ISCD':'0000',
        'FID_TRGT_CLS_CODE':'',
        'FID_TRGT_EXLS_CLS_CODE':'',
        'FID_INPUT_PRICE_1':'',
        'FID_INPUT_PRICE_2':'',
        'FID_VOL_CNT':''
    }
    # API 요청 보내기
    try:
        # t_now = datetime.datetime.now()
        t_now = datetime.datetime.now().replace(microsecond=0)

        res = requests.get(URL, headers=headers, params=params)
        #print(f'상한가: {res.text}')
        # 응답 처리
        if res.status_code == 200:
            data = res.json()
            # 결과 출력
            stocks = data.get('output', [])
            # send_message(f"상한가 종목 조회 결과 (총 {len(stocks)}개 종목):")
            sym_list = []
            
            for stock in stocks:
                sym = stock['mksc_shrn_iscd'] 
                sym_list.append(sym)
                acml_vol = int(stock['acml_vol'])  # 전체 거래량
                bidp_rsqn1 = int(stock['bidp_rsqn1'])  # 매수호가잔량1
                # 매수호가잔량1의 비율 계산 (소수점 둘째 자리까지 반올림)
                percentage = round((bidp_rsqn1 / acml_vol) * 100, 2)
                # send_message(f"종목명: {stock['hts_kor_isnm']}, 종목 코드: {sym}, 현재가: {stock['stck_prpr']}, 상승률: {stock['prdy_ctrt']}, 거래량: {acml_vol}, 매수호가잔량1: {bidp_rsqn1} ({percentage}%)")
                if sym not in upper_limit_reached:
                    upper_limit_reached[sym] = {
                        "stck_prpr": get_current_price(sym),
                        "time": t_now,
                        "initial_acml_vol": get_acml_vol(sym),
                        "initial_bidp_rsqn1": get_bidp_rsqn1(sym)
                    }
            return sym_list
        else:
            print("HTTP 요청 오류:", res.status_code, res.text)
            return []
    except Exception as e:
        print("예외 발생:", e)
        return []

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

def buy(code="005935", qty="1"):
    """주식 시장가 매수"""  
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
        ord_no = res.json()['output']['ODNO']  # 🔴 주문번호
        send_message(f"[매수 주문 접수] {code}, 주문번호:{ord_no}")
        return ord_no
    else:
        send_message(f"[매수 실패]{str(res.json())}")
        return False

def cancel_buy(code, orgn_odno):
    """미체결 매수 취소"""
    PATH = "uapi/domestic-stock/v1/trading/order-rvsecncl"
    URL = f"{URL_BASE}/{PATH}"

    data = {
        "CANO": CANO,
        "ACNT_PRDT_CD": ACNT_PRDT_CD,
        "ORGN_ODNO": orgn_odno,
        "ORD_DVSN": "01",
        "RVSE_CNCL_DVSN_CD": "02",  # 02 = 취소
        "ORD_QTY": "0",
        "ORD_UNPR": "0",
        "QTY_ALL_ORD_YN": "Y"
    }

    headers = {
        "Content-Type":"application/json",
        "authorization":f"Bearer {ACCESS_TOKEN}",
        "appKey":APP_KEY,
        "appSecret":APP_SECRET,
        "tr_id":"TTTC0013U",
        "custtype":"P",
        "hashkey": hashkey(data)
    }

    res = requests.post(URL, headers=headers, data=json.dumps(data))
    result = res.json()

    if result['rt_cd'] == '0':
        send_message(f"[매수 취소 성공] {code}, 주문번호:{orgn_odno}")
        return True
    else:
        send_message(f"[매수 취소 실패] {result}")
        return False

def sell(code="005935", qty="1"):
    """주식 시장가 매도"""
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

def get_kr_stock_name(code):
    ticker_name = stock.get_market_ticker_name(code)
    return ticker_name if ticker_name else None

# 전역 캐시
_STOCK_CACHE = {}
def load_market(market):
    if market not in _STOCK_CACHE:
        print(f"[LOAD] {market} 다운로드")
        _STOCK_CACHE[market] = fdr.StockListing(market)
    return _STOCK_CACHE[market]

def get_stock_name(code):
    code = code.upper()

    # 한국 (pykrx)
    if code.isdigit():
        try:
            name = get_kr_stock_name(code)
            if name:
                return name
        except Exception as e:
            print(f"[WARN] pykrx error: {e}")

    # 한국 ETF
    try:
        etf = load_market('ETF/KR')
        row = etf[etf['Symbol'] == code]
        if not row.empty:
            return row['Name'].values[0]
    except:
        pass

    # 미국
    for market in ['NASDAQ', 'NYSE', 'AMEX']:
        try:
            us = load_market(market)
            row = us[us['Symbol'] == code]
            if not row.empty:
                return row['Name'].values[0]
        except:
            pass

    return 'Not Found'

# 자동매매 시작
# 자동매매 시작
try:
    ACCESS_TOKEN = get_access_token()
    # print(ACCESS_TOKEN)
    # ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ0b2tlbiIsImF1ZCI6ImFmODQ1NzNmLTRmMmYtNDM5Mi05ZDlmLTFiNGEzMzZkMjFkNyIsInByZHRfY2QiOiIiLCJpc3MiOiJ1bm9ndyIsImV4cCI6MTc3MjE1MDcxMiwiaWF0IjoxNzcyMDY0MzEyLCJqdGkiOiJQU0ZieDJORUZ3d3RDZHZudHhFaWVHUHAwSFphaDNNakRRSFYifQ.bJ44oaV-3u4wacSgR6_X_xQu8pTHHbBWVfWXvRrLucp3dkzcRruwla6i_-CaoiIUKIbjQDOC0YirgAh6AwTAbg"
    highprice_symbols = []
    symbol_list = []
    bought_list = []
    total_cash = get_balance()
    stock_dict, buy_prices = get_stock_balance()

    for sym in stock_dict.keys():
        bought_list.append(sym)

    target_buy_count = 1
    buy_percent = 1
    buy_amount = total_cash * buy_percent
    soldout = False

    upper_limit_reached = {}
    pending_buy_orders = {}

    send_message("=== 상한가 자동매매 프로그램 시작 ===")

    while True:
        kr_holidays = holidays.KR()
        # t_now = datetime.datetime.now()
        t_now = datetime.datetime.now().replace(microsecond=0)
        today = t_now.weekday()

        t_9 = t_now.replace(hour=9, minute=0, second=0, microsecond=0)
        t_find = t_now.replace(hour=9, minute=20, second=0, microsecond=0)
        t_start = t_now.replace(hour=9, minute=20, second=0, microsecond=0)
        t_stop_new_buy = t_now.replace(hour=14, minute=30, second=0, microsecond=0)
        t_cancel = t_now.replace(hour=15, minute=0, second=0, microsecond=0)
        t_exit = t_now.replace(hour=15, minute=20, second=0, microsecond=0)

        # 휴일/주말 종료
        if t_now in kr_holidays or today >= 5:
            send_message("휴일 또는 주말 → 종료")
            break
        
        if t_9 < t_now < t_find and soldout == False: # 잔여 수량 매도
            for sym, qty in stock_dict.items():
                sell(sym, qty)
            soldout = True
            bought_list = []
            time.sleep(10)
            stock_dict, buy_prices = get_stock_balance()
            #보유주식 매도 후에 보유현금 다시 조회 하고 buy_amount 다시 계산한다
            total_cash = get_balance() # 보유 현금 조회

        # ===============================
        # 1️⃣ 상한가 발굴 + 즉시 매수 구간
        # ===============================
        if t_find < t_now < t_stop_new_buy:

            highprice_symbols = get_highprice_symbols()

            if len(highprice_symbols) >= 1:
                symbol_list = highprice_symbols[:]
                # send_message(f"발굴한 상한가 종목은 아래와 같습니다.")
                # send_message(f"검색회수: {highprice_symbols}")

            for sym in symbol_list:

                if len(bought_list) >= target_buy_count:
                    break

                if sym in bought_list:
                    continue

                current_price = get_current_price(sym)
                current_acml_vol = get_acml_vol(sym)
                current_bidp_rsqn1 = get_bidp_rsqn1(sym)
                stock_name = get_stock_name(sym)

                # 🔥 핵심수정 1: 5분 유지 후 매수
                # 상한가 풀리면 삭제
                if sym in upper_limit_reached:
                    if current_price != upper_limit_reached[sym]["stck_prpr"]:
                        continue

                elapsed = (t_now - upper_limit_reached[sym]["time"]).total_seconds()
                elapsed = max(0, elapsed)
                
                if elapsed < 180 or current_bidp_rsqn1 < upper_limit_reached[sym]["initial_bidp_rsqn1"] * 0.8:
                    continue

                # 🔥 핵심수정 2: 매수잔량 5% 이상
                if current_bidp_rsqn1 < current_acml_vol * 0.05:
                    continue

                # 거래대금 조건 완화 (5억)
                if current_price * current_acml_vol < 500000000:
                    continue

                buy_qty = int(buy_amount // current_price)

                if buy_qty > 0:
                    send_message(f"{sym}({stock_name}) 종목 상한가 매수를 시도합니다.")
                    send_message(f"매수호가잔량1({current_bidp_rsqn1})이 거래량의 5%({current_acml_vol*0.05:.2f}) 보다 큼.")
                    send_message(f"현재 거래대금({current_price*current_acml_vol})이 5억 보다 큼.")
                    send_message(f"상한가가 3분 이상 유지. 1호가 매수잔량 진입시의 80% 유지.")
                    send_message(f"{sym} 상한가 매수 시도")
                    ord_no = buy(sym, buy_qty)
                    if ord_no:
                        pending_buy_orders[sym] = ord_no
                        bought_list.append(sym)
                        stock_dict, buy_prices = get_stock_balance()

            time.sleep(1)

        # ===============================
        # 2️⃣ 보유 종목 관리
        # ===============================
        if t_now.second % 10 == 0 : # 30초 단위로 보유주식 현황 파악(매수시 즉 반영, 상한가 풀리는지 모니터링 대응 가능)
            stock_dict, buy_prices = get_stock_balance()
            total_cash = get_balance() # 보유 현금 조회
            time.sleep(1)
            
        if stock_dict:

            # 추가된 부분: 항상 매도 조건을 확인하도록 별도의 루프 추가, 보유재고에서 찾음
            for sym in stock_dict:
                if sym in upper_limit_reached:
                    stock_name = get_stock_name(sym)
                    current_price = get_current_price(sym)
                    current_bidp_rsqn1 = get_bidp_rsqn1(sym) # 현재 매수호가잔량1 을 구함
                    if current_price == upper_limit_reached[sym]["stck_prpr"] and current_bidp_rsqn1 < upper_limit_reached[sym]["initial_bidp_rsqn1"] * 0.5: # 매수호가잔량1 수량이 50% 이하로 줄어들 경우
                        qty = stock_dict[sym]
                        send_message(f"{sym}({stock_name}) 매수 대기 수량 감소로 상한가 풀릴 가능성 큼 매도 시도.")
                        send_message(f"현재 매수호가잔량1({current_bidp_rsqn1})이 상한가 도달시의 매수호가잔량1({upper_limit_reached[sym]["initial_bidp_rsqn1"]})의 50% 보다 작음.")
                        result = sell(sym, qty)
                        if result:
                            bought_list.remove(sym)
                            symbol_list.remove(sym)
                            stock_dict, buy_prices = get_stock_balance()
                time.sleep(1)

            for sym in list(stock_dict.keys()):

                qty = stock_dict[sym]
                current_price = get_current_price(sym)
               
                # 🔥 핵심수정 3: 상한가 이탈 즉시 매도
                if sym in upper_limit_reached:
                    upper_price = upper_limit_reached[sym]["stck_prpr"]
                    if current_price < upper_price:
                        send_message(f"{sym} 상한가 이탈 → 즉시 매도")
                        sell(sym, qty)
                        bought_list.remove(sym)
                        stock_dict, buy_prices = get_stock_balance()
                        continue

                # -4% 손절
                if sym in buy_prices:
                    buy_price = float(buy_prices[sym])
                    if current_price <= buy_price * 0.96:
                        send_message(f"{sym} -4% 손절")
                        sell(sym, qty)
                        bought_list.remove(sym)
                        stock_dict, buy_prices = get_stock_balance()

            time.sleep(1)

        # ===============================
        # 3️⃣ 15시 미체결 취소
        # ===============================
        if t_cancel < t_now < t_exit:
            for sym, ord_no in list(pending_buy_orders.items()):
                if sym not in stock_dict:
                    send_message(f"{sym} 미체결 취소")
                    cancel_buy(sym, ord_no)
                    pending_buy_orders.pop(sym)

        # ===============================
        # 4️⃣ 종료
        # ===============================
        if t_now > t_exit:
            send_message("프로그램 종료")
            break

except Exception as e:
    send_message(f"[오류 발생]{e}")
