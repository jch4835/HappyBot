
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

    t_now_ny = t_now_ny + datetime.timedelta(days=4)

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
          

t_now_ny = None
t_9 = None
t_start = None
t_buy = None
t_sell = None
t_exit = None
us_holidays = holidays.US()

get_trading_times()            

if t_now_ny in us_holidays:
    holiday_name = us_holidays[t_now_ny]
    print(f"{t_now_ny} (미국 공휴일: {holiday_name}) ⇒ 프로그램 종료")
else:
    print(f"{t_now_ny} (NYSE 휴장일 / 주말) ⇒ 프로그램 종료")

# if t_9 == None:
#     print(f"{t_now_ny.date()}은(는) 공휴일 ==> 프로그램 종료.")

# if t_now_ny.weekday() >= 5:  # 토요일이나 일요일이면 자동 종료
#     print("주말!!! 프로그램 종료.")