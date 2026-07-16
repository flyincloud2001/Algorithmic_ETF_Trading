# 制定一個合理的最低交易量，篩選出適合的ETF

import yfinance as yf

# 日均成交金額門檻（美股用美元、加股用加幣）
MIN_AVG_DOLLAR_VOLUME = 5_000_000
# 抓取資料所需的最少交易日筆數，低於此視為資料不足
MIN_REQUIRED_ROWS = 20
# 用來計算日均成交金額的交易日數
LOOKBACK_DAYS = 60


def passes_min_volume(symbol: str) -> bool:
    """判斷單一ETF是否符合最低交易量門檻。"""
    try:
        hist = yf.Ticker(symbol).history(period="3mo", auto_adjust=True)

        if hist is None or len(hist) < MIN_REQUIRED_ROWS:
            return False

        # 只取最近 60 個交易日
        hist = hist.tail(LOOKBACK_DAYS)

        # 每日成交金額 = 成交量 × 收盤價
        dollar_volume = hist["Volume"] * hist["Close"]
        avg_dollar_volume = dollar_volume.mean()

        return avg_dollar_volume >= MIN_AVG_DOLLAR_VOLUME
    except Exception:
        return False
