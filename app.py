# 這份檔案將把"Algorithmic ETF Trading\data\ranked_good_universe.csv"中的ETF製作成Streamlit介面

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import os
import time
import glob

from trading_logic.timezone_utils import get_now_in_eastern, is_market_open, is_premarket

# ========== 參數設定 ==========
DATA_DIR = "data"
TOP_N_DAILY = 20
REQUEST_DELAY = 0.2
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.5
RANKED_PATH = "data/ranked_good_universe.csv"

st.set_page_config(page_title="ETF Rebound Selection Model", layout="wide")


def _format_bin_range(lower: float, upper: float) -> str:
    """把區間邊界格式化成方便顯示的文字，無限邊界顯示為∞。"""
    lower_str = "-∞" if np.isinf(lower) else f"{lower:.1f}"
    upper_str = "∞" if np.isinf(upper) else f"{upper:.1f}"
    return f"[{lower_str}, {upper_str})"


def _fetch_yesterday_status(row):
    """
    對一支ETF抓最近10天資料，算出昨天收盤對昨天開盤的漲跌幅百分比，
    並計算跟這支ETF最佳區間中點的距離。
    回傳(dict, None)代表成功，或(None, 錯誤原因字串)代表失敗。
    """
    symbol = row["symbol"]

    # 抓資料失敗時重試最多MAX_RETRIES次，每次重試中間多等一點時間
    hist = None
    last_error = "Unknown error"
    for attempt in range(MAX_RETRIES):
        try:
            hist = yf.Ticker(symbol).history(period="10d", auto_adjust=True)
            if not hist.empty:
                break
            last_error = "Returned data is empty"
        except Exception as e:
            hist = None
            last_error = f"{type(e).__name__}: {e}"

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))

    if hist is None or hist.empty:
        return None, last_error

    # 有時候Yahoo在美股開盤前這個時間點，最新一天的資料還沒處理完成，Open和Close會是NaN
    # 先把這種缺值的列濾掉，剩下的才是真正可以用的完整交易日資料
    valid_hist = hist.dropna(subset=["Open", "Close"])

    if len(valid_hist) < 1:
        return None, "Recent data is all missing; Yahoo data may not be updated yet, try again later"

    # hist.index是用美東時間標記的，不能拿本地系統時間去比對
    # 用valid_hist.index[-1]自己帶的時區資訊，換算出"現在"在美東時間是幾點幾號
    now_in_market_tz = pd.Timestamp.now(tz=valid_hist.index[-1].tz)
    last_valid_date = valid_hist.index[-1].date()
    today_date_in_market_tz = now_in_market_tz.date()

    # 只比較日期還不夠，若已經過了美東下午4點收盤時間，這一天的資料其實已經完整
    market_close_time = now_in_market_tz.replace(hour=16, minute=0, second=0, microsecond=0)
    last_row_still_in_progress = (
        last_valid_date == today_date_in_market_tz and now_in_market_tz < market_close_time
    )

    if last_row_still_in_progress:
        if len(valid_hist) < 2:
            return None, "Only today's data is available; yesterday's data is not yet complete"
        yesterday_row = valid_hist.iloc[-2]
    else:
        yesterday_row = valid_hist.iloc[-1]

    yesterday_open = yesterday_row["Open"]
    yesterday_close = yesterday_row["Close"]
    yesterday_date = yesterday_row.name.strftime("%Y-%m-%d")

    if yesterday_open == 0 or pd.isna(yesterday_open) or pd.isna(yesterday_close):
        return None, "Yesterday's open or close price is 0 or missing"

    # 昨日收盤對昨日開盤的報酬率，轉換為百分比形式（例如1.02變成2.0）
    yesterday_return = yesterday_close / yesterday_open
    yesterday_return_pct = yesterday_return * 100 - 100

    # x、y直接取自ranked_good_universe.csv，代表這支ETF歷史上最佳區間的統計數據
    x = row["x"]
    y = row["y"]

    # 這支ETF最佳區間的中點；首尾兩個區間邊界是無限，退回用有限的那一端當作參考點
    bin_lower = row["best_bin_lower"]
    bin_upper = row["best_bin_upper"]
    if np.isinf(bin_lower):
        best_bin_mid = bin_upper
    elif np.isinf(bin_upper):
        best_bin_mid = bin_lower
    else:
        best_bin_mid = (bin_lower + bin_upper) / 2

    distance = abs(yesterday_return_pct - best_bin_mid)

    return {
        "symbol": symbol,
        "country": row["country"],
        "original_rank": row["rank"],
        "yesterday_date": yesterday_date,
        "yesterday_return_pct": round(float(yesterday_return_pct), 4),
        "x": x,
        "y": y,
        "best_bin_lower": bin_lower,
        "best_bin_upper": bin_upper,
        "distance": round(float(distance), 4),
    }, None


def _run_daily_analysis(ranked_df: pd.DataFrame, log_placeholder, progress_bar) -> pd.DataFrame:
    """對ranked_df裡的每支ETF呼叫_fetch_yesterday_status，過程中更新進度條和文字紀錄。"""
    records = []
    total = len(ranked_df)
    logs = []

    for i, (_, row) in enumerate(ranked_df.iterrows()):
        result, error_reason = _fetch_yesterday_status(row)

        if result is not None:
            records.append(result)
        else:
            logs.append(f"{row['symbol']} data fetch failed, skipped, reason: {error_reason}")

        time.sleep(REQUEST_DELAY)

        if i % 10 == 0 or i == total - 1:
            progress_bar.progress(min((i + 1) / total, 1.0))
            logs.append(f"Processed {i + 1}/{total} ETFs")
            log_placeholder.text("\n".join(logs[-10:]))

    return pd.DataFrame(records)


def _plot_daily_results(top_df: pd.DataFrame):
    """畫出今日候選ETF昨日漲跌幅的長條圖，每根bar旁邊標示該ETF的最佳區間範圍。"""
    fig, ax = plt.subplots(figsize=(14, 5))
    x_pos = np.arange(len(top_df))

    bars = ax.bar(x_pos, top_df["yesterday_return_pct"])

    for bar, (_, row) in zip(bars, top_df.iterrows()):
        bin_range_label = _format_bin_range(row["best_bin_lower"], row["best_bin_upper"])
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            bin_range_label,
            ha="center",
            va="bottom" if height >= 0 else "top",
            fontsize=8,
            rotation=90,
        )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(top_df["symbol"], rotation=45)
    ax.set_xlabel("ETF Symbol")
    ax.set_ylabel("Yesterday's Return (%)")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title(f"Today's Top {len(top_df)} ETFs: Yesterday's Return vs Best Bin Range")

    return fig


def main():
    st.title("ETF Rebound Selection Model")
    st.caption("Manually triggered; not scheduled automatically")

    ranked_df = pd.read_csv(RANKED_PATH)

    tab1, tab2 = st.tabs(["Candidate ETF Overview", "Daily Analysis"])

    # ---- 分頁一：候選ETF總覽 ----
    with tab1:
        st.subheader(f"Candidate ETF Pool — {len(ranked_df)} total")
        st.caption(f"Loaded from {RANKED_PATH}")

        countries = sorted(ranked_df["country"].dropna().unique())

        for country in countries:
            country_df = ranked_df[ranked_df["country"] == country].sort_values("rank")
            with st.expander(f"{country} ({len(country_df)})"):
                st.dataframe(
                    country_df[["rank", "symbol", "country", "x", "y"]].rename(
                        columns={
                            "rank": "Rank",
                            "symbol": "Symbol",
                            "country": "Country",
                            "x": "Up Ratio %",
                            "y": "Avg Up Move",
                        }
                    ),
                    use_container_width=True,
                )

    # ---- 分頁二：每日分析 ----
    with tab2:
        st.subheader("Run Daily Analysis")

        now_eastern = get_now_in_eastern()
        if is_market_open():
            market_status = "Open"
        elif is_premarket():
            market_status = "Pre-market"
        else:
            market_status = "After-hours (or non-trading day)"

        st.write(f"Current Eastern Time: {now_eastern.strftime('%Y-%m-%d %H:%M:%S')} ({market_status})")
        st.write(
            f"Clicking the button will fetch the latest data for all candidate ETFs "
            f"and find the top {TOP_N_DAILY} that fell yesterday and are closest to their best bin midpoint"
        )

        if st.button("Start Analysis"):
            progress_bar = st.progress(0.0)
            log_placeholder = st.empty()

            with st.spinner("Fetching latest data and calculating..."):
                result_df = _run_daily_analysis(ranked_df, log_placeholder, progress_bar)

            st.success(f"Analysis complete — successfully retrieved data for {len(result_df)} ETFs")

            # 完整結果存檔，檔名包含日期，每天執行都會留下一份紀錄
            os.makedirs(DATA_DIR, exist_ok=True)
            snapshot_date = get_now_in_eastern().strftime("%Y-%m-%d")
            snapshot_path = os.path.join(DATA_DIR, f"snapshot_{snapshot_date}.csv")
            result_df.to_csv(snapshot_path, index=False)
            st.write(f"Full results saved to {snapshot_path}")

            # 只保留昨日下跌（yesterday_return_pct小於0）的ETF
            down_only_df = result_df[result_df["yesterday_return_pct"] < 0].copy()

            # 依距離由小到大排序，取前TOP_N_DAILY名，再依原始排名重新排序並標記今日名次
            top_df = down_only_df.sort_values("distance").head(TOP_N_DAILY).copy()
            top_df = top_df.sort_values("original_rank").reset_index(drop=True)
            top_df["today_rank"] = top_df.index + 1

            st.subheader(f"Today's Top {len(top_df)} (sorted by original rank)")
            st.dataframe(
                top_df[
                    [
                        "today_rank",
                        "original_rank",
                        "symbol",
                        "country",
                        "yesterday_return_pct",
                        "x",
                        "distance",
                        "y",
                    ]
                ].rename(
                    columns={
                        "today_rank": "Today's Rank",
                        "original_rank": "Original Rank",
                        "symbol": "Symbol",
                        "country": "Country",
                        "yesterday_return_pct": "Yesterday's Return %",
                        "x": "X Value",
                        "distance": "Distance",
                        "y": "Y Value",
                    }
                ),
                use_container_width=True,
            )

            st.subheader("Yesterday's Return vs Best Bin Range Chart")
            fig = _plot_daily_results(top_df)
            st.pyplot(fig)

            st.subheader(f"Full Status for All {len(result_df)} ETFs Yesterday")
            st.dataframe(result_df.sort_values("distance"), use_container_width=True)


if __name__ == "__main__":
    main()
