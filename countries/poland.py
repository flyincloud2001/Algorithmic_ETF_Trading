# 這份檔案用來抓取波蘭GPW交易所所有ETF代碼

import pandas as pd
import requests

# GPW官方ETF全覽頁面網址
GPW_ETF_LIST_URL = "https://www.gpw.pl/etfs-full-view"

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# GPW官網解析失敗時使用的靜態備援代碼清單
STATIC_FALLBACK_TICKERS = (
    "ETFBCASH",
    "ETFBDIVPL",
    "ETFBM40TR",
    "ETFBNDXPL",
    "ETFBS80TR",
    "ETFBSPXPL",
    "ETFBTBSP",
    "ETFBTCPL",
    "ETFBW20ST",
    "ETFBW20TR",
    "ETFDAX",
    "ETFNATO",
    "ETFSP500",
)

# 波蘭文小計列的代碼值，需排除
SUBTOTAL_ROW_VALUE = "RAZEM"

# 代碼結尾必須排除的後綴（2倍放空、3倍槓桿、2倍槓桿）
EXCLUDED_SUFFIXES = ("2ST", "3LV", "2LV")

# 代碼中含有這些關鍵字也必須排除（反向、放空ETF）
EXCLUDED_KEYWORDS = ("INVERSE", "SHORT")


def _is_excluded(code: str) -> bool:
    """判斷代碼是否為應排除的槓桿、反向、放空ETF。"""
    if code.endswith(EXCLUDED_SUFFIXES):
        return True
    return any(keyword in code for keyword in EXCLUDED_KEYWORDS)


def _apply_filter(tickers) -> list[str]:
    """套用清理、排除小計列、排除槓桿反向關鍵字，並加上.WA後綴。"""
    symbols = []
    for ticker in tickers:
        if ticker is None or (isinstance(ticker, float) and pd.isna(ticker)):
            continue

        code = str(ticker).strip().upper()

        if not code or code == SUBTOTAL_ROW_VALUE:
            continue

        if _is_excluded(code):
            continue

        symbols.append(f"{code}.WA")

    return symbols


def _fetch_from_gpw() -> list[str]:
    """從GPW官方ETF全覽頁面解析出"Instrument"欄位的所有代碼。"""
    response = requests.get(GPW_ETF_LIST_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    tables = pd.read_html(response.text)

    tickers = []
    for table in tables:
        columns = [str(col) for col in table.columns]

        if not any("Instrument" in col for col in columns):
            continue

        # 印出找到的表格欄位名稱以便除錯
        print(f"Found table columns: {columns}")

        instrument_column = next(col for col in table.columns if "Instrument" in str(col))
        tickers.extend(table[instrument_column].tolist())

    return tickers


def get_pl_etf_symbols() -> list[str]:
    """回傳波蘭GPW交易所所有ETF代碼的清單（yfinance使用的.WA後綴格式）。"""
    try:
        tickers = _fetch_from_gpw()
        symbols = _apply_filter(tickers)

        if symbols:
            return list(dict.fromkeys(symbols))

        print("Warning: no ETF codes found on GPW page, falling back to static list")
        return list(dict.fromkeys(_apply_filter(STATIC_FALLBACK_TICKERS)))
    except Exception as e:
        print(f"Error: could not fetch Poland ETF symbol list from GPW ({e}), falling back to static list")
        return list(dict.fromkeys(_apply_filter(STATIC_FALLBACK_TICKERS)))
