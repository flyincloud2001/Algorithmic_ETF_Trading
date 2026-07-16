# 這份檔案用來抓取瑞士SIX Swiss Exchange所有ETF代碼

import re
import time

import requests
import yfinance as yf

# 偽裝瀏覽器的User-Agent，避免被justETF拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# 取得動態counter用的搜尋頁網址
SEARCH_PAGE_URL = "https://www.justetf.com/en/search.html?search=ETFS"

# 從搜尋頁HTML中解析動態counter的正則表達式
COUNTER_PATTERN = r"(\d+)-1\.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel&search=ETFS&_wicket=1"

# POST請求固定的payload
POST_PAYLOAD = {
    "draw": 1,
    "start": 0,
    "length": -1,
    "lang": "en",
    "country": "CH",
    "universeType": "private",
    "defaultCurrency": "CHF",
}

# 名稱必須排除的關鍵字（槓桿、放空、反向ETF）
EXCLUDED_NAME_KEYWORDS = ("LEVERAGED", "SHORT", "INVERSE", "2X", "3X", "-2", "-3")

# 每次用yfinance驗證代碼之間的等待秒數
VERIFY_DELAY_SECONDS = 0.3


def get_ch_etf_symbols() -> list[str]:
    """回傳瑞士SIX Swiss Exchange所有ETF代碼的清單（yfinance使用的.SW後綴格式）。"""
    try:
        session = requests.Session()

        # 第一步：對justETF發送GET請求，取得動態counter
        get_response = session.get(SEARCH_PAGE_URL, headers=HEADERS, timeout=30)
        get_response.raise_for_status()

        counter_match = re.search(COUNTER_PATTERN, get_response.text)
        if counter_match:
            counter = counter_match.group(1)
        else:
            counter = "0"
            print("Warning: could not parse justETF dynamic counter, falling back to default value 0")

        # 第二步：用counter組出POST網址，取得完整ETF清單
        post_url = (
            f"https://www.justetf.com/en/search.html?{counter}"
            "-1.0-container-tabsContentContainer-tabsContentRepeater-1-container-content-etfsTablePanel"
            "&search=ETFS&_wicket=1"
        )

        post_response = session.post(post_url, headers=HEADERS, data=POST_PAYLOAD, timeout=30)
        post_response.raise_for_status()
        etf_list = post_response.json().get("data", [])

        # 先用名稱、代碼做篩選，減少之後不必要的yfinance驗證次數
        candidate_symbols = []
        for etf in etf_list:
            ticker = etf.get("ticker")
            name = etf.get("name")

            if not ticker or not name:
                continue

            name_upper = name.upper()

            # 名稱必須包含"ETF"字樣才保留
            if "ETF" not in name_upper:
                continue

            # 排除槓桿、放空、反向ETF
            if any(keyword in name_upper for keyword in EXCLUDED_NAME_KEYWORDS):
                continue

            candidate_symbols.append(f"{ticker}.SW")

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
        print(f"Error: exception while fetching Switzerland ETF symbol list ({e})")
        return []
