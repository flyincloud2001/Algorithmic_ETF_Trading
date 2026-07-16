# 這份檔案用來抓取智利Bolsa de Santiago所有ETF代碼

import time

import pandas as pd
import requests
import yfinance as yf

# stockanalysis.com上智利ETF清單頁面網址
STOCKANALYSIS_URL = "https://stockanalysis.com/list/chilean-etfs/"

# Wikipedia備援頁面網址（stockanalysis.com失敗時使用）
WIKI_FALLBACK_URL = "https://en.wikipedia.org/wiki/List_of_Chilean_exchange-traded_funds"

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 名稱必須排除的關鍵字（槓桿、反向ETF）
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "LEVERAGED", "BEAR", "SHORT", "2X", "3X")

# 可能包含代碼的欄位名稱關鍵字
CODE_COLUMN_KEYWORDS = ("SYMBOL", "TICKER", "CODE")
# 可能包含名稱的欄位名稱關鍵字
NAME_COLUMN_KEYWORDS = ("NAME",)

# 每次用yfinance驗證代碼之間的等待秒數
VERIFY_DELAY_SECONDS = 0.3


def _find_column(keys, keywords):
    """依關鍵字動態找出對應的欄位名稱，找不到則回傳None。"""
    for key in keys:
        key_upper = str(key).upper()
        if any(keyword in key_upper for keyword in keywords):
            return key
    return None


def _name_is_excluded(name) -> bool:
    """判斷名稱是否含有槓桿、反向等應排除的關鍵字。"""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    return any(keyword in str(name).upper() for keyword in EXCLUDED_NAME_KEYWORDS)


def _extract_codes_from_tables(tables) -> list[str]:
    """從HTML表格中動態找出代碼與名稱欄位，取出候選代碼。"""
    codes = []
    for table in tables:
        columns = [str(col) for col in table.columns]
        # 印出找到的表格欄位名稱以便除錯
        print(f"Found table columns: {columns}")

        code_column = _find_column(columns, CODE_COLUMN_KEYWORDS)
        if code_column is None:
            continue

        name_column = _find_column(columns, NAME_COLUMN_KEYWORDS)

        for _, row in table.iterrows():
            code = row.get(code_column)

            if pd.isna(code):
                continue

            code = str(code).strip()
            if not code:
                continue

            if name_column is not None and _name_is_excluded(row.get(name_column)):
                continue

            codes.append(code)

    return codes


def _fetch_from_stockanalysis() -> list[str]:
    """第一步：從stockanalysis.com解析智利ETF清單。"""
    response = requests.get(STOCKANALYSIS_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    return _extract_codes_from_tables(tables)


def _fetch_from_wikipedia() -> list[str]:
    """第二步：stockanalysis.com失敗時，改用Wikipedia備援。"""
    response = requests.get(WIKI_FALLBACK_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    return _extract_codes_from_tables(tables)


def _verify_and_build_symbols(codes) -> list[str]:
    """把代碼加上.SN後綴，並逐一用yfinance驗證是否為有效ETF。"""
    symbols = []
    for code in codes:
        symbol = f"{code}.SN"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_cl_etf_symbols() -> list[str]:
    """回傳智利Bolsa de Santiago所有ETF代碼的清單（yfinance使用的.SN後綴格式）。"""
    try:
        codes = _fetch_from_stockanalysis()

        if not codes:
            codes = _fetch_from_wikipedia()

        symbols = _verify_and_build_symbols(codes)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Chile ETF symbol list ({e})")
        return []
