# 這份檔案制定了某一國家ETF低波動率的標準
# 低波動率的標準是: 用過去10年收盤對收盤的日報酬算出年化標準差作為排名依據，再篩選出排名前20%的ETF

import math

import yfinance as yf

# 計算資料不足的最少收盤價筆數門檻
MIN_REQUIRED_ROWS = 500
# 年化波動率使用的交易日數
TRADING_DAYS_PER_YEAR = 252
# 取排名前20%的比例
TOP_PERCENTAGE = 0.2


def get_annualized_volatility(symbol: str) -> float | None:
    """計算單一ETF的年化波動率，供外部排名使用。"""
    try:
        hist = yf.Ticker(symbol).history(period="10y", auto_adjust=True)

        if hist is None or len(hist) < MIN_REQUIRED_ROWS:
            return None

        # 收盤對收盤的日報酬率
        daily_returns = hist["Close"].pct_change()

        # 年化波動率 = 日報酬率標準差 × sqrt(252)
        annualized_volatility = daily_returns.std() * math.sqrt(TRADING_DAYS_PER_YEAR)

        return float(annualized_volatility)
    except Exception:
        return None


def filter_low_volatility(symbols: list[str]) -> list[str]:
    """輸入一組ETF代碼清單，回傳年化波動率排名前20%的清單。"""
    # 計算每個symbol的年化波動率，過濾掉抓取失敗或資料不足的symbol
    volatilities = []
    for symbol in symbols:
        volatility = get_annualized_volatility(symbol)
        if volatility is not None:
            volatilities.append((symbol, volatility))

    if not volatilities:
        return []

    # 依年化波動率由低到高排序
    volatilities.sort(key=lambda item: item[1])

    # 取前20%
    top_count = math.ceil(len(volatilities) * TOP_PERCENTAGE)

    return [symbol for symbol, _volatility in volatilities[:top_count]]
