# 這份檔案用來抓取加拿大（TSX、TSXV）交易所所有ETF代碼

import string
import time

import pandas as pd
import requests

# 偽裝瀏覽器的User-Agent，避免被eoddata.com拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 交易所代碼與對應的股票代碼後綴
EXCHANGE_SUFFIXES = {
    "TSX": ".TO",
    "TSXV": ".V",
}

# 排除的代碼類型：債券、特別股、認股權證
EXCLUDED_CODE_SUBSTRINGS = (".DB", ".PR", ".WT", ".RT")

# 每頁抓取之間的等待秒數
PAGE_INTERVAL_SECONDS = 0.2


def _build_url(exchange: str, letter: str) -> str:
    """依交易所與字母組成eoddata.com股票清單頁面網址。"""
    if letter == "A":
        return f"https://www.eoddata.com/stocklist/{exchange}.htm"
    return f"https://www.eoddata.com/stocklist/{exchange}/{letter}.htm"


def _fetch_page_symbols(exchange: str, letter: str) -> list[str]:
    """抓取單一交易所、單一字母頁面的ETF代碼。"""
    url = _build_url(exchange, letter)
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    symbols = []
    for table in tables:
        # 找出同時含有"Code"和"Name"欄位的表格
        if "Code" not in table.columns or "Name" not in table.columns:
            continue

        for _, row in table.iterrows():
            code = str(row["Code"])
            name = str(row["Name"])

            # 排除代碼含有債券、特別股、認股權證後綴的
            if any(substring in code for substring in EXCLUDED_CODE_SUBSTRINGS):
                continue

            # 名稱轉大寫後必須包含"ETF"字樣才保留
            if "ETF" not in name.upper():
                continue

            symbols.append(code + EXCHANGE_SUFFIXES[exchange])

    return symbols


def get_ca_etf_symbols() -> list[str]:
    """回傳TSX和TSXV所有ETF代碼的清單。"""
    all_symbols = []

    for exchange in EXCHANGE_SUFFIXES:
        for letter in string.ascii_uppercase:
            try:
                all_symbols.extend(_fetch_page_symbols(exchange, letter))
            except Exception as e:
                print(f"Warning: could not fetch {exchange} stock list for letter {letter} ({e})")

            time.sleep(PAGE_INTERVAL_SECONDS)

    # 合併兩個交易所結果並去除重複，同時保留原始順序
    return list(dict.fromkeys(all_symbols))
