# 這份檔案用來抓取土耳其Borsa Istanbul所有ETF代碼

import time

import pandas as pd
import requests
import yfinance as yf

# TEFAS官方API網址
TEFAS_API_URL = "https://www.tefas.gov.tr/api/funds/fonGnlBlgSiraliGetir"

# 查詢參數，fontip為BYF代表Exchange Traded Funds分類
TEFAS_API_PARAMS = {"fontip": "BYF"}

# 偽裝瀏覽器的headers，避免被拒絕
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.tefas.gov.tr/",
}

# 名稱必須排除的關鍵字（槓桿、反向ETF）。土耳其文關鍵字需保留原文才能比對土耳其文基金名稱
EXCLUDED_NAME_KEYWORDS = (
    "KALDIR",
    "TERS",
    "INVERSE",
    "LEVERAGED",
    "BEAR",
    "SHORT",
    "2X",
    "3X",
)

# 每次用yfinance驗證代碼之間的等待秒數
VERIFY_DELAY_SECONDS = 0.3


def _name_is_excluded(name) -> bool:
    """判斷名稱是否含有槓桿、反向等應排除的關鍵字。"""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return False
    return any(keyword in str(name).upper() for keyword in EXCLUDED_NAME_KEYWORDS)


def get_tr_etf_symbols() -> list[str]:
    """回傳土耳其Borsa Istanbul所有ETF代碼的清單（yfinance使用的.IS後綴格式）。"""
    try:
        response = requests.get(TEFAS_API_URL, headers=HEADERS, params=TEFAS_API_PARAMS, timeout=30)
        response.raise_for_status()
        records = response.json().get("data", [])

        # 先用基金代碼、名稱做篩選，減少之後不必要的yfinance驗證次數
        candidate_symbols = []
        for record in records:
            code = record.get("FONKODU")

            if code is None or str(code).strip() == "":
                continue

            code = str(code).strip()

            if _name_is_excluded(record.get("FONUNVAN")):
                continue

            candidate_symbols.append(f"{code}.IS")

        # 用yfinance逐一驗證代碼是否有效，驗證失敗或資料為空的代碼直接跳過
        symbols = []
        for symbol in candidate_symbols:
            try:
                hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
                if hist is not None and not hist.empty:
                    symbols.append(symbol)
            except Exception:
                pass

            time.sleep(VERIFY_DELAY_SECONDS)

        # 去除重複，同時保留原始順序
        return list(dict.fromkeys(symbols))
    except Exception as e:
        print(f"Error: could not fetch Turkey ETF symbol list from TEFAS API ({e})")
        return []
