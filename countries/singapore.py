# 這份檔案用來抓取新加坡SGX交易所所有ETF代碼

import time

import pandas as pd
import requests
import yfinance as yf

# Wikipedia上新加坡SGX ETF清單頁面網址
SGX_ETF_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_Singapore_exchange-traded_funds"

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 名稱必須排除的關鍵字（反向、放空、槓桿ETF）
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "BEAR", "SHORT", "LEVERAGED", "2X", "3X")

# 可能包含ticker代碼的欄位名稱關鍵字
TICKER_COLUMN_KEYWORDS = ("SYMBOL", "TICKER", "CODE", "SGX")

# 每次用yfinance驗證代碼之間的等待秒數
VERIFY_DELAY_SECONDS = 0.3


def get_sg_etf_symbols() -> list[str]:
    """回傳新加坡SGX交易所所有ETF代碼的清單（yfinance使用的.SI後綴格式）。"""
    try:
        response = requests.get(SGX_ETF_WIKI_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        tables = pd.read_html(response.text)

        candidate_symbols = []
        for table in tables:
            # 印出所有找到的表格欄位名稱以便除錯
            print(f"Found table columns: {list(table.columns)}")

            ticker_column = next(
                (
                    col
                    for col in table.columns
                    if any(keyword in str(col).upper() for keyword in TICKER_COLUMN_KEYWORDS)
                ),
                None,
            )

            if ticker_column is None:
                continue

            # 嘗試找出名稱欄位，用來過濾反向、放空、槓桿ETF
            name_column = next((col for col in table.columns if "NAME" in str(col).upper()), None)

            for _, row in table.iterrows():
                ticker = row.get(ticker_column)

                if pd.isna(ticker):
                    continue

                ticker = str(ticker).strip().upper()

                if not ticker:
                    continue

                if name_column is not None:
                    name = row.get(name_column)
                    if not pd.isna(name) and any(
                        keyword in str(name).upper() for keyword in EXCLUDED_NAME_KEYWORDS
                    ):
                        continue

                candidate_symbols.append(f"{ticker}.SI")

        # 用yfinance逐一驗證代碼是否有效，驗證失敗或資料為空的代碼直接跳過
        symbols = []
        for symbol in candidate_symbols:
            try:
                hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
                if hist is not None and not hist.empty:
                    symbols.append(symbol)
            except Exception:
                pass

            time.sleep(VERIFY_DELAY_SECONDS)

        # 去除重複，同時保留原始順序
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: exception while fetching Singapore ETF symbols ({e})")
        return []
