# 先定義data['return']，代表該ETF過去十年的昨日收盤對今日收盤的報酬率
# 再根據data['return']定義data['tomorrow_return']，代表明日開盤對今日收盤的報酬率
# 制定不同data['return']值的範圍，單位是%，分界點包含 range(-4, 4.2, 0.2), 每個範圍的形式為(-infinity, a), [b, c), [d, infinity)
# 針對每個data['return']值的範圍，計算該範圍內有多少比例對應的data['tomorrow_return']的值為上漲，將此比例記作為x%，並計算這些上漲值的平均值y%
# 選出x值最高的"data['return']值的範圍"
# 若此範圍的x>=80且y>=0.5，則此ETF被篩選通過
# 最後將篩選通過的ETF輸出在"Algorithmic ETF Trading\data\good_universe.csv"

import math

import pandas as pd
import yfinance as yf

# 資料不足的最少歷史資料筆數門檻
MIN_REQUIRED_ROWS = 500
# 最佳區間上漲比例門檻（%）
X_THRESHOLD = 80
# 最佳區間上漲平均倍數門檻（對應tomorrow_return原始比例，1.005即上漲0.5%以上）
Y_THRESHOLD = 1.005


def passes_good_universe(symbol: str) -> bool:
    """判斷單一ETF是否通過good_universe篩選條件。"""
    try:
        hist = yf.Ticker(symbol).history(period="10y", auto_adjust=True)

        if hist is None or len(hist) < MIN_REQUIRED_ROWS:
            return False

        data = hist[["Open", "Close"]].copy()

        # 今日收盤相對昨日收盤的報酬率
        data["return"] = data["Close"] / data["Close"].shift(1)
        # 明日開盤相對今日收盤的報酬率
        data["tomorrow_return"] = data["Open"].shift(-1) / data["Close"]

        data = data.dropna(subset=["return", "tomorrow_return"])

        # 轉換為百分比形式，例如1.02變成2.0
        data["return"] = data["return"] * 100 - 100

        # 依range(-4, 4.2, 0.2)的分界點建立42個區間：
        # (-inf, -4.0)、[-4.0, -3.8)、...、[3.8, 4.0)、[4.0, inf)
        breakpoints = [round(-4.0 + i * 0.2, 1) for i in range(41)]
        bin_edges = [-math.inf] + breakpoints + [math.inf]
        data["bin"] = pd.cut(data["return"], bins=bin_edges, right=False)

        best_x = -1.0
        best_count = -1
        best_y = 0.0

        for _bin_label, group in data.groupby("bin", observed=True):
            tomorrow_returns = group["tomorrow_return"]
            count = len(tomorrow_returns)

            # x% = 該區間中明日開盤上漲（tomorrow_return > 1.0）的比例
            up_mask = tomorrow_returns > 1.0
            x = up_mask.mean() * 100

            # y = 上漲值的平均值，若無上漲值則為0
            up_values = tomorrow_returns[up_mask]
            y = up_values.mean() if not up_values.empty else 0.0

            # x值最高的區間為最佳區間，平手則取事件數較多的
            if x > best_x or (x == best_x and count > best_count):
                best_x = x
                best_count = count
                best_y = y

        return best_x >= X_THRESHOLD and best_y >= Y_THRESHOLD
    except Exception:
        return False
