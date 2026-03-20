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

def get_moving_average(code="005935", days=5):
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
    prices = [int(item['stck_clpr']) for item in data[1:days+1]]
    moving_average = sum(prices) / len(prices)
    return moving_average

def get_prev_close_price(code="005935", days_ago=1):
    """N일 전 종가 조회 (days_ago=1 → 전일, 2 → 2일전)"""
    
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
        "fid_cond_mrkt_div_code": "J",   # 코스피
        "fid_input_iscd": code,
        "fid_org_adj_prc": "1",
        "fid_period_div_code": "D"
    }
    
    res = requests.get(URL, headers=headers, params=params)
    data = res.json().get('output', [])
    
    # 필요한 데이터 길이 체크 (오늘 포함 + N일 전)
    if len(data) <= days_ago:
        raise ValueError(
            f"{code} 데이터 부족 (요청: {days_ago}일 전, 데이터 길이: {len(data)})"
        )
    
    # 🔥 핵심: 인덱스를 days_ago로 변경
    close_price = int(data[days_ago]['stck_clpr'])
    
    return close_price

def get_price_by_day(code="005935", days_ago=1, field="close"):
    """
    N일 전 OHLCV 데이터 조회
    
    field:
        "open"   : 시가
        "high"   : 고가
        "low"    : 저가
        "close"  : 종가
        "volume" : 거래량
    """
    
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
    
    res = requests.get(URL, headers=headers, params=params)
    data = res.json().get('output', [])
    
    if len(data) <= days_ago:
        raise ValueError(
            f"{code} 데이터 부족 (요청: {days_ago}일 전, 데이터 길이: {len(data)})"
        )
    
    row = data[days_ago]
    
    # 🔥 필드 매핑 (KIS API 필드명)
    field_map = {
        "open": "stck_oprc",   # 시가
        "high": "stck_hgpr",   # 고가
        "low": "stck_lwpr",    # 저가
        "close": "stck_clpr",  # 종가
        "volume": "acml_vol"   # 거래량
    }
    
    if field not in field_map:
        raise ValueError(f"지원하지 않는 field: {field}")
    
    return int(row[field_map[field]])
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

def calc_ai_score_fast(code):
    score = 0

    try:
        # 🔥 한번만 호출
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

        res = requests.get(URL, headers=headers, params=params)
        data = res.json().get('output', [])

        if len(data) < 21:
            return 0

        # 🔥 데이터 정리
        closes = [int(d['stck_clpr']) for d in data]
        volumes = [int(d['acml_vol']) for d in data]

        print("closes: ", closes)
        print("volumes: ", volumes)
        # 이동평균
        ma5 = sum(closes[1:6]) / 5
        ma20 = sum(closes[1:21]) / 20
        print("ma5: ", ma5)
        print("ma20: ", ma20)
        close_0, close_1, close_2 = closes[0], closes[1], closes[2]
        vol_1, vol_2 = volumes[1], volumes[2]
        print("close_0: ", close_0)
        print("close_1: ", close_1)
        print("close_2: ", close_2)
        print("vol_1: ", vol_1)
        print("vol_2: ", vol_2)
        open_0 = int(data[0]['stck_oprc'])
        high_0 = int(data[0]['stck_hgpr'])
        low_0 = int(data[0]['stck_lwpr'])
        print("open_0: ", open_0)
        print("high_0: ", high_0)
        print("low_0: ", low_0)
        # 1️⃣ 추세
        if ma5 > ma20:
            score += 20

        # 2️⃣ 거래대금
        if close_1 * vol_1 > close_2 * vol_2 * 2:
            score += 25

        # 3️⃣ 모멘텀
        if (close_1 - close_2) / close_2 > 0.05:
            score += 20

        # 4️⃣ 눌림목
        if -0.03 < (close_0 - close_1) / close_1 < 0.02:
            score += 15

        # 5️⃣ 변동성
        if (high_0 - low_0) / low_0 > 0.03:
            score += 10

        # 6️⃣ 갭
        if 0.02 < (open_0 - close_1) / close_1 < 0.05:
            score += 10

    except Exception as e:
        print(f"{code} 오류:", e)
        return 0

    return score

# 자동매매 시작
try:
    ACCESS_TOKEN = get_access_token()
    # print(ACCESS_TOKEN)
    # ACCESS_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJzdWIiOiJ0b2tlbiIsImF1ZCI6IjhlZDM1NWVkLTNhMzYtNDljMC1iNmU5LTA1NTQ1NjllYjU2ZiIsInByZHRfY2QiOiIiLCJpc3MiOiJ1bm9ndyIsImV4cCI6MTc3Mzk1NTQwMiwiaWF0IjoxNzczODY5MDAyLCJqdGkiOiJQU0ZieDJORUZ3d3RDZHZudHhFaWVHUHAwSFphaDNNakRRSFYifQ.VNLs_la4nReE8TsG1g7almEkfCZ73Tm25Hnhi2hJlQtm4UNk75h7vYYro-GYtn3WfeX61o_oXbrjy7Tz4ndTjA"

    START_CASH = 100_000_000
    start_date = "2026-01-01"
    end_date = "2026-12-31"
    symbols = ["000660"]  # 하이닉스
    symbols = ["000660","035420","051910","006400","052690","454910"]
            # '005930',  # 삼성전자  -1%
            # '000660',  # SK하이닉스  88%
            # '035420',  # NAVER   20%
            # '051910',  # LG화학    92%
            # '006400',  # 삼성SDI    76%
            # '068270',  # 셀트리온     5.1%
            # '207940',  # 삼성바이오로직스    5.41%
            # '035720',  # 카카오   -12%
            # '105560',  # KB금융    -13%
            # '055550',  # 신한지주    -17%]
            # '052690', # 한전기술
            # '454910', # 두산로보틱스

    BUY_SCORE = 50
    TAKE_PROFIT = 0.03
    STOP_LOSS = -0.02
    MAX_POSITIONS = 3   # 최대 동시 보유 종목 수

    data = {}
    for sym in symbols:
        start_date_adj = (pd.to_datetime(start_date) - pd.DateOffset(months=1)).strftime("%Y-%m-%d")
        df = fdr.DataReader(sym, start_date_adj, end=end_date)
        data[sym] = df

    # 날짜 통합
    dates = sorted(list(set().union(*[df.index for df in data.values()])))

    send_message("=== AI단타 자동매매 프로그램 시작 ===")

    while True:
        ##########################################
        # 💰 계좌 상태 초기화(매우중요)
        ##########################################
        cash = START_CASH
        positions = {}  # {종목: {qty, buy_price, buy_date}}
        equity_curve = []
        trade_log = []

        kr_holidays = holidays.KR()
        t_now = datetime.datetime.now().replace(microsecond=0)
        today = t_now.weekday()

        t_9 = t_now.replace(hour=9, minute=10, second=0, microsecond=0)
        t_stop_new_buy = t_now.replace(hour=15, minute=0, second=0, microsecond=0)
        t_exit = t_now.replace(hour=15, minute=20, second=0, microsecond=0)

        # 휴일/주말 종료
        if t_now in kr_holidays or today >= 5:
            send_message("휴일 또는 주말 → 종료")
            break
        
        if t_9 < t_now < t_stop_new_buy: # 모니터링
           if t_now.minute % 30 == 0: 
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
                send_message(f"초기 자산: {START_CASH:,.0f}")
                send_message(f"최종 자산: {final_asset:,.0f}")
                send_message(f"총 수익률: {total_return*100:.2f}%")
                # print(f"MDD: {mdd*100:.2f}%")
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
                time.sleep(60)           
        

        # ===============================
        # 4️⃣ 종료
        # ===============================
        if t_now > t_exit:
            send_message("프로그램 종료")
            break

except Exception as e:
    send_message(f"[오류 발생]{e}")
