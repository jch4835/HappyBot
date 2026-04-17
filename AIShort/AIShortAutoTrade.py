import requests
import yaml
import requests
import json
import datetime
import time
import yaml
import holidays
import FinanceDataReader as fdr
import pandas as pd
from pykrx import stock
import sys

with open('C:\\git\\HappyBot\\AIShort\\config.yaml', encoding='UTF-8') as f:    
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

# =========================
# 종목 캐시
# =========================
_STOCK_CACHE = {}

def load_market(market):
    if market not in _STOCK_CACHE:
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

def get_kr_stock_name(code):
    ticker_name = stock.get_market_ticker_name(code)
    return ticker_name if ticker_name else None

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

def get_price(sym, date, df):
    
    # 오늘이면 실시간 가격
    if date.date() == pd.Timestamp.today().date():
        return get_current_price(sym)   # ← 한국투자증권 API
    
    # 과거면 종가
    return df.loc[date]['Close']

##########################################
# 🧠 AI 점수
##########################################
def calc_ai_score(df):
    score = 0

    try:
        ma5 = df['Close'].rolling(5).mean()
        ma20 = df['Close'].rolling(20).mean()
        # 1.추세점수 : 단기상승추세(지금상승흐름인지 인)
        if ma5.iloc[-1] > ma20.iloc[-1]:
            score += 20
        # 2.거래대금 증가율 : 큰 돈이 들어왔다(세력유입, 가장중요한 조건)
        v1 = df.iloc[-2]['Close'] * df.iloc[-2]['Volume']
        v2 = df.iloc[-3]['Close'] * df.iloc[-3]['Volume']

        if v1 > v2 * 2:
            score += 25
        # 3.상승모멘텀 : 강한 상승 시작 구간, 급등 초기 포착, 초기상승 -> 단타 최적 구간
        momentum = (df.iloc[-2]['Close'] - df.iloc[-3]['Close']) / df.iloc[-3]['Close']
        if momentum > 0.05:
            score += 20
        # 4.눌림목 상태 : 조금쉬었다가 다시 갈 자리(너무 많이 빠지면 안 되고 너무 올라버리면 늦음)
        pullback = (df.iloc[-1]['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']
        if -0.03 < pullback < 0.02:
            score += 15
        # 5. 변동성 : 단타 가능한 움직임 있음, 안 움직이면 수익 못 냄 
        vol = (df.iloc[-1]['High'] - df.iloc[-1]['Low']) / df.iloc[-1]['Low']
        if vol > 0.03:
            score += 10
        # 6. 갭조건 : 시초에 강한 매수세, 시장관심+ 뉴스 + 수급
        gap = (df.iloc[-1]['Open'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close']
        if 0.02 < gap < 0.05:
            score += 10

    except:
        return 0

    return score

#종목별 백테스트 함수
def run_backtest_single(sym, df):

    cash = START_CASH
    positions = {}
    equity_curve = []
    trade_log = []

    dates = df.index

    for date in dates:

        # 🔴 매도
        for s in list(positions.keys()):

            if date not in df.index:
                continue

            price = df.loc[date]['Close']
            pos = positions[s]

            ret = (price - pos['buy_price']) / pos['buy_price']

            if ret >= TAKE_PROFIT or ret <= STOP_LOSS:
                cash += pos['qty'] * price

                trade_log.append({
                    "symbol": s,
                    "type": "SELL",
                    "date": date,
                    "price": price,
                    "qty": pos['qty'],
                    "return": ret,
                    "reason": "익절" if ret > 0 else "손절"
                })

                del positions[s]

        # 🟢 매수
        if len(positions) < MAX_POSITIONS:

            idx = df.index.get_loc(date)
            if idx >= 20:

                sub_df = df.iloc[:idx]
                score = calc_ai_score(sub_df)

                if score >= BUY_SCORE:

                    price = df.loc[date]['Close']
                    invest_cash = cash
                    qty = int(invest_cash // price)

                    if qty > 0:
                        cash -= qty * price

                        positions[sym] = {
                            "qty": qty,
                            "buy_price": price,
                            "buy_date": date
                        }

                        trade_log.append({
                            "symbol": sym,
                            "type": "BUY",
                            "date": date,
                            "price": price,
                            "qty": qty,
                            "reason": f"AI score={score}"
                        })

        # 💰 평가
        total = cash
        for s, pos in positions.items():
            if date in df.index:
                price = df.loc[date]['Close']
                total += pos['qty'] * price

        equity_curve.append(total)

    # 📊 결과 계산
    equity_series = pd.Series(equity_curve)

    final_asset = equity_series.iloc[-1]
    total_return = (final_asset - START_CASH) / START_CASH

    peak = equity_series.cummax()
    drawdown = (equity_series - peak) / peak
    mdd = drawdown.min()

    wins, losses = 0, 0
    for t in trade_log:
        if t['type'] == "SELL":
            if t['return'] > 0:
                wins += 1
            else:
                losses += 1

    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0

    return {
        "sym": sym,
        "final_asset": final_asset,
        "total_return": total_return,
        "mdd": mdd,
        "win_rate": win_rate,
        "trades": trade_log,
        "wins": wins,
        "losses":losses,
    }

def get_stock_balance(show_log=True):
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
    if show_log:
        send_message(f"====주식 보유잔고====")
    for stock in stock_list:
        if int(stock['hldg_qty']) > 0:
            stock_dict[stock['pdno']] = stock['hldg_qty']
            buy_prices[stock['pdno']] = stock['pchs_avg_pric'] # 매수 가격 기록
            if show_log:
                send_message(f"{stock['prdt_name']}({stock['pdno']}): {stock['hldg_qty']}주({stock['pchs_avg_pric']}원)")
            time.sleep(0.1)
    if show_log:            
        send_message(f"주식 평가 금액: {evaluation[0]['scts_evlu_amt']}원")
        time.sleep(0.1)
        send_message(f"평가 손익 합계: {evaluation[0]['evlu_pfls_smtl_amt']}원")
        time.sleep(0.1)
        send_message(f"총 평가 금액: {evaluation[0]['tot_evlu_amt']}원")
        time.sleep(0.1)
        send_message(f"=================")
    return stock_dict, buy_prices

def get_balance(show_log=True):
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
    if show_log:
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
    
# 자동매매 시작
try:
    kr_holidays = holidays.KR()
    t_now = datetime.datetime.now().replace(microsecond=0)
    today = t_now.weekday()

    # 휴일/주말 종료
    if t_now in kr_holidays or today >= 5:
        send_message("휴일 또는 주말 → 종료")
        sys.exit()

    ACCESS_TOKEN = get_access_token()
    # print(ACCESS_TOKEN)
    # ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ0b2tlbiIsImF1ZCI6IjhlZDM1NWVkLTNhMzYtNDljMC1iNmU5LTA1NTQ1NjllYjU2ZiIsInByZHRfY2QiOiIiLCJpc3MiOiJ1bm9ndyIsImV4cCI6MTc3Mzk1NTQwMiwiaWF0IjoxNzczODY5MDAyLCJqdGkiOiJQU0ZieDJORUZ3d3RDZHZudHhFaWVHUHAwSFphaDNNakRRSFYifQ.VNLs_la4nReE8TsG1g7almEkfCZ73Tm25Hnhi2hJlQtm4UNk75h7vYYro-GYtn3WfeX61o_oXbrjy7Tz4ndTjA"

    START_CASH = 4_000_000
    start_date = "2026-01-01"
    end_date = "2026-12-31"
    # symbols = ["006360"]  # 하이닉스
    symbols = ["005930","000660","035420","051910","006400","052690","454910","034020","006360"]
        # '005930',  # 삼성전자     6.88%
        # '000660',  # SK하이닉스  53.15%
        # '035420',  # NAVER      33.92%
        # '051910',  # LG화학      45.44%
        # '006400',  # 삼성SDI     30.18%
        # '068270',  # 셀트리온     34.15%
        # '207940',  # 삼성바이오로직스    25.36%
        # '035720',  # 카카오      19.27%
        # '105560',  # KB금융      -2.95%
        # '055550',  # 신한지주     -4.3%
        # '052690', # 한전기술      1.5%
        # '454910', # 두산로보틱스  26.5%
        # '034020', # 두산에너빌리티  41.27%
        # '006360', # GS건설 

    BUY_SCORE = 50
    TAKE_PROFIT = 0.03
    STOP_LOSS = -0.02
    MAX_POSITIONS = 3   # 최대 동시 보유 종목 수
    
    data = {}
    results = []

    for sym in symbols:
        start_date_adj = (pd.to_datetime(start_date) - pd.DateOffset(months=1)).strftime("%Y-%m-%d")
        df = fdr.DataReader(sym, start_date_adj, end=end_date)
        data[sym] = df

        result = run_backtest_single(sym, df)
        results.append(result)
    
    send_message("===== AI단타 자동매매 프로그램 시작 =====")
    send_message("==========종목별 백테스트 결과==========")
    send_message(f"=== 기간: {start_date} ~ {end_date} ===")

    for r in results:
        send_message(
                    f"🔥 {r['sym']}({get_stock_name(r['sym'])}) | 수익률: {r['total_return']*100:.2f}% | "
                    f"승률: {r['win_rate']*100:.1f}% | 거래수: {r['wins']+r['losses']}"
        )
        time.sleep(5)

    time.sleep(30)

    # 날짜 통합
    dates = sorted(list(set().union(*[df.index for df in data.values()])))    

    executed_buy = set()
    executed_sell = set()
    total_cash = get_balance()
    stock_dict, buy_prices = get_stock_balance()
    buy_log = []

    while True:
        ##########################################
        # 💰 계좌 상태 초기화(매우중요)
        ##########################################
        cash = START_CASH
        positions = {}  # {종목: {qty, buy_price, buy_date}}
        equity_curve = []
        trade_log = []

        t_now = datetime.datetime.now().replace(microsecond=0)
        
        t_9 = t_now.replace(hour=9, minute=10, second=0, microsecond=0)
        t_mon_end = t_now.replace(hour=15, minute=0, second=0, microsecond=0) 
        t_sell_start = t_now.replace(hour=15, minute=0, second=0, microsecond=0) 
        t_sell_end = t_now.replace(hour=15, minute=5, second=0, microsecond=0) 
        t_buy_start = t_now.replace(hour=15, minute=5, second=0, microsecond=0)
        t_buy_end = t_now.replace(hour=15, minute=10, second=0, microsecond=0) 
        t_exit = t_now.replace(hour=15, minute=20, second=0, microsecond=0) 

        if t_9 < t_now < t_mon_end: # 모니터링
           if t_now.hour % 2 == 0 and t_now.minute == 0:
                ##########################################
                # 🚀 메인 루프 (실전형)
                ##########################################
                for date in dates:

                    # 🔴 1. 매도 먼저 (리스크 관리)
                    for sym in list(positions.keys()):

                        df = data[sym]

                        if date not in df.index:
                            continue
                        # 오늘 가격 기준으로 익절 / 손절 판단 get_current_price(sym) 으로 교체 필요
                        # 오늘이면 실시간 가격 과거이면 종가
                        # price = df.loc[date]['Close'] # today close price
                        price = get_price(sym, date, df)
                        pos = positions[sym]

                        ret = (price - pos['buy_price']) / pos['buy_price']

                        if ret >= TAKE_PROFIT or ret <= STOP_LOSS:

                            cash += pos['qty'] * price

                            trade_log.append({
                                "symbol": sym,
                                "type": "SELL",
                                "date": date,
                                "price": price,
                                "qty": pos['qty'],
                                "return": ret,
                                "reason": "익절" if ret > 0 else "손절"
                            })

                            del positions[sym]

                    # 🟢 2. 매수 (남은 자리만)
                    for sym in symbols:
                        if len(positions) >= MAX_POSITIONS:
                            break
                        if sym in positions:
                            continue
                        df = data[sym]
                        if date not in df.index:
                            continue
                        idx = df.index.get_loc(date)
                        if idx < 20:
                            continue
                        sub_df = df.iloc[:idx]
                        score = calc_ai_score(sub_df)
                        # score = calc_ai_score_fast(sym)
                        if score >= BUY_SCORE:
                            # 오늘 종가로 매수했다고 가정. get_current_price(sym) 으로 교체 필요
                            # 오늘이면 실시간 가격 과거이면 종가
                            # price = df.loc[date]['Close'] # today close price
                            price = get_price(sym, date, df)

                            invest_cash = cash / (MAX_POSITIONS - len(positions))
                            qty = int(invest_cash // price)

                            if qty == 0:
                                continue
                            cash -= qty * price
                            positions[sym] = {
                                "qty": qty,
                                "buy_price": price,
                                "buy_date": date
                            }

                            trade_log.append({
                                "symbol": sym,
                                "type": "BUY",
                                "date": date,
                                "price": price,
                                "qty": qty,
                                "reason": f"AI score={score}"
                            })

                    # 💰 3. 자산 평가
                    total = cash

                    for sym, pos in positions.items():
                        df = data[sym]
                        if date in df.index:
                            # 현재 계좌 평가금액 계산  get_current_price(sym) 교체 필요
                            # 오늘이면 실시간 가격 과거이면 종가
                            # price = df.loc[date]['Close'] # today close price
                            price = get_price(sym, date, df)
                            total += pos['qty'] * price

                    equity_curve.append(total)

                ##########################################
                # 📊 결과 분석
                ##########################################
                equity_series = pd.Series(equity_curve)

                final_asset = equity_series.iloc[-1]
                total_return = (final_asset - START_CASH) / START_CASH

                peak = equity_series.cummax()
                drawdown = (equity_series - peak) / peak
                mdd = drawdown.min()

                wins, losses = 0, 0

                for t in trade_log:
                    if t['type'] == "SELL":
                        if t['return'] > 0:
                            wins += 1
                        else:
                            losses += 1

                win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0

                ##########################################
                # 📋 상세 로그 출력
                ##########################################
                send_message("\n📊 ===== 백테스트 결과 =====")
                send_message(f"기간: {start_date} ~ {end_date}")
                send_message(f"🚀 총 수익률: 🔥 {total_return*100:.2f}% 🔥")
                send_message(f"초기 자산: {START_CASH:,.0f}")
                send_message(f"최종 자산: {final_asset:,.0f}")
                send_message(f"승률: {win_rate*100:.2f}%")
                send_message(f"총 거래 수: {wins+losses}")
                send_message(f"BUY SCORE: {BUY_SCORE}")

                send_message("\n📌 ===== 전체 거래 로그 (최근 20일) =====")

                # 오늘 기준 20일 전
                cutoff_date = datetime.datetime.now() - datetime.timedelta(days=20)

                for t in sorted(trade_log, key=lambda x: x['date']):
                    # 날짜 필터링
                    if t['date'] < cutoff_date:
                        continue

                    if t['type'] == "BUY":
                        send_message(
                            f"[매수] {t['date'].date()} {t['symbol']}({get_stock_name(t['symbol'])}) | 가격:{t['price']:.0f} | 수량:{t['qty']} | {t['reason']}"
                        )
                    else:
                        send_message(
                            f"[매도] {t['date'].date()} {t['symbol']}({get_stock_name(t['symbol'])}) | 가격:{t['price']:.0f} | 수량:{t['qty']} | 수익률:{t['return']*100:.2f}% | {t['reason']}"
                        )
                buy_log = trade_log
                time.sleep(60)           

        # ===============================
        # 🔴 매도 (15:00 ~ 15:05)
        # ===============================
        if t_sell_start <= t_now < t_sell_end:
            send_message("📌 실전 매도 체크")
            stock_dict, buy_prices = get_stock_balance(show_log=False)
            if stock_dict:
                send_message("📌 보유 체크")
                for code, qty in stock_dict.items():
                    # 🔴 중복 매도 방지
                    if code in executed_sell:
                        continue
                    try:
                        current_price = get_current_price(code)
                        buy_price = float(buy_prices[code])
                        ret = (current_price - buy_price) / buy_price
                        # 👉 기존 매도 조건 그대로 사용
                        if ret >= TAKE_PROFIT or ret <= STOP_LOSS:
                            send_message(f"[매도 실행] {code} / 수익률:{ret*100:.2f}%")
                            result = sell(code, qty)
                            if result:
                                executed_sell.add(code)   # ✅ 핵심
                                time.sleep(1)
                    except Exception as e:
                        send_message(f"[매도 오류] {code} : {e}")        
            time.sleep(60)
        # ===============================
        # 🟢 매수 (15:05 ~ 15:10)
        # ===============================
        if t_buy_start <= t_now < t_buy_end:
            send_message("📌 실전 매수 시작")
            today = datetime.datetime.now().date()
            for t in buy_log:
                # 오늘 매수 시그널만
                if t['type'] != "BUY":
                    continue
                if t['date'].date() != today:
                    continue
                code = t['symbol']
                qty = t['qty']
                current_price = get_current_price(code)
                send_message("📌 중복 매수 체크")
                # 🔴 중복 매수 방지
                if code in executed_buy:
                    continue
                send_message(f"[매수 시도] {code} / 수량:{qty}")
                result = buy(code, qty)
                if result:
                    executed_buy.add(code)   # ✅ 핵심
                    time.sleep(1)
            time.sleep(60)

        # ===============================
        # 4️⃣ 종료
        # ===============================
        if t_now > t_exit:
            send_message("프로그램 종료")
            break

except Exception as e:
    send_message(f"[오류 발생]{e}")
