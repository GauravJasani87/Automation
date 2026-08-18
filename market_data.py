"""
stock_history.py
---------------------------------------------------------------
Fetch DAILY price history for ONE company over a period you choose
(e.g. 2 months, 2 years, 10 years) using free Yahoo Finance data.

No API key. No login.

SETUP (run once):
    pip install --upgrade yfinance curl_cffi pandas

RUN:
    python stock_history.py
---------------------------------------------------------------
"""

import sys
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

try:
    import yfinance as yf
    import pandas as pd
except ImportError:
    sys.exit(
        "\n[!] Missing packages. Install with:\n"
        "    pip install --upgrade yfinance curl_cffi pandas\n"
    )

# --- Corporate SSL workaround + browser impersonation ---
try:
    from curl_cffi import requests as cffi_requests
    SESSION = cffi_requests.Session(impersonate="chrome", verify=False)
except Exception:
    SESSION = None


# ----------------------------------------------------------------------
# Turn plain-English period into a yfinance period string
# ----------------------------------------------------------------------
def parse_period(text):
    """
    Accepts inputs like:
        '2 months', '2mo', '6 months', '1 year', '2 years',
        '10 years', '10y', 'ytd', 'max', '5d'
    Returns a valid yfinance period string, or None if not understood.
    """
    t = text.strip().lower().replace(" ", "")

    # direct shortcuts yfinance already understands
    if t in ("ytd", "max"):
        return t

    # pull the leading number
    num = "".join(ch for ch in t if ch.isdigit())
    if not num:
        return None
    n = int(num)

    if "year" in t or t.endswith("y") or t.endswith("yr") or t.endswith("yrs"):
        return f"{n}y"
    if "month" in t or "mo" in t:
        return f"{n}mo"
    if "week" in t or t.endswith("wk"):
        return f"{n}wk"
    if "day" in t or t.endswith("d"):
        return f"{n}d"
    return None


# ----------------------------------------------------------------------
# Fetch the daily history
# ----------------------------------------------------------------------
def get_history(ticker, period):
    t = yf.Ticker(ticker, session=SESSION) if SESSION else yf.Ticker(ticker)
    hist = t.history(period=period, interval="1d")  # daily candles
    if hist.empty:
        return None, None

    # Clean up: keep OHLCV, drop incomplete (NaN) rows, tidy the index
    cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in hist.columns]
    hist = hist[cols].dropna(subset=["Close"])
    hist.index = hist.index.date  # show just the date, not the timestamp

    # Grab a friendly company name + currency
    name, currency = ticker.upper(), ""
    try:
        fi = t.fast_info
        currency = fi.get("currency") or ""
    except Exception:
        pass
    try:
        info = t.info
        name = info.get("longName") or info.get("shortName") or ticker.upper()
        currency = currency or info.get("currency") or ""
    except Exception:
        pass

    return hist, {"name": name, "currency": currency}


# ----------------------------------------------------------------------
# Show a summary of the period
# ----------------------------------------------------------------------
def print_summary(hist, meta, ticker, period):
    cur = meta["currency"]
    first_close = hist["Close"].iloc[0]
    last_close = hist["Close"].iloc[-1]
    change = last_close - first_close
    change_pct = (change / first_close) * 100 if first_close else 0
    arrow = "\u25b2" if change >= 0 else "\u25bc"

    print("\n" + "=" * 60)
    print(f"  {meta['name']}  ({ticker.upper()})   |   Period: {period}")
    print("=" * 60)
    print(f"  Trading days : {len(hist)}")
    print(f"  From         : {hist.index[0]}   Close: {first_close:,.2f} {cur}")
    print(f"  To           : {hist.index[-1]}   Close: {last_close:,.2f} {cur}")
    print(f"  Change       : {arrow} {change:+,.2f} ({change_pct:+.2f}%)")
    print(f"  Period High  : {hist['High'].max():,.2f} {cur}")
    print(f"  Period Low   : {hist['Low'].min():,.2f} {cur}")
    print("=" * 60)


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  DAILY STOCK HISTORY  (Yahoo Finance - no key, no login)")
    print("=" * 60)

    # 1) Company
    ticker = input("Enter ticker (e.g. AAPL, HSBA.L, RELIANCE.NS): ").strip()
    if not ticker:
        print("No ticker entered. Exiting.")
        return

    # 2) Period
    raw_period = input("Enter period (e.g. 2 months, 2 years, 10 years, ytd, max): ").strip()
    period = parse_period(raw_period)
    if not period:
        print(f"[!] Couldn't understand period '{raw_period}'. "
              f"Try '2 months', '2 years', '10 years', 'ytd' or 'max'.")
        return

    print(f"\nFetching daily data for {ticker.upper()} over {period} ...")
    hist, meta = get_history(ticker, period)
    if hist is None:
        print(f"[!] No data found for '{ticker}'. Check the ticker/suffix.")
        return

    # 3) Show the data
    print_summary(hist, meta, ticker, period)

    # Print the full daily table (pandas shows it nicely)
    pd.set_option("display.max_rows", None)   # show every row
    print("\nDaily prices:\n")
    print(hist.round(2))

    # 4) Optional: save to CSV
    save = input("\nSave this to a CSV file? (y/n): ").strip().lower()
    if save == "y":
        fname = f"{ticker.upper().replace('.', '_')}_{period}_{datetime.now():%Y%m%d}.csv"
        hist.round(4).to_csv(fname)
        print(f"[✓] Saved to: {fname}")


if __name__ == "__main__":
    main()