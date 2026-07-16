# 這份檔案用來抓取香港HKEX所有ETF代碼

import io

import pandas as pd
import requests

# HKEX官方ETF清單CSV網址
HKEX_ETF_LIST_URL = "https://www.hkex.com.hk/eng/etfrc/ListOfAllETF/ETFList.csv"

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 名稱必須排除的關鍵字（反向、放空、槓桿、做多、槓桿反向ETF）
EXCLUDED_NAME_KEYWORDS = (
    "INVERSE",
    "BEAR",
    "SHORT",
    "LEVERAGED",
    "BULL",
    "2X",
    "3X",
    "-2",
    "-3",
    "L&I",
)


def get_hk_etf_symbols() -> list[str]:
    """回傳香港HKEX所有ETF代碼的清單（yfinance使用的.HK後綴格式）。"""
    try:
        response = requests.get(HKEX_ETF_LIST_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()

        # 這份CSV編碼不固定，先試utf-8-sig，失敗再試latin-1
        try:
            df = pd.read_csv(io.BytesIO(response.content), encoding="utf-8-sig")
        except Exception:
            df = pd.read_csv(io.BytesIO(response.content), encoding="latin-1")

        # 印出所有欄位名稱以便除錯
        print(f"HKEX ETF list column names: {list(df.columns)}")

        # 動態找出股票代碼欄位與名稱欄位
        code_column = next((col for col in df.columns if "code" in col.lower()), None)
        name_column = next((col for col in df.columns if "name" in col.lower()), None)

        if code_column is None or name_column is None:
            print(f"Error: could not find code or name column, columns are {list(df.columns)}")
            return []
    except Exception as e:
        print(f"Error: could not download or parse HKEX ETF list ({e})")
        return []

    symbols = []
    for _, row in df.iterrows():
        code = row.get(code_column)
        name = row.get(name_column)

        if pd.isna(code) or pd.isna(name):
            continue

        name_upper = str(name).upper()

        # 排除反向、放空、槓桿ETF
        if any(keyword in name_upper for keyword in EXCLUDED_NAME_KEYWORDS):
            continue

        # 股票代碼補零至4位，再加上.HK後綴
        code_str = str(code).strip().split(".")[0].zfill(4)
        symbols.append(f"{code_str}.HK")

    # 去除重複，同時保留原始順序
    return list(dict.fromkeys(symbols))
