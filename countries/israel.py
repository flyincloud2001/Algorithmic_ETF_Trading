# 這份檔案用來抓取以色列TASE交易所所有ETF代碼

import re
import time

import pandas as pd
import requests
import yfinance as yf

# TASE官方ETF頁面網址
TASE_ETF_PAGE_URL = "https://market.tase.co.il/en/market_data/etfs"

# justETF備援用的搜尋頁網址與動態counter正則表達式（與countries/uk.py相同邏輯）
JUSTETF_SEARCH_PAGE_URL = "https://www.justetf.com/en/search.html?search=ETFS"
JUSTETF_COUNTER_PATTERN = r"(\d+)-1\.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel&search=ETFS&_wicket=1"

# justETF POST請求固定的payload，country設為IL、defaultCurrency設為ILS
JUSTETF_POST_PAYLOAD = {
    "draw": 1,
    "start": 0,
    "length": -1,
    "lang": "en",
    "country": "IL",
    "universeType": "private",
    "defaultCurrency": "ILS",
}

# 偽裝完整瀏覽器的headers，避免被拒絕
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://market.tase.co.il/",
}

# 名稱必須排除的關鍵字（槓桿、反向ETF）。希伯來文關鍵字需保留原文才能比對希伯來文名稱
EXCLUDED_NAME_KEYWORDS = (
    "INVERSE",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "2X",
    "3X",
    "ממונף",
    "הפוך",
)

# 可能包含ETF代碼的欄位名稱關鍵字
CODE_COLUMN_KEYWORDS = ("NUMBER", "CODE", "SYMBOL", "ISIN")
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


def _fetch_codes_from_tase() -> list[str]:
    """第一步：從TASE官方ETF頁面解析出代碼。"""
    response = requests.get(TASE_ETF_PAGE_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    codes = []
    for table in tables:
        columns = [str(col) for col in table.columns]
        # 印出所有找到的表格欄位名稱以便除錯
        print(f"Found table columns: {columns}")

        code_column = _find_column(columns, CODE_COLUMN_KEYWORDS)
        if code_column is None:
            continue

        name_column = _find_column(columns, NAME_COLUMN_KEYWORDS)

        for _, row in table.iterrows():
            code = row.get(code_column)

            if pd.isna(code):
                continue

            # 以色列ETF代碼是純數字，去除小數點與空白
            code = str(code).strip().split(".")[0]
            if not code:
                continue

            if name_column is not None and _name_is_excluded(row.get(name_column)):
                continue

            codes.append(code)

    return codes


def _fetch_codes_from_justetf() -> list[str]:
    """第二步：TASE來源失敗時，改用justETF備援（與countries/uk.py相同邏輯）。"""
    session = requests.Session()

    get_response = session.get(JUSTETF_SEARCH_PAGE_URL, headers=HEADERS, timeout=30)
    get_response.raise_for_status()

    counter_match = re.search(JUSTETF_COUNTER_PATTERN, get_response.text)
    if counter_match:
        counter = counter_match.group(1)
    else:
        counter = "0"
        print("Warning: could not parse justETF dynamic counter, falling back to default value 0")

    post_url = (
        f"https://www.justetf.com/en/search.html?{counter}"
        "-1.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel"
        "&search=ETFS&_wicket=1"
    )

    post_response = session.post(post_url, headers=HEADERS, data=JUSTETF_POST_PAYLOAD, timeout=30)
    post_response.raise_for_status()
    etf_list = post_response.json().get("data", [])

    codes = []
    for etf in etf_list:
        ticker = etf.get("ticker")
        name = etf.get("name")

        if not ticker or not name:
            continue

        # 名稱必須包含"ETF"字樣才保留
        if "ETF" not in name.upper():
            continue

        if _name_is_excluded(name):
            continue

        codes.append(ticker)

    return codes


def _verify_and_build_symbols(codes) -> list[str]:
    """把代碼加上.TA後綴，並逐一用yfinance驗證是否為有效ETF。"""
    symbols = []
    for code in codes:
        symbol = f"{code}.TA"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_il_etf_symbols() -> list[str]:
    """回傳以色列TASE交易所所有ETF代碼的清單（yfinance使用的.TA後綴格式）。"""
    codes = []
    try:
        codes = _fetch_codes_from_tase()
    except Exception as e:
        print(f"Warning: could not fetch ETF list from TASE ({e}), falling back to justETF")

    if not codes:
        try:
            codes = _fetch_codes_from_justetf()
        except Exception as e:
            print(f"Error: could not fetch Israel ETF symbol list from either source ({e})")
            return []

    try:
        symbols = _verify_and_build_symbols(codes)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not verify Israel ETF symbols via yfinance ({e})")
        return []
