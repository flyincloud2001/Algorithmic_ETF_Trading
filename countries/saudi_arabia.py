# 這份檔案用來抓取沙烏地阿拉伯Saudi Exchange (Tadawul)所有ETF代碼

import time

import yfinance as yf

# 沙烏地ETF代碼掃描範圍（連續4位數字，從9400開始）
SCAN_RANGE_START = 9400
SCAN_RANGE_END = 9450

# 已知的沙烏地ETF代碼備援清單，不需驗證直接加入
KNOWN_FALLBACK_CODES = [
    "9400",
    "9401",
    "9402",
    "9403",
    "9404",
    "9405",
    "9406",
    "9407",
    "9408",
    "9409",
    "9410",
    "9411",
    "9412",
]

# 每次用yfinance驗證代碼之間的等待秒數
VERIFY_DELAY_SECONDS = 0.3

# 名稱必須排除的關鍵字（槓桿、反向ETF）
EXCLUDED_NAME_KEYWORDS = ("INVERSE", "LEVERAGED", "BEAR", "SHORT", "2X", "3X")


def _scan_range() -> list[str]:
    """掃描9400到9450的代碼範圍，用yfinance驗證每個代碼是否為有效ETF。"""
    symbols = []
    for code in range(SCAN_RANGE_START, SCAN_RANGE_END + 1):
        symbol = f"{code}.SR"
        try:
            hist = yf.Ticker(symbol).history(period="5d", auto_adjust=True)
            if hist is not None and not hist.empty:
                symbols.append(symbol)
        except Exception:
            pass

        time.sleep(VERIFY_DELAY_SECONDS)

    return symbols


def _name_is_excluded(symbol: str) -> bool:
    """盡力查詢ETF名稱，判斷是否含有槓桿、反向等應排除的關鍵字，查詢失敗時視為不排除。"""
    try:
        info = yf.Ticker(symbol).info
        name = info.get("longName") or info.get("shortName") or ""
    except Exception:
        return False

    if not name:
        return False

    return any(keyword in name.upper() for keyword in EXCLUDED_NAME_KEYWORDS)


def get_sa_etf_symbols() -> list[str]:
    """回傳沙烏地阿拉伯Saudi Exchange所有ETF代碼的清單（yfinance使用的.SR後綴格式）。"""
    scanned_symbols = []
    try:
        scanned_symbols = _scan_range()
    except Exception as e:
        print(f"Warning: exception while scanning Tadawul ETF code range ({e})")

    fallback_symbols = [f"{code}.SR" for code in KNOWN_FALLBACK_CODES]

    # 由於ETF數量少，yfinance存在性驗證本身就是最主要的過濾器；
    # 名稱關鍵字排除是盡力而為的第二層過濾，查詢失敗時不排除該代碼
    combined_symbols = list(dict.fromkeys(scanned_symbols + fallback_symbols))

    symbols = []
    for symbol in combined_symbols:
        if not symbol:
            continue

        if _name_is_excluded(symbol):
            continue

        symbols.append(symbol)

    return list(dict.fromkeys(symbols))
