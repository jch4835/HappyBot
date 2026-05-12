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

def get_buy_amount(symbol: str) -> int:
    """
    [매수금액 단일 공급 함수 - 하드코딩 버전]
    symbol 별 매수금액을 여기서만 관리한다.
    """
    # ⭐ 여기서 종목별 매수금액 설정 (여기만 수정하면 됨)
    BUY_AMOUNT_MAP = {
        "465580": 3_000_000,   # ACE 미국빅테크TOP7 Plus
        "381180": 3_000_000,   # TIGER 미국필라델피아반도체나스닥
        "457480": 3_000_000,   # ACE 테슬라벨류체인액티브
        "438080": 9_000_000,   # ACE 미국S&P500미국채혼합50액티브
        "438100": 9_000_000,   # ACE 미국나스닥100미국채혼합50액티브        
    }

    DEFAULT_BUY_AMOUNT = 3_000_000  # 설정 없는 종목 기본금액

    # 1️⃣ 종목별 목표 금액 가져오기
    target_amount = BUY_AMOUNT_MAP.get(symbol, DEFAULT_BUY_AMOUNT)
    send_message(f"{symbol} 목표 매수금액: {target_amount:,}원")
    return target_amount

symbol_list = ["465580","381180","457480","438080","438100"]

for sym in symbol_list:
    get_buy_amount(sym)