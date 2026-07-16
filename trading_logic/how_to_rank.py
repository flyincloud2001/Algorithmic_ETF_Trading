# 根據此地址: Algorithmic ETF Trading\filters\good_universe_filter.py 關於x%和y%的定義
# 先用x由高而低排名，再用y由高而低排名
# 最後輸出結果至"Algorithmic ETF Trading\data\ranked_good_universe.csv"

import pandas as pd


def rank_good_universe(df: pd.DataFrame) -> pd.DataFrame:
    """輸入good_universe的DataFrame，回傳依x、y排名後的DataFrame。"""
    # 先依x由高到低排名，x相同時依y由高到低排名
    ranked_df = df.sort_values(by=["x", "y"], ascending=[False, False]).reset_index(drop=True)

    # 新增rank欄位，從1開始編號
    ranked_df["rank"] = ranked_df.index + 1

    return ranked_df
