# 這份檔案用來抓取印尼IDX交易所所有ETF代碼

import time

import pandas as pd
import requests
import yfinance as yf

# IDX內部API網址
IDX_API_URL = "https://www.idx.co.id/umbraco/Surface/ETFData/GetEtfListAll"

# IDX ETF清單頁面網址（內部API失敗時的備援）
IDX_ETF_PAGE_URL = "https://www.idx.co.id/en/market-data/exchanged-traded-fund-etf-data/exchange-traded-fund-etf-list"

# 偽裝完整瀏覽器的headers，避免被拒絕
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.idx.co.id/",
}

# 名稱必須排除的關鍵字（槓桿、反向ETF）
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "LEVERAGED", "BEAR", "SHORT", "2X", "3X")

# 可能包含代碼的欄位名稱關鍵字
CODE_COLUMN_KEYWORDS = ("CODE", "STOCKCODE", "ETFCODE", "SYMBOL", "KODE")
# 可能包含名稱的欄位名稱關鍵字
NAME_COLUMN_KEYWORDS = ("NAME", "NAMA")

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


def _extract_from_records(records) -> list[str]:
    """從JSON資料（list of dict）中動態找出代碼與名稱欄位，取出候選代碼。"""
    if not records:
        return []

    sample_keys = list(records[0].keys())
    code_column = _find_column(sample_keys, CODE_COLUMN_KEYWORDS)

    if code_column is None:
        # 找不到代碼欄位時，印出所有欄位名稱以便除錯
        print(f"Error: could not find code column in IDX API response, available columns: {sample_keys}")
        return []

    name_column = _find_column(sample_keys, NAME_COLUMN_KEYWORDS)

    codes = []
    for record in records:
        code = record.get(code_column)

        if code is None or str(code).strip() == "":
            continue

        if name_column is not None and _name_is_excluded(record.get(name_column)):
            continue

        codes.append(str(code).strip())

    return codes


def _extract_from_tables(tables) -> list[str]:
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


def _fetch_from_idx_api() -> list[str]:
    """第一步：呼叫IDX內部API，取得ETF清單。"""
    response = requests.get(IDX_API_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    try:
        payload = response.json()
        records = payload.get("data", payload) if isinstance(payload, dict) else payload
        return _extract_from_records(records)
    except ValueError:
        # 回應不是JSON，改用pandas.read_html()解析
        tables = pd.read_html(response.text)
        return _extract_from_tables(tables)


def _fetch_from_idx_page() -> list[str]:
    """第二步：IDX內部API失敗時，改用IDX ETF清單頁面備援。"""
    response = requests.get(IDX_ETF_PAGE_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)
    return _extract_from_tables(tables)


def _verify_and_build_symbols(codes) -> list[str]:
    """把代碼加上.JK後綴，並逐一用yfinance驗證是否為有效ETF。"""
    symbols = []
    for code in codes:
        symbol = f"{code}.JK"

        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def get_id_etf_symbols() -> list[str]:
    """回傳印尼IDX交易所所有ETF代碼的清單（yfinance使用的.JK後綴格式）。"""
    try:
        codes = _fetch_from_idx_api()

        if not codes:
            codes = _fetch_from_idx_page()

        symbols = _verify_and_build_symbols(codes)
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Indonesia ETF symbol list ({e})")
        return []
