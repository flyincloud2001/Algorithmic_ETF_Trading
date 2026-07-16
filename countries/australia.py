# 這份檔案用來抓取澳洲ASX交易所所有ETF代碼

import io

import pandas as pd
import requests

# ASX官方上市證券清單CSV網址
ASX_LISTED_COMPANIES_URL = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 名稱必須排除的關鍵字（避險基金、管理型基金、槓桿、放空、反向ETF）
EXCLUDED_NAME_KEYWORDS = (
    "HEDGE FUND",
    "MANAGED FUND",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "INVERSE",
    "2X",
    "3X",
)


def get_au_etf_symbols() -> list[str]:
    """回傳澳洲ASX交易所所有ETF代碼的清單（yfinance使用的.AX後綴格式）。"""
    try:
        response = requests.get(ASX_LISTED_COMPANIES_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        # 這份CSV前兩行是說明文字，第三行才是真正的欄位標題，所以要跳過前兩行
        df = pd.read_csv(io.StringIO(response.text), skiprows=2)
    except Exception as e:
        print(f"Error: could not download or parse ASX listed securities list ({e})")
        return []

    symbols = []
    for _, row in df.iterrows():
        name = row.get("Company name")
        code = row.get("ASX code")

        if pd.isna(name) or pd.isna(code):
            continue

        name_upper = str(name).upper()
        code = str(code).strip()

        if not code:
            continue

        # 名稱必須包含"ETF"字樣才保留
        if "ETF" not in name_upper:
            continue

        # 排除避險基金、管理型基金、槓桿、放空、反向ETF
        if any(keyword in name_upper for keyword in EXCLUDED_NAME_KEYWORDS):
            continue

        symbols.append(f"{code}.AX")

    # 去除重複，同時保留原始順序
    return list(dict.fromkeys(symbols))
