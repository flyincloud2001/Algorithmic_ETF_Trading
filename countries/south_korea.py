# 這份檔案用來抓取韓國KRX交易所所有ETF代碼

import pandas as pd
from pykrx import stock

# 名稱必須排除的關鍵字（槓桿、反向ETF）
EXCLUDED_NAME_KEYWORDS = ("레버리지", "인버스", "2X", "3X")


def get_kr_etf_symbols() -> list[str]:
    """回傳韓國KRX交易所所有ETF代碼的清單（yfinance使用的.KS後綴格式）。"""
    try:
        today = pd.Timestamp.today().strftime("%Y%m%d")

        # 取得所有ETF代碼清單（6位數字代碼）
        tickers = stock.get_etf_ticker_list(today)

        symbols = []
        for ticker in tickers:
            # 逐一取得ETF名稱，用來過濾槓桿、反向ETF
            name = stock.get_market_ticker_name(ticker)

            if not name:
                continue

            if any(keyword in name for keyword in EXCLUDED_NAME_KEYWORDS):
                continue

            symbols.append(f"{ticker}.KS")

        # 去除重複，同時保留原始順序
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: exception while fetching South Korea ETF symbol list ({e})")
        return []
