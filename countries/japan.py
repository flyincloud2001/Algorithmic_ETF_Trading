# 這份檔案用來抓取日本TSE交易所所有ETF代碼

import io

import pdfplumber
import requests

# JPX官方ETF清單PDF網址
JPX_ETF_PDF_URL = (
    "https://www.jpx.co.jp/english/equities/products/etfs/tvdivq000001j45s-att/b5b4pj000002nyru.pdf"
)

# 偽裝瀏覽器的User-Agent，避免被拒絕
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def get_jp_etf_symbols() -> list[str]:
    """回傳日本TSE交易所所有ETF代碼的清單（yfinance使用的.T後綴格式）。"""
    try:
        response = requests.get(JPX_ETF_PDF_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Error: could not download JPX ETF list PDF ({e})")
        return []

    codes = []

    try:
        with pdfplumber.open(io.BytesIO(response.content)) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables():
                    if not table:
                        continue

                    header = table[0]
                    if "Code" not in header:
                        continue

                    code_index = header.index("Code")

                    for row in table[1:]:
                        if code_index >= len(row):
                            continue

                        code = row[code_index]
                        if code is None:
                            continue

                        code = code.strip()

                        # 排除空字串、含空白、以及表格標題列本身（"Code"）
                        if not code or " " in code or code == "Code":
                            continue

                        codes.append(code)
    except Exception as e:
        print(f"Error: could not parse JPX ETF list PDF ({e})")
        return []

    symbols = [f"{code}.T" for code in codes]

    # 去除重複，同時保留原始順序
    return list(dict.fromkeys(symbols))
