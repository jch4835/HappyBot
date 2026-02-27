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

    for market in ['NASDAQ', 'NYSE', 'AMEX']:
        try:
            # us = load_market(market)
            row = us[us['Symbol'] == code]
            if not row.empty:
                return row['Name'].values[0]
        except:
            continue

    return 'Not Found'

# =========================================================
# HOLD 계산 함수
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
# Parameters (🇺🇸 미국 ETF)
# =========================================================
code_list = ["QQQ"]

start_date = "2025-01-01"
end_date = "2025-12-31"
보유기간 = 13

start_year = pd.to_datetime(start_date).year
sell_deadline = pd.to_datetime(end_date)

moving_start_date = (
    pd.to_datetime(start_date) - pd.DateOffset(days=30)
).strftime("%Y-%m-%d")

send_message(f"🇺🇸 미국 ETF 백테스트 시작 (TQQQ): {start_date} ~ {end_date}")

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

    df['SMA10'] = df['Close'].rolling(10).mean()
    df['SMA20'] = df['Close'].rolling(20).mean()
    df = df.loc[start_date:]

    # -------------------------------
    # 단순 수익률
    # -------------------------------
    df_base = df[df.index.year == start_year]
    단순수익률 = (df_base.iloc[-1]['Close'] / df_base.iloc[0]['Close'] - 1) * 100
    단순_기간_수익률_리스트.append(단순수익률)

    # -------------------------------
    # 매수 시그널
    # -------------------------------
    buy_signals_all = []
    for i in range(1, len(df)):
        if (
            df['Close'].iloc[i - 1] < df['SMA10'].iloc[i - 1]
            and df['Close'].iloc[i] > df['SMA10'].iloc[i]
        ) or (
            df['Close'].iloc[i - 1] < df['SMA20'].iloc[i - 1]
            and df['Close'].iloc[i] > df['SMA20'].iloc[i]
        ):
            buy_signals_all.append(i)

    buy_signals_start_year = [
        i for i in buy_signals_all if df.index[i].year == start_year
    ]

    signal_returns = []
    signal_count = 0
    hold_ranges = []

    # -------------------------------
    # 매도 로직 (기존 그대로)
    # -------------------------------
    for buy_idx in buy_signals_start_year:
        buy_price = df.iloc[buy_idx]['Close']
        buy_date = df.index[buy_idx]

        sell_date = None
        sell_price = None
        수익률 = None

        for next_buy_idx in buy_signals_all:
            if next_buy_idx < buy_idx:
                continue

            sell_idx = next_buy_idx + 보유기간
            if sell_idx >= len(df):
                break

            candidate_date = df.index[sell_idx]
            if candidate_date > sell_deadline:
                break

            candidate_price = df.iloc[sell_idx]['Close']
            candidate_return = (candidate_price / buy_price - 1) * 100

            if candidate_return >= 0:
                sell_date = candidate_date
                sell_price = candidate_price
                수익률 = candidate_return
                break

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
            f"{code} | 매수 {buy_date.date()} ${buy_price:.2f} → "
            f"매도 {sell_date.date()} ${sell_price:.2f} | "
            f"수익률 {수익률:.2f}% | 보유 {보유일}일 | "
            f"HOLD {current_hold}"
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
# =
