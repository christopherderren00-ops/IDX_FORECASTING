#!/usr/bin/env python3
"""
fetch_idx_data.py

Menarik data harga historis (harian) dan data fundamental untuk saham-saham
IDX dari Yahoo Finance (via yfinance), lalu menuliskannya ke satu file JSON
dalam format yang langsung bisa dibaca oleh dashboard React
(stock-forecast-dashboard.jsx).

Perhitungan SMA / EMA / RSI / MACD / proyeksi tren TETAP dilakukan di sisi
dashboard (client-side, dari data `series` mentah) -- script ini HANYA
bertugas menyediakan data harga & fundamental yang asli, bukan simulasi.

Cara pakai:
    pip install -r requirements.txt
    python scripts/fetch_idx_data.py

Output:
    data/latest.json
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

# ---------------------------------------------------------------------------
# Daftar saham yang mau dipantau. Tambah/kurangi sesuai kebutuhan.
# Kode Yahoo Finance untuk saham IDX selalu diakhiri ".JK".
# ---------------------------------------------------------------------------
TICKERS = {
    "BBCA": {"yahoo": "BBCA.JK", "name": "Bank Central Asia Tbk", "sector": "Perbankan"},
    "BBRI": {"yahoo": "BBRI.JK", "name": "Bank Rakyat Indonesia Tbk", "sector": "Perbankan"},
    "TLKM": {"yahoo": "TLKM.JK", "name": "Telkom Indonesia Tbk", "sector": "Telekomunikasi"},
    "ASII": {"yahoo": "ASII.JK", "name": "Astra International Tbk", "sector": "Otomotif & Konglomerasi"},
    "GOTO": {"yahoo": "GOTO.JK", "name": "GoTo Gojek Tokopedia Tbk", "sector": "Teknologi"},
}

HISTORY_DAYS = "1y"  # rentang histori yang ditarik (cukup untuk MA50 + RSI/MACD)
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "latest.json"
MAX_RETRIES = 3
RETRY_DELAY_SEC = 5


def fetch_series(yahoo_code: str):
    """Ambil harga close harian, kembalikan list [{date, close}, ...]."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            hist = yf.Ticker(yahoo_code).history(period=HISTORY_DAYS, interval="1d")
            if hist.empty:
                raise ValueError("Data historis kosong")
            hist = hist.dropna(subset=["Close"])
            series = [
                {"date": idx.strftime("%Y-%m-%d"), "close": round(float(row["Close"]))}
                for idx, row in hist.iterrows()
            ]
            return series
        except Exception as exc:  # noqa: BLE001
            print(f"  [!] percobaan {attempt}/{MAX_RETRIES} gagal ambil histori {yahoo_code}: {exc}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY_SEC)
    return []


def fetch_fundamental(yahoo_code: str):
    """Ambil metrik fundamental dari Yahoo Finance. Field yang tidak tersedia
    untuk suatu saham akan bernilai None -- ini normal, terutama untuk saham
    dengan cakupan data Yahoo yang terbatas."""
    try:
        info = yf.Ticker(yahoo_code).get_info()
    except Exception as exc:  # noqa: BLE001
        print(f"  [!] gagal ambil fundamental {yahoo_code}: {exc}", file=sys.stderr)
        info = {}

    pe = info.get("trailingPE")
    pbv = info.get("priceToBook")
    eps = info.get("trailingEps")
    roe = info.get("returnOnEquity")
    der = info.get("debtToEquity")
    div_yield = info.get("dividendYield")
    market_cap = info.get("marketCap")

    return {
        "pe": round(pe, 1) if pe else None,
        "pbv": round(pbv, 2) if pbv else None,
        "eps": round(eps) if eps else None,
        # Yahoo mengembalikan returnOnEquity sbg desimal (0.213 = 21.3%)
        "roe": round(roe * 100, 1) if roe is not None else None,
        # Yahoo mengembalikan debtToEquity sudah dalam bentuk persen (mis. 42.3)
        "der": round(der / 100, 2) if der is not None else None,
        "div_yield": round(div_yield * 100, 2) if div_yield else 0,
        "mcap": f"{market_cap / 1e12:.3f}T" if market_cap else None,
    }


def main():
    print(f"Mulai fetch {len(TICKERS)} saham @ {datetime.now(timezone.utc).isoformat()}")
    stocks = {}

    for code, meta in TICKERS.items():
        print(f"- {code} ({meta['yahoo']})")
        series = fetch_series(meta["yahoo"])
        fundamental = fetch_fundamental(meta["yahoo"])

        if not series:
            print(f"  [x] dilewati, tidak ada data harga untuk {code}", file=sys.stderr)
            continue

        stocks[code] = {
            "name": meta["name"],
            "sector": meta["sector"],
            "series": series,
            "fundamental": fundamental,
        }
        time.sleep(1)  # jeda sopan antar-request ke Yahoo Finance

    if not stocks:
        print("Tidak ada data yang berhasil diambil sama sekali -- keluar tanpa menulis file.", file=sys.stderr)
        sys.exit(1)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance (yfinance)",
        "stocks": stocks,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Selesai. Ditulis ke {OUTPUT_PATH} ({len(stocks)} saham).")


if __name__ == "__main__":
    main()
