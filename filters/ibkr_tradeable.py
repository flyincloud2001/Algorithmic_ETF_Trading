# 這份檔案用來確認ETF是否真的能在IBKR（Interactive Brokers）交易，避免篩選出的ETF在實際下單時找不到合約

import time

from ib_insync import IB, Stock

# 每筆合約查詢之間的等待秒數，避免對TWS/Gateway造成過大負擔
QUERY_INTERVAL_SECONDS = 0.1


def filter_ibkr_tradeable(
    symbols: list[str],
    host: str = "127.0.0.1",
    port: int = 7497,
    client_id: int = 99,
) -> list[str]:
    """輸入一組ETF代碼清單，回傳真的能在IBKR交易的清單。"""
    ib = IB()

    try:
        ib.connect(host, port, clientId=client_id)
    except Exception as e:
        # 連線失敗時不排除任何ETF，直接回傳原始清單
        print(f"Warning: could not connect to IBKR ({e}), skipping IBKR tradeability check")
        return list(symbols)

    tradeable_symbols = []

    try:
        for symbol in symbols:
            # 根據代碼後綴建立對應的合約
            if symbol.endswith(".L"):
                base_symbol = symbol[: -len(".L")]
                contract = Stock(base_symbol, "LSEETF", "GBP")
            elif symbol.endswith(".T"):
                base_symbol = symbol[: -len(".T")]
                contract = Stock(base_symbol, "TSEJ", "JPY")
            elif symbol.endswith(".AX"):
                base_symbol = symbol[: -len(".AX")]
                contract = Stock(base_symbol, "ASX", "AUD")
            elif symbol.endswith(".PA"):
                base_symbol = symbol[: -len(".PA")]
                contract = Stock(base_symbol, "SBF", "EUR")
            elif symbol.endswith(".AS"):
                base_symbol = symbol[: -len(".AS")]
                contract = Stock(base_symbol, "AEB", "EUR")
            elif symbol.endswith(".KS"):
                base_symbol = symbol[: -len(".KS")]
                contract = Stock(base_symbol, "KSE", "KRW")
            elif symbol.endswith(".SW"):
                base_symbol = symbol[: -len(".SW")]
                contract = Stock(base_symbol, "EBS", "CHF")
            elif symbol.endswith(".HK"):
                base_symbol = symbol[: -len(".HK")]
                contract = Stock(base_symbol, "SEHK", "HKD")
            elif symbol.endswith(".SI"):
                base_symbol = symbol[: -len(".SI")]
                contract = Stock(base_symbol, "SGX", "SGD")
            elif symbol.endswith(".NS"):
                base_symbol = symbol[: -len(".NS")]
                contract = Stock(base_symbol, "NSE", "INR")
            elif symbol.endswith(".TW"):
                base_symbol = symbol[: -len(".TW")]
                contract = Stock(base_symbol, "TSEJ", "TWD")
            elif symbol.endswith(".SA"):
                base_symbol = symbol[: -len(".SA")]
                contract = Stock(base_symbol, "BVMF", "BRL")
            elif symbol.endswith(".MX"):
                base_symbol = symbol[: -len(".MX")]
                contract = Stock(base_symbol, "MEXI", "MXN")
            elif symbol.endswith(".IS"):
                base_symbol = symbol[: -len(".IS")]
                contract = Stock(base_symbol, "BIST", "TRY")
            elif symbol.endswith(".SR"):
                base_symbol = symbol[: -len(".SR")]
                contract = Stock(base_symbol, "TADAWUL", "SAR")
            elif symbol.endswith(".JK"):
                base_symbol = symbol[: -len(".JK")]
                contract = Stock(base_symbol, "IDX", "IDR")
            elif symbol.endswith(".JO"):
                base_symbol = symbol[: -len(".JO")]
                contract = Stock(base_symbol, "JSE", "ZAR")
            elif symbol.endswith(".WA"):
                base_symbol = symbol[: -len(".WA")]
                contract = Stock(base_symbol, "WSE", "PLN")
            elif symbol.endswith(".SN"):
                base_symbol = symbol[: -len(".SN")]
                contract = Stock(base_symbol, "BCS", "CLP")
            elif symbol.endswith(".TO"):
                base_symbol = symbol[: -len(".TO")]
                contract = Stock(base_symbol, "SMART", "CAD", primaryExchange="TSE")
            elif symbol.endswith(".V"):
                base_symbol = symbol[: -len(".V")]
                contract = Stock(base_symbol, "SMART", "CAD", primaryExchange="VENTURE")
            else:
                contract = Stock(symbol, "SMART", "USD")

            details = ib.reqContractDetails(contract)

            if details:
                tradeable_symbols.append(symbol)

            time.sleep(QUERY_INTERVAL_SECONDS)
    finally:
        ib.disconnect()

    return tradeable_symbols
