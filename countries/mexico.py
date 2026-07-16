# 這份檔案用來抓取墨西哥BMV所有本地ETF代碼

import pandas as pd
import requests

# BMV官方TRAC頁面網址
BMV_TRAC_URL = "https://www.bmv.com.mx/en/markets/tracks"

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# BMV官網解析失敗時使用的靜態備援代碼清單
STATIC_FALLBACK_TICKERS = (
    "NAFTRACISHRS",
    "ILCTRACISHRS",
    "MEXTRAC09",
    "SMARTRC14",
    "DIABLOI10",
    "ANGEL10",
    "CHNTRAC11",
    "FIBRATC14",
    "DLRTRAC15",
    "PSOTRAC15",
    "QVGMEX18",
)

# 名稱或代碼必須排除的關鍵字（反向、槓桿ETF；ANGEL10是2倍槓桿）
EXCLUDED_KEYWORDS = (
    "INVERSE",
    "INVERSO",
    "DIABLO",
    "ANGEL",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "2X",
    "3X",
)


def _is_excluded(text) -> bool:
    """判斷文字是否含有反向、槓桿等應排除的關鍵字。"""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return False
    return any(keyword in str(text).upper() for keyword in EXCLUDED_KEYWORDS)


def _fetch_from_bmv() -> list[str]:
    """第一步：從BMV官方TRAC頁面解析所有表格的第一欄代碼。"""
    response = requests.get(BMV_TRAC_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    if not tables:
        raise ValueError("No tables found on BMV TRAC page")

    tickers = []
    for table in tables:
        if table.shape[1] < 1:
            continue

        # 每個表格的第一欄通常是NAME欄，BMV代碼由多個英數字母組成
        first_column = table.iloc[:, 0]

        for value in first_column:
            if pd.isna(value):
                continue

            # 去除空白後取完整字串作為代碼
            ticker = "".join(str(value).split())
            if ticker:
                tickers.append(ticker)

    return tickers


def _apply_filter(tickers) -> list[str]:
    """套用排除關鍵字與空值篩選，並加上.MX後綴。"""
    symbols = []
    for ticker in tickers:
        if ticker is None or (isinstance(ticker, float) and pd.isna(ticker)):
            continue

        ticker = str(ticker).strip()
        if not ticker:
            continue

        if _is_excluded(ticker):
            continue

        symbols.append(f"{ticker}.MX")

    return symbols


def get_mx_etf_symbols() -> list[str]:
    """回傳墨西哥BMV所有本地ETF代碼的清單（yfinance使用的.MX後綴格式）。"""
    try:
        tickers = _fetch_from_bmv()
        symbols = _apply_filter(tickers)
        if symbols:
            return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Warning: could not fetch ETF list from BMV official page ({e}), falling back to static list")

    try:
        symbols = _apply_filter(STATIC_FALLBACK_TICKERS)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not build Mexico ETF symbol list ({e})")
        return []
