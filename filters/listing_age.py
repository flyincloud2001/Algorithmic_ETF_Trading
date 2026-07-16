# 篩選出上市至少15年的ETF

from datetime import datetime, timezone

import yfinance as yf

# 最低上市年數門檻
MIN_LISTING_YEARS = 15
# 一年的平均天數（含閏年）
DAYS_PER_YEAR = 365.25


def passes_listing_age(symbol: str) -> bool:
    """判斷單一ETF是否上市滿15年。"""
    try:
        hist = yf.Ticker(symbol).history(period="max", auto_adjust=True)

        if hist is None or hist.empty:
            return False

        # 歷史資料最早一筆的日期視為上市日期
        listing_date = hist.index[0]
        if listing_date.tzinfo is not None:
            now = datetime.now(timezone.utc).astimezone(listing_date.tzinfo)
        else:
            now = datetime.now()

        years_listed = (now - listing_date).days / DAYS_PER_YEAR

        return years_listed >= MIN_LISTING_YEARS
    except Exception:
        return False
