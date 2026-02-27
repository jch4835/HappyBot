import FinanceDataReader as fdr
import matplotlib.pyplot as plt
from matplotlib import font_manager, rc
import platform
import numpy as np
import pandas as pd
import datetime
import requests
import yaml

# =========================================================
# Config
# =========================================================
with open('C:\\git\\HappyBot\\BackTest\\config.yaml', encoding='UTF-8') as f:
    _cfg = yaml.load(f, Loader=yaml.FullLoader)

DISCORD_WEBHOOK_URL = _cfg['DISCORD_WEBHOOK_URL']

# =========================================================
# Font
# =========================================================
if platform.system() == 'Windows':
    font_name = font_manager.FontProperties(
        fname='C:/Windows/Fonts/Arial.ttf'
    ).get_name()
    rc('font', family=font_name)

plt.rcParams['font.family'] = 'Arial'

# =========================================================
# Discord
# =========================================================
def send_message(msg):
    now = datetime.datetime.now()
    message = {"content": f"[{now:%Y-%m-%d %H:%M:%S}] {msg}"}
    requests.post(DISCORD_WEBHOOK_URL, data=message)
    print(message)

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

    try:
        etf = load_market('ETF/KR')
        row = etf[etf['Symbol'] == code]
        if not row.empty:
            return row['Name'].values[0]
    except:
        pass

    for market in ['NASDAQ', 'NYSE', 'AMEX']:
        try:
            us = load_market(market)
            row = us[us['Symbol'] == code]
            if not row.empty:
                return row['Name'].values[0]
        except:
            continue

    return 'Not Found'

# =========================================================
# HOLD 계산
# =========================================================
def calculate_max_hold(hold_ranges):
    events = []
    for start, end in hold_ranges:
        events.append((start, 1))
        events.append((end, -1))

    events.sort()
    current = 0
    max_hold = 0

    for _, delta in events:
        current += delta
        max_hold = max(max_hold, current)

    return max_hold


def calculate_current_hold(current_date, hold_ranges):
    return sum(
        1 for start, end in hold_ranges
        if start <= current_date < end
    )

# =========================================================
# Parameters
# =========================================================
code_list = ["465580","381180","457480","438080","438100"]
# code_list = ["465580","457480"]
code_list = ["465580"]
start_date = "2025-01-01"
end_date = "2025-12-31"

start_year = pd.to_datetime(start_date).year
sell_deadline = pd.to_datetime(end_date)

moving_start_date = (
    pd.to_datetime(start_date) - pd.DateOffset(days=40)
).strftime("%Y-%m-%d")

send_message(f"🇰🇷 한국 주식/ETF 백테스트 시작: {start_date} ~ {end_date}")

# =========================================================
# Result
# =========================================================
단순_기간_수익률_리스트 = []
이동평균_수익률_리스트 = []
signal_count_dict = {}
hold_count_dict = {}

# =========================================================
# Backtest
# =========================================================
for code in code_list:
    df = fdr.DataReader(code, moving_start_date, end_date)

    # 이동평균
    df['SMA10'] = df['Close'].rolling(10).mean()
    df['SMA20'] = df['Close'].rolling(20).mean()

    # 블린저밴드
    df['STD20'] = df['Close'].rolling(20).std()
    df['BB_UPPER'] = df['SMA20'] + 2 * df['STD20']
    df['BB_LOWER'] = df['SMA20'] - 2 * df['STD20']

    df = df.loc[start_date:]

    df_base = df[df.index.year == start_year]
    단순수익률 = (df_base.iloc[-1]['Close'] / df_base.iloc[0]['Close'] - 1) * 100
    단순_기간_수익률_리스트.append(단순수익률)

    # =========================
    # 매수 로직 (변경 없음)
    # =========================
    buy_signals_all = []

    for i in range(1, len(df)):
        prev_close = df['Close'].iloc[i - 1]
        curr_close = df['Close'].iloc[i]

        prev_bb_lower = df['BB_LOWER'].iloc[i - 1]
        curr_bb_lower = df['BB_LOWER'].iloc[i]

        curr_sma10 = df['SMA10'].iloc[i]
        curr_sma20 = df['SMA20'].iloc[i]

        condition_ma = (
            curr_close < curr_sma10 and
            curr_close < curr_sma20
        )

        condition_bb = (
            prev_close < prev_bb_lower and
            curr_close > curr_bb_lower
        )

        if condition_bb:
            buy_signals_all.append(i)

    buy_signals_start_year = [
        i for i in buy_signals_all if df.index[i].year == start_year
    ]

    signal_returns = []
    signal_count = 0
    hold_ranges = []

    # =========================================================
    # 매도 로직 (신규 조건)
    # =========================================================
    for buy_idx in buy_signals_start_year:

        buy_price = df.iloc[buy_idx]['Close']
        buy_date = df.index[buy_idx]

        sell_date = None
        sell_price = None

        # 🔵 12월 이후 블린저 상단 돌파 찾기
        for i in range(buy_idx + 1, len(df)):

            current_date = df.index[i]

            # 12월 이후만 체크
            if current_date.month < 12:
                continue

            prev_close = df['Close'].iloc[i - 1]
            curr_close = df['Close'].iloc[i]

            prev_bb_upper = df['BB_UPPER'].iloc[i - 1]
            curr_bb_upper = df['BB_UPPER'].iloc[i]

            if prev_close < prev_bb_upper and curr_close > curr_bb_upper:
                sell_date = current_date
                sell_price = curr_close
                break

        # 🔵 상단 돌파 못하면 기간 말일 매도
        if sell_date is None:
            sell_date = df.index[df.index <= sell_deadline][-1]
            sell_price = df.loc[sell_date, 'Close']

        수익률 = (sell_price / buy_price - 1) * 100
        보유일 = (sell_date - buy_date).days

        signal_returns.append(수익률)
        signal_count += 1

        hold_ranges.append((buy_date, sell_date))
        current_hold = calculate_current_hold(buy_date, hold_ranges)

        send_message(
            f"{code} | 매수 {buy_date.date()} "
            f"종가:{buy_price:.0f} | "
            f"BB하단:{df.iloc[buy_idx]['BB_LOWER']:.0f} → "
            f"매도 {sell_date.date()} {sell_price:.0f} | "
            f"수익률 {수익률:.2f}% | "
            f"보유 {보유일}일 | HOLD {current_hold}"
        )

    이동평균_수익률 = sum(signal_returns)
    이동평균_수익률_리스트.append(이동평균_수익률)

    max_hold = calculate_max_hold(hold_ranges)

    signal_count_dict[code] = signal_count
    hold_count_dict[code] = max_hold

    send_message(
        f"{code}({get_stock_name(code)}) 요약 | "
        f"단순: {단순수익률:.2f}% | "
        f"전략: {이동평균_수익률:.2f}% | "
        f"Signal: {signal_count} | "
        f"HOLD: {max_hold}"
    )

# =========================================================
# Summary
# =========================================================
send_message(
    f"✅ 전체 완료 | "
    f"단순수익률({start_year}): {np.mean(단순_기간_수익률_리스트):.2f}% | "
    f"전략수익률: {np.mean(이동평균_수익률_리스트):.2f}% | "
    f"Signal: {sum(signal_count_dict.values())} | "
    f"HOLD: {max(hold_count_dict.values())}"
)