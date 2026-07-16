# 這份檔案用來抓取美股（NASDAQ官方清單）所有ETF代碼

import requests

# NASDAQ官方上市清單網址
NASDAQ_LISTED_URL = "http://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED_URL = "http://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

# 各清單對應的代碼欄位名稱（nasdaqlisted叫"Symbol"，otherlisted叫"ACT Symbol"）
SYMBOL_COLUMN_NAMES = {
    NASDAQ_LISTED_URL: "Symbol",
    OTHER_LISTED_URL: "ACT Symbol",
}


def _fetch_etf_symbols(url: str) -> list[str]:
    """從單一NASDAQ官方清單網址抓取ETF代碼清單。"""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    lines = response.text.splitlines()
    # 第一行是標題列，最後兩行是檔案資訊，都要排除
    header = lines[0].split("|")
    data_lines = lines[1:-2]

    symbol_index = header.index(SYMBOL_COLUMN_NAMES[url])
    etf_index = header.index("ETF")

    symbols = []
    for line in data_lines:
        fields = line.split("|")
        if len(fields) <= max(symbol_index, etf_index):
            continue

        # 只保留ETF欄位值為"Y"的列
        if fields[etf_index] != "Y":
            continue

        symbol = fields[symbol_index]
        # 排除代碼包含"."或"$"的（特別股、權證等）
        if "." in symbol or "$" in symbol:
            continue

        symbols.append(symbol)

    return symbols


def get_us_etf_symbols() -> list[str]:
    """回傳美股所有ETF代碼的清單。"""
    all_symbols = []

    for url in (NASDAQ_LISTED_URL, OTHER_LISTED_URL):
        try:
            all_symbols.extend(_fetch_etf_symbols(url))
        except Exception as e:
            print(f"Warning: could not fetch ETF list from {url} ({e})")

    # 合併兩個來源並去除重複，同時保留原始順序
    return list(dict.fromkeys(all_symbols))
