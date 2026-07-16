# 這份檔案用來抓取台灣TWSE所有ETF代碼

import pandas as pd
import requests

# TWSE官方開放資料API：基金基本資料彙總表
TWSE_API_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap47_L"

# Wikipedia備援頁面網址（TWSE官方API失敗時依序嘗試）
WIKI_FALLBACK_URLS = (
    "https://en.wikipedia.org/wiki/List_of_Taiwan_exchange-traded_funds",
    "https://zh.wikipedia.org/wiki/臺灣指數股票型基金列表",
)

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 名稱必須排除的關鍵字（槓桿、反向ETF）。中文關鍵字需保留原文，用來比對中文基金名稱
EXCLUDED_NAME_KEYWORDS = (
    "槓桿",
    "反向",
    "放空",
    "BEAR",
    "INVERSE",
    "LEVERAGED",
    "2X",
    "3X",
    "2倍",
    "3倍",
)

# 可能包含基金代號、名稱、上市日期的欄位名稱關鍵字
CODE_COLUMN_KEYWORDS = ("基金代號", "代號", "CODE", "SYMBOL", "TICKER")
NAME_COLUMN_KEYWORDS = ("基金中文名稱", "基金名稱", "名稱", "NAME")
LISTING_DATE_COLUMN_KEYWORDS = ("上市日期", "上市", "LISTING DATE", "DATE")


def _find_column(keys, keywords):
    """依關鍵字動態找出對應的欄位名稱，找不到則回傳None。"""
    for key in keys:
        key_upper = str(key).upper()
        if any(keyword.upper() in key_upper for keyword in keywords):
            return key
    return None


def _name_is_excluded(name) -> bool:
    """判斷名稱是否含有槓桿、反向等應排除的關鍵字。"""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    name_str = str(name).upper()
    return any(keyword.upper() in name_str for keyword in EXCLUDED_NAME_KEYWORDS)


def _fetch_from_twse_api() -> list[str]:
    """呼叫TWSE官方開放資料API，取得基金基本資料彙總表並解析出ETF代碼。"""
    response = requests.get(TWSE_API_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    records = response.json()

    if not records:
        raise ValueError("TWSE API returned an empty list")

    sample_keys = list(records[0].keys())
    code_column = _find_column(sample_keys, CODE_COLUMN_KEYWORDS)

    if code_column is None:
        # 找不到代號欄位時，印出所有欄位名稱以便除錯
        print(f"Error: could not find fund code column, available columns: {sample_keys}")
        raise ValueError("Fund code column not found in TWSE API response")

    name_column = _find_column(sample_keys, NAME_COLUMN_KEYWORDS)
    # 上市日期欄位目前只用於確認資料表結構，暫不作為篩選依據
    _listing_date_column = _find_column(sample_keys, LISTING_DATE_COLUMN_KEYWORDS)

    symbols = []
    for record in records:
        code = record.get(code_column)

        if code is None or str(code).strip() == "":
            continue

        code = str(code).strip()

        if name_column is not None and _name_is_excluded(record.get(name_column)):
            continue

        symbols.append(f"{code}.TW")

    return symbols


def _fetch_from_wikipedia() -> list[str]:
    """TWSE官方API失敗時，依序嘗試Wikipedia頁面備援。"""
    for url in WIKI_FALLBACK_URLS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            tables = pd.read_html(response.text)
        except Exception:
            continue

        symbols = []
        for table in tables:
            columns = [str(col) for col in table.columns]
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

                symbols.append(f"{code}.TW")

        if symbols:
            return symbols

    return []


def get_tw_etf_symbols() -> list[str]:
    """回傳台灣TWSE所有ETF代碼的清單（yfinance使用的.TW後綴格式）。"""
    try:
        symbols = _fetch_from_twse_api()
        if symbols:
            return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Warning: could not fetch ETF list from TWSE official API ({e}), falling back to Wikipedia")

    try:
        symbols = _fetch_from_wikipedia()
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Taiwan ETF symbol list from either source ({e})")
        return []
