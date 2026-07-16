# 這份檔案用來抓取巴西B3交易所所有ETF代碼

import base64
import json

import pandas as pd
import requests

# B3官方內部API的基本查詢參數
B3_API_PARAMS = {"language": "pt-br", "pageNumber": 1, "pageSize": 500, "typeFund": "ETF"}

# B3備援頁面網址（官方API失敗時使用）
B3_FALLBACK_URL = "https://sistemaswebb3-listados.b3.com.br/fundsListedPage/ETF"

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 名稱必須排除的關鍵字（槓桿、反向ETF）。葡萄牙文關鍵字需保留原文才能比對葡萄牙文基金名稱
EXCLUDED_NAME_KEYWORDS = (
    "ALAVANCADO",
    "INVERSO",
    "INVERSE",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "2X",
    "3X",
)

# 可能包含ticker代碼的欄位名稱關鍵字（備援表格解析用）
TICKER_COLUMN_KEYWORDS = ("TICKER", "CODE", "CODIGO", "SYMBOL")
# 可能包含基金名稱的欄位名稱關鍵字
NAME_COLUMN_KEYWORDS = ("NAME", "NOME")


def _name_is_excluded(name) -> bool:
    """判斷名稱是否含有槓桿、反向等應排除的關鍵字。"""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    name_upper = str(name).upper()
    return any(keyword in name_upper for keyword in EXCLUDED_NAME_KEYWORDS)


def _fetch_from_b3_api() -> list[str]:
    """呼叫B3官方內部API，取得ETF清單並解析出代碼。"""
    encoded = base64.b64encode(json.dumps(B3_API_PARAMS).encode()).decode()
    url = f"https://sistemaswebb3-listados.b3.com.br/fundsProxy/fundsCall/GetListedFundsSummaryByTypeFunds/{encoded}"

    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    payload = response.json()

    results = payload.get("results", [])

    symbols = []
    for result in results:
        ticker = result.get("fundTicker")

        if ticker is None or str(ticker).strip() == "":
            continue

        ticker = str(ticker).strip()

        # 動態找出名稱欄位，用來過濾槓桿、反向ETF
        name_key = next(
            (key for key in result.keys() if any(keyword in key.upper() for keyword in NAME_COLUMN_KEYWORDS)),
            None,
        )
        if name_key is not None and _name_is_excluded(result.get(name_key)):
            continue

        symbols.append(f"{ticker}.SA")

    return symbols


def _fetch_from_fallback_page() -> list[str]:
    """B3官方API失敗時，改用備援頁面的表格解析。"""
    response = requests.get(B3_FALLBACK_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    symbols = []
    for table in tables:
        columns = [str(col) for col in table.columns]
        ticker_column = next(
            (col for col in columns if any(keyword in col.upper() for keyword in TICKER_COLUMN_KEYWORDS)),
            None,
        )

        if ticker_column is None:
            continue

        name_column = next(
            (col for col in columns if any(keyword in col.upper() for keyword in NAME_COLUMN_KEYWORDS)),
            None,
        )

        for _, row in table.iterrows():
            ticker = row.get(ticker_column)

            if pd.isna(ticker):
                continue

            ticker = str(ticker).strip()
            if not ticker:
                continue

            if name_column is not None and _name_is_excluded(row.get(name_column)):
                continue

            symbols.append(f"{ticker}.SA")

    return symbols


def get_br_etf_symbols() -> list[str]:
    """回傳巴西B3交易所所有ETF代碼的清單（yfinance使用的.SA後綴格式）。"""
    try:
        symbols = _fetch_from_b3_api()
        if symbols:
            return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Warning: could not fetch ETF list from B3 official API ({e}), falling back to listed page")

    try:
        symbols = _fetch_from_fallback_page()
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Brazil ETF symbol list from either source ({e})")
        return []
