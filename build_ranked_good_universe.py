# 這份檔案將在"build_universe_and_good_universe.py"被執行後才可執行
# 這份檔案將根據地址"Algorithmic ETF Trading\trading_logic"中的"how_to_rank.py"去輸出檔案
# 輸出的檔案地址為"Algorithmic ETF Trading\data\ranked_good_universe.csv"

import time

import numpy as np
import pandas as pd
import yfinance as yf

from trading_logic.how_to_rank import rank_good_universe

# ========== 參數設定 ==========
GOOD_UNIVERSE_PATH = "data/good_universe.csv"
RANKED_OUTPUT_PATH = "data/ranked_good_universe.csv"
REQUEST_DELAY = 0.3
PROGRESS_INTERVAL = 20

# 資料不足的最少歷史資料筆數門檻（與filters/good_universe_filter.py一致）
MIN_REQUIRED_ROWS = 500


def _compute_best_bin(symbol: str):
    """
    對單一ETF重新抓取10年資料，計算42個區間中x值最高的區間。
    回傳(x, y, best_bin_lower, best_bin_upper)；資料不足時回傳None。
    """
    hist = yf.Ticker(symbol).history(period="10y", auto_adjust=True)

    if hist is None or len(hist) < MIN_REQUIRED_ROWS:
        return None

    data = hist[["Open", "Close"]].copy()

    # 今日收盤相對昨日收盤的報酬率
    data["return"] = data["Close"] / data["Close"].shift(1)
    # 明日開盤相對今日收盤的報酬率
    data["tomorrow_return"] = data["Open"].shift(-1) / data["Close"]

    data = data.dropna(subset=["return", "tomorrow_return"])

    # 轉換為百分比形式，例如1.02變成2.0
    data["return"] = data["return"] * 100 - 100

    # 與filters/good_universe_filter.py完全相同的42個區間定義：
    # (-inf, -4.0)、[-4.0, -3.8)、...、[3.8, 4.0)、[4.0, inf)
    breakpoints = [round(-4.0 + i * 0.2, 1) for i in range(41)]
    bin_edges = [-np.inf] + breakpoints + [np.inf]
    data["bin"] = pd.cut(data["return"], bins=bin_edges, right=False)

    best_x = -1.0
    best_count = -1
    best_y = 0.0
    best_bin = None

    for bin_label, group in data.groupby("bin", observed=True):
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
            best_bin = bin_label

    if best_bin is None:
        return None

    return best_x, best_y, best_bin.left, best_bin.right


def main():
    good_universe_df = pd.read_csv(GOOD_UNIVERSE_PATH)
    total = len(good_universe_df)
    print(f"Loaded good_universe.csv, {total} ETFs total")

    records = []

    for i, (_, row) in enumerate(good_universe_df.iterrows()):
        symbol = row["symbol"]
        country = row["country"]

        try:
            result = _compute_best_bin(symbol)
        except Exception as e:
            print(f"Warning: exception while computing x, y for {symbol} ({e}), skipped")
            result = None

        if result is None:
            print(f"Warning: insufficient history or computation failed for {symbol}, skipped")
        else:
            x, y, bin_lower, bin_upper = result
            records.append({
                "symbol": symbol,
                "country": country,
                "x": x,
                "y": y,
                "best_bin_lower": bin_lower,
                "best_bin_upper": bin_upper,
            })

        time.sleep(REQUEST_DELAY)

        if (i + 1) % PROGRESS_INTERVAL == 0 or (i + 1) == total:
            print(f"Processed {i + 1}/{total} ETFs")

    df = pd.DataFrame(records)
    ranked_df = rank_good_universe(df)
    ranked_df.to_csv(RANKED_OUTPUT_PATH, index=False)

    print(f"Done! ranked_good_universe.csv written to {RANKED_OUTPUT_PATH}, {len(ranked_df)} ETFs total")


if __name__ == "__main__":
    main()
