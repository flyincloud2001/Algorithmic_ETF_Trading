# 這份檔案用來抓取印度NSE所有ETF代碼

import io
import re

import pandas as pd
import requests

# NSE官方ETF清單CSV網址
NSE_ETF_CSV_URL = "https://nsearchives.nseindia.com/content/equities/ETF_SECURITY_L.csv"

# Wikipedia上印度ETF清單頁面網址（NSE官方來源失敗時的備援）
WIKI_ETF_URL = "https://en.wikipedia.org/wiki/List_of_Indian_exchange-traded_funds"

# 偽裝完整瀏覽器的headers，避免被NSE官方網站拒絕
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.nseindia.com/",
}

# 名稱必須排除的關鍵字（槓桿、反向ETF）
EXCLUDED_NAME_KEYWORDS = ("LEVERAGED", "INVERSE", "BEAR", "SHORT", "2X", "3X")

# 可能包含ticker代碼的欄位名稱關鍵字（Wikipedia備援用）
TICKER_COLUMN_KEYWORDS = ("NSE", "SYMBOL", "TICKER")


def _apply_name_filter(df: pd.DataFrame, symbol_column: str) -> list[str]:
    """動態找出名稱欄位，排除槓桿、反向ETF後回傳有效的原始代碼清單。"""
    name_column = next((col for col in df.columns if "NAME" in str(col).upper()), None)

    symbols = []
    for _, row in df.iterrows():
        symbol = row.get(symbol_column)

        if pd.isna(symbol):
            continue

        symbol = str(symbol).strip()
        if not symbol:
            continue

        if name_column is not None:
            name = row.get(name_column)
            if not pd.isna(name) and any(
                keyword in str(name).upper() for keyword in EXCLUDED_NAME_KEYWORDS
            ):
                continue

        symbols.append(symbol)

    return symbols


def _fetch_from_nse() -> list[str]:
    """第一步：嘗試從NSE官方下載ETF清單CSV。"""
    response = requests.get(NSE_ETF_CSV_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(io.StringIO(response.text))

    if "SYMBOL" not in df.columns:
        raise ValueError("NSE ETF CSV does not contain a SYMBOL column")

    symbols = _apply_name_filter(df, "SYMBOL")
    return [f"{symbol}.NS" for symbol in symbols]


def _fetch_from_wikipedia() -> list[str]:
    """第二步：NSE官方來源失敗時，改用Wikipedia備援。"""
    response = requests.get(WIKI_ETF_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    symbols = []
    for table in tables:
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

        raw_symbols = _apply_name_filter(table, ticker_column)

        for raw_symbol in raw_symbols:
            # 從類似"NSE: LIQUIDBEES"的格式中擷取真正的代碼，一般欄位值則直接使用
            match = re.search(r"([A-Z0-9\-&]+)\s*$", raw_symbol.upper())
            ticker = match.group(1) if match else raw_symbol.upper()
            symbols.append(f"{ticker}.NS")

    return symbols


def get_in_etf_symbols() -> list[str]:
    """回傳印度NSE所有ETF代碼的清單（yfinance使用的.NS後綴格式）。"""
    try:
        symbols = _fetch_from_nse()
        if symbols:
            return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Warning: could not fetch ETF list from NSE official source ({e}), falling back to Wikipedia")

    try:
        symbols = _fetch_from_wikipedia()
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch India ETF symbol list from either source ({e})")
        return []
