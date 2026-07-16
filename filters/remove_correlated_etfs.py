# 有一些不同的ETF可能追蹤的是相同的股票，或是有相同的走勢，這份檔案專門篩選出走勢相同的股票，並取其中市值最大(或其他合理的標準)的一個最為代表

import itertools

import pandas as pd
import yfinance as yf

# 相關係數門檻，超過此值視為同走勢
CORRELATION_THRESHOLD = 0.95


def remove_correlated_etfs(symbols: list[str]) -> list[str]:
    """輸入一組ETF代碼清單，回傳排除同走勢後的清單。"""
    if len(symbols) < 2:
        return list(symbols)

    # 一次性抓取所有ETF過去3年的收盤價
    try:
        raw = yf.download(
            symbols,
            period="3y",
            auto_adjust=True,
            group_by="ticker",
        )
    except Exception:
        # 整批抓取失敗，所有symbol視為保留
        return list(symbols)

    # 整理出每支ETF的收盤價，單一symbol抓取失敗時直接保留、不參與相關性比對
    close_prices = {}
    for symbol in symbols:
        try:
            series = raw[symbol]["Close"]
            if series is None or series.dropna().empty:
                continue
            close_prices[symbol] = series
        except Exception:
            continue

    if len(close_prices) < 2:
        return list(symbols)

    price_df = pd.DataFrame(close_prices)
    returns_df = price_df.pct_change()

    # 計算所有ETF兩兩之間的Pearson相關係數矩陣
    corr_matrix = returns_df.corr(method="pearson")

    valid_symbols = list(close_prices.keys())

    # 找出所有相關性超過門檻的配對，並依相關係數由高到低排序，供貪婪演算法依序處理
    pairs = []
    for sym_a, sym_b in itertools.combinations(valid_symbols, 2):
        corr_value = corr_matrix.loc[sym_a, sym_b]
        if pd.notna(corr_value) and corr_value > CORRELATION_THRESHOLD:
            pairs.append((corr_value, sym_a, sym_b))
    pairs.sort(key=lambda item: item[0], reverse=True)

    total_assets_cache = {}

    def get_total_assets(symbol):
        # 查詢並快取totalAssets，避免同一symbol重複查詢
        if symbol not in total_assets_cache:
            try:
                total_assets_cache[symbol] = yf.Ticker(symbol).info.get("totalAssets")
            except Exception:
                total_assets_cache[symbol] = None
        return total_assets_cache[symbol]

    excluded = set()

    # 貪婪演算法：從相關性最高的配對開始處理，已被排除的symbol不再參與後續比對
    for _corr_value, sym_a, sym_b in pairs:
        if sym_a in excluded or sym_b in excluded:
            continue

        assets_a = get_total_assets(sym_a)
        assets_b = get_total_assets(sym_b)

        if assets_a is not None and assets_b is not None:
            # 保留totalAssets較大的那支
            if assets_a >= assets_b:
                excluded.add(sym_b)
            else:
                excluded.add(sym_a)
        elif assets_a is not None:
            excluded.add(sym_b)
        elif assets_b is not None:
            excluded.add(sym_a)
        else:
            # 兩支都查不到totalAssets，保留代碼字母順序較前的那支
            if sym_a < sym_b:
                excluded.add(sym_b)
            else:
                excluded.add(sym_a)

    # 依原始輸入順序回傳，排除清單中已被淘汰的symbol
    return [symbol for symbol in symbols if symbol not in excluded]
