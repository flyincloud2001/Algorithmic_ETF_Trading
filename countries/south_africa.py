# 這份檔案用來抓取南非JSE所有ETF代碼

import io
import re
import time

import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup

# JSE ETF清單頁面網址
JSE_ETF_LIST_PAGE_URL = "https://www.jse.co.za/files/etf-list"

# 找不到頁面連結時的備援XLSX網址
FALLBACK_XLSX_URL = "https://www.jse.co.za/sites/default/files/media/documents/ETFList/ETF%20List%20v.53.xlsx"

# justETF備援用的搜尋頁網址與動態counter正則表達式（與countries/uk.py相同邏輯）
JUSTETF_SEARCH_PAGE_URL = "https://www.justetf.com/en/search.html?search=ETFS"
JUSTETF_COUNTER_PATTERN = r"(\d+)-1\.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel&search=ETFS&_wicket=1"

# justETF POST請求固定的payload，country設為ZA、defaultCurrency設為ZAR
JUSTETF_POST_PAYLOAD = {
    "draw": 1,
    "start": 0,
    "length": -1,
    "lang": "en",
    "country": "ZA",
    "universeType": "private",
    "defaultCurrency": "ZAR",
}

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 名稱必須排除的關鍵字（槓桿、反向ETF）
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "LEVERAGED", "BEAR", "SHORT", "2X", "3X")

# 可能包含股票代碼的欄位名稱關鍵字
CODE_COLUMN_KEYWORDS = ("CODE", "TICKER", "SYMBOL", "JSE")
# 可能包含名稱的欄位名稱關鍵字
NAME_COLUMN_KEYWORDS = ("NAME", "FUND", "ETF")

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


def _find_xlsx_url() -> str:
    """從JSE ETF清單頁面找出最新的XLSX下載連結，找不到則回傳備援網址。"""
    try:
        response = requests.get(JSE_ETF_LIST_PAGE_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if "ETFList" in href or href.lower().endswith(".xlsx"):
                if href.startswith("http"):
                    return href
                return f"https://www.jse.co.za{href}"
    except Exception:
        pass

    return FALLBACK_XLSX_URL


def _fetch_codes_from_jse() -> list[str]:
    """第一步：下載JSE的ETF清單XLSX並解析出代碼。"""
    xlsx_url = _find_xlsx_url()

    response = requests.get(xlsx_url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    df = pd.read_excel(io.BytesIO(response.content))

    # 印出所有欄位名稱以便除錯
    print(f"JSE ETF list column names: {list(df.columns)}")

    code_column = _find_column(df.columns, CODE_COLUMN_KEYWORDS)
    if code_column is None:
        raise ValueError(f"Could not find code column, available columns: {list(df.columns)}")

    name_column = _find_column(df.columns, NAME_COLUMN_KEYWORDS)

    codes = []
    for _, row in df.iterrows():
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


def _fetch_codes_from_justetf() -> list[str]:
    """第二步：JSE來源失敗時，改用justETF備援（與countries/uk.py相同邏輯）。"""
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
    """把代碼加上.JO後綴，並逐一用yfinance驗證是否為有效ETF。"""
    symbols = []
    for code in codes:
        symbol = f"{code}.JO"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_za_etf_symbols() -> list[str]:
    """回傳南非JSE所有ETF代碼的清單（yfinance使用的.JO後綴格式）。"""
    codes = []
    try:
        codes = _fetch_codes_from_jse()
    except Exception as e:
        print(f"Warning: could not fetch ETF list from JSE ({e}), falling back to justETF")

    if not codes:
        try:
            codes = _fetch_codes_from_justetf()
        except Exception as e:
            print(f"Error: could not fetch South Africa ETF symbol list from either source ({e})")
            return []

    try:
        symbols = _verify_and_build_symbols(codes)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not verify South Africa ETF symbols via yfinance ({e})")
        return []
