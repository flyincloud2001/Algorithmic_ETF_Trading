# 時區處理(美東時間 vs 台灣時間)

import pandas as pd

# 盤中交易時段的起訖時間（美東時間）
MARKET_OPEN_TIME = pd.Timestamp("09:30").time()
MARKET_CLOSE_TIME = pd.Timestamp("16:00").time()

# 盤前時段的起訖時間（美東時間）
PREMARKET_OPEN_TIME = pd.Timestamp("04:00").time()


def get_now_in_eastern() -> pd.Timestamp:
    """回傳現在的美東時間。"""
    return pd.Timestamp.now(tz="America/New_York")


def is_market_open() -> bool:
    """判斷現在美東時間是否在正常交易時段內（週一到週五 09:30-16:00）。"""
    now = get_now_in_eastern()

    if now.weekday() > 4:
        return False

    return MARKET_OPEN_TIME <= now.time() < MARKET_CLOSE_TIME


def is_premarket() -> bool:
    """判斷現在美東時間是否在盤前時段內（週一到週五 04:00-09:30）。"""
    now = get_now_in_eastern()

    if now.weekday() > 4:
        return False

    return PREMARKET_OPEN_TIME <= now.time() < MARKET_OPEN_TIME
