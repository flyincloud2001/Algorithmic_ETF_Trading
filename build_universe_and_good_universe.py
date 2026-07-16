# 這份檔案每次被執行時，只針對一個國家做篩選(以下註解以加拿大為例)
# 當這份程式碼被執行時，會根據地址"Algorithmic ETF Trading\filters"中的"ibkr_tradeable.py、listing_age.py、low_volatility.py、remove_correlated_etfs.py、min_volume.py"這五份檔案，和根據地址"Algorithmic ETF Trading\countries"中的"canada.py"，去篩選出ETF，並新增至"Algorithmic ETF Trading\data\universe.csv"
# 建造完good_universe.csv後，這份檔案會繼續從good_universe.csv裡的ETF，根據地址"Algorithmic ETF Trading\filters"中的"good_universe_filter.py"這份檔案繼續篩選出ETF，並新增到"Algorithmic ETF Trading\data\good_universe.csv"
# 被針對做篩選的國家將可以手動被指定，程式碼中包含了"有我可以做更動的國家"的註解
# 每當這份程式碼被執行(每當一個國家被做篩選)時，universe.csv和good_universe.csv這兩份檔案會先後被更新，而不是被替換
# 這份檔案out_sampling.py暫時不做更動

import os
import time

import pandas as pd

from countries.usa import get_us_etf_symbols
from countries.canada import get_ca_etf_symbols
from countries.uk import get_uk_etf_symbols
from countries.germany import get_de_etf_symbols
from countries.japan import get_jp_etf_symbols
from countries.australia import get_au_etf_symbols
from countries.france import get_fr_etf_symbols
from countries.netherlands import get_nl_etf_symbols
from countries.south_korea import get_kr_etf_symbols
from countries.switzerland import get_ch_etf_symbols
from countries.hong_kong import get_hk_etf_symbols
from countries.singapore import get_sg_etf_symbols
from countries.india import get_in_etf_symbols
from countries.taiwan import get_tw_etf_symbols
from countries.brazil import get_br_etf_symbols
from countries.mexico import get_mx_etf_symbols
from countries.turkey import get_tr_etf_symbols
from countries.saudi_arabia import get_sa_etf_symbols
from countries.indonesia import get_id_etf_symbols
from countries.south_africa import get_za_etf_symbols
from countries.poland import get_pl_etf_symbols
from filters.listing_age import passes_listing_age
from filters.min_volume import passes_min_volume
from filters.low_volatility import filter_low_volatility
from filters.remove_correlated_etfs import remove_correlated_etfs
from filters.ibkr_tradeable import filter_ibkr_tradeable
from filters.good_universe_filter import passes_good_universe

# ========== 參數設定區塊 ==========
# 有我可以做更動的國家：每次執行前手動修改，目前支援"United States"、"Canada"、"United Kingdom"、"Germany"、"Japan"、"Australia"、"France"、"Netherlands"、"South Korea"、"Switzerland"、"Hong Kong"、"Singapore"、"India"、"Taiwan"、"Brazil"、"Mexico"、"Turkey"、"Saudi Arabia"、"Indonesia"、"South Africa"、"Poland"
COUNTRY = "United States"

UNIVERSE_PATH = "data/universe.csv"
GOOD_UNIVERSE_PATH = "data/good_universe.csv"
REQUEST_DELAY = 0.3

# 支援的國家與對應的代碼抓取函式
COUNTRY_SYMBOL_FETCHERS = {
    "United States": get_us_etf_symbols,
    "Canada": get_ca_etf_symbols,
    "United Kingdom": get_uk_etf_symbols,
    "Germany": get_de_etf_symbols,
    "Japan": get_jp_etf_symbols,
    "Australia": get_au_etf_symbols,
    "France": get_fr_etf_symbols,
    "Netherlands": get_nl_etf_symbols,
    "South Korea": get_kr_etf_symbols,
    "Switzerland": get_ch_etf_symbols,
    "Hong Kong": get_hk_etf_symbols,
    "Singapore": get_sg_etf_symbols,
    "India": get_in_etf_symbols,
    "Taiwan": get_tw_etf_symbols,
    "Brazil": get_br_etf_symbols,
    "Mexico": get_mx_etf_symbols,
    "Turkey": get_tr_etf_symbols,
    "Saudi Arabia": get_sa_etf_symbols,
    "Indonesia": get_id_etf_symbols,
    "South Africa": get_za_etf_symbols,
    "Poland": get_pl_etf_symbols,
}


def _load_existing_csv(path: str, columns: list[str]) -> pd.DataFrame:
    """讀取現有csv，若不存在或為空則回傳只有指定欄位的空DataFrame。"""
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return pd.read_csv(path)
    return pd.DataFrame(columns=columns)


def main():
    if COUNTRY not in COUNTRY_SYMBOL_FETCHERS:
        print(f"Error: unsupported country「{COUNTRY}」, please check the COUNTRY setting")
        return

    print(f"===== Starting filter for country: {COUNTRY} =====")

    # 步驟1：根據COUNTRY取得該國家原始ETF代碼清單
    symbols = COUNTRY_SYMBOL_FETCHERS[COUNTRY]()
    print(f"Retrieved raw ETF symbol list, {len(symbols)} total")

    # 步驟2a：上市超過15年
    remaining = []
    for symbol in symbols:
        if passes_listing_age(symbol):
            remaining.append(symbol)
        time.sleep(REQUEST_DELAY)
    print(f"{len(remaining)} remaining after 'listed over 15 years' filter")

    # 步驟2b：最少交易量
    next_remaining = []
    for symbol in remaining:
        if passes_min_volume(symbol):
            next_remaining.append(symbol)
        time.sleep(REQUEST_DELAY)
    remaining = next_remaining
    print(f"{len(remaining)} remaining after 'minimum volume' filter")

    # 步驟2c：低波動率（整批傳入）
    remaining = filter_low_volatility(remaining)
    print(f"{len(remaining)} remaining after 'low volatility' filter")

    # 步驟2d：排除同走勢的ETF（整批傳入）
    remaining = remove_correlated_etfs(remaining)
    print(f"{len(remaining)} remaining after 'removing correlated ETFs'")

    # 步驟2e：IBKR可交易性（整批傳入）
    remaining = filter_ibkr_tradeable(remaining)
    print(f"{len(remaining)} remaining after 'IBKR tradeable' filter")

    # TODO：out_sampling.py這個樣本外驗證步驟暫時略過，未來在此加入

    # 步驟3：通過所有篩選的symbol視為這個國家的universe
    universe_df = pd.DataFrame({"symbol": remaining, "country": COUNTRY})

    # 步驟4：讀取現有universe.csv，移除同一國家的舊資料，再把新結果append進去
    existing_universe_df = _load_existing_csv(UNIVERSE_PATH, ["symbol", "country"])
    existing_universe_df = existing_universe_df[existing_universe_df["country"] != COUNTRY]
    updated_universe_df = pd.concat([existing_universe_df, universe_df], ignore_index=True)
    updated_universe_df.to_csv(UNIVERSE_PATH, index=False)
    print(f"universe.csv updated: {COUNTRY} added {len(universe_df)}, total {len(updated_universe_df)}")

    # 步驟5：對通過universe篩選的symbol逐一執行good_universe篩選
    good_universe_symbols = []
    for symbol in remaining:
        if passes_good_universe(symbol):
            good_universe_symbols.append(symbol)
        time.sleep(REQUEST_DELAY)
    print(f"{len(good_universe_symbols)} remaining after 'good_universe' filter")

    # 步驟6：讀取現有good_universe.csv，移除同一國家的舊資料，再把新結果append進去
    good_universe_df = pd.DataFrame({"symbol": good_universe_symbols, "country": COUNTRY})
    existing_good_universe_df = _load_existing_csv(GOOD_UNIVERSE_PATH, ["symbol", "country"])
    existing_good_universe_df = existing_good_universe_df[existing_good_universe_df["country"] != COUNTRY]
    updated_good_universe_df = pd.concat([existing_good_universe_df, good_universe_df], ignore_index=True)
    updated_good_universe_df.to_csv(GOOD_UNIVERSE_PATH, index=False)
    print(f"good_universe.csv updated: {COUNTRY} added {len(good_universe_df)}, total {len(updated_good_universe_df)}")

    print(f"===== {COUNTRY} filtering pipeline complete =====")


if __name__ == "__main__":
    main()
