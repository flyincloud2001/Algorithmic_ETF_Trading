# 這份檔案用來抓取越南HOSE交易所所有ETF代碼

import time

import pandas as pd
import requests
import yfinance as yf

# stockanalysis.com上越南ETF清單頁面網址
STOCKANALYSIS_URL = "https://stockanalysis.com/list/vietnam-etfs/"

# stockanalysis.com解析失敗時使用的靜態備援代碼清單
STATIC_FALLBACK_TICKERS = (
    "E1VFVN30",
    "FUEVFVND",
    "FUESSVFL",
    "FUESSV30",
    "FUEVN100",
    "FUEDCMID",
    "FUEIP100",
    "FUESSV50",
    "DCDS",
    "VFMVSF",
)

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


def _fetch_codes_from_stockanalysis() -> list[str]:
    """第一步：從stockanalysis.com解析越南ETF清單，取出候選代碼。"""
    response = requests.get(STOCKANALYSIS_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

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


def _verify_and_build_symbols(codes) -> list[str]:
    """把代碼加上.VN後綴，並逐一用yfinance驗證是否為有效ETF。"""
    symbols = []
    for code in codes:
        if code is None or (isinstance(code, float) and pd.isna(code)):
            continue

        code = str(code).strip()
        if not code:
            continue

        symbol = f"{code}.VN"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_vn_etf_symbols() -> list[str]:
    """回傳越南HOSE交易所所有ETF代碼的清單（yfinance使用的.VN後綴格式）。"""
    try:
        codes = _fetch_codes_from_stockanalysis()
        symbols = _verify_and_build_symbols(codes)

        if symbols:
            return list(dict.fromkeys(symbols))

        print("Warning: no ETF codes found on stockanalysis.com, falling back to static list")
    except Exception as e:
        print(f"Warning: could not fetch ETF list from stockanalysis.com ({e}), falling back to static list")

    try:
        symbols = _verify_and_build_symbols(STATIC_FALLBACK_TICKERS)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Vietnam ETF symbol list ({e})")
        return []
