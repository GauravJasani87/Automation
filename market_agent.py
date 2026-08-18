"""
market_agent.py
----------------
An AI agent that identifies top-performing companies for a given market
and industry, and explains why they're trending using Gemini AI.

Phase 1 (this version):
  - Fetch today's top gaining stocks (US market) from Financial Modeling Prep (FMP)
  - Look up each gainer's company profile (sector/industry/description)
  - Cache results locally to avoid repeated API calls on the same day
  - Ask the user which industry to filter by (dynamic input)

Dependencies:
  - requests
  - python-dotenv

Usage:
  python market_agent.py
"""

import os
import json
from datetime import date
import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # reads FMP_API_KEY and GEMINI_API_KEY from .env

FMP_API_KEY = os.getenv("FMP_API_KEY")
CACHE_FILE = "gainers_cache.json"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY)


def get_top_gainers():
    """
    Fetch today's top gaining stocks (US market) from Financial Modeling Prep.

    Returns:
        list of dict: Each dict contains 'symbol', 'name', 'price',
                      'change', 'changesPercentage', 'exchange'.
    """
    url = f"https://financialmodelingprep.com/stable/biggest-gainers?apikey={FMP_API_KEY}"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return []

    return response.json()


def get_company_profile(symbol):
    """
    Fetch company profile details for a single stock symbol (free endpoint).
    Includes sector, industry, description, market cap, etc.

    Parameters:
        symbol (str): Stock ticker symbol, e.g. "AAPL".

    Returns:
        dict or None: Company profile data, or None if not found/error.
    """
    url = f"https://financialmodelingprep.com/stable/profile?symbol={symbol}&apikey={FMP_API_KEY}"
    response = requests.get(url)

    if response.status_code != 200:
        return None

    data = response.json()
    return data[0] if data else None


def get_gainers_with_profiles(force_refresh=False):
    """
    Get today's gainers merged with their company profiles.
    Uses a local cache file to avoid repeated API calls on the same day.

    Parameters:
        force_refresh (bool): If True, ignores cache and calls the API fresh.

    Returns:
        list of dict: Gainers merged with profile info (sector, industry, etc.)
    """
    today_str = str(date.today())

    # Try loading from cache first
    if not force_refresh and os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
        if cache.get("date") == today_str:
            print(f"Loaded {len(cache['data'])} stocks from cache (no API calls used).")
            return cache["data"]

    # Cache missing, outdated, or force_refresh requested -> fetch fresh
    print("Fetching fresh data from FMP API...")
    gainers = get_top_gainers()

    enriched = []
    for stock in gainers:
        profile = get_company_profile(stock["symbol"])
        if profile:
            enriched.append({**stock, **profile})

    # Save to cache
    with open(CACHE_FILE, "w") as f:
        json.dump({"date": today_str, "data": enriched}, f)

    print(f"Fetched and cached {len(enriched)} stocks.")
    return enriched


def filter_by_industry(stocks, industry_keyword):
    """
    Filter an already-enriched stock list by industry/sector keyword.
    No API calls made here - pure local filtering.

    Parameters:
        stocks (list of dict): Enriched stock list (with sector/industry fields).
        industry_keyword (str): Keyword to match, e.g. "Auto".

    Returns:
        list of dict: Matching stocks.
    """
    keyword = industry_keyword.lower()
    matches = []
    for stock in stocks:
        industry = (stock.get("industry") or "").lower()
        sector = (stock.get("sector") or "").lower()
        if keyword in industry or keyword in sector:
            matches.append(stock)
    return matches

def explain_why_trending(stock):
    """
    Use Gemini to generate a short explanation of what the company does
    and a plausible reason why it might be trending today.

    Parameters:
        stock (dict): A single stock's combined gainer + profile data.

    Returns:
        str: A short AI-generated explanation.
    """
    prompt = (
        f"Company: {stock['name']} ({stock['symbol']})\n"
        f"Sector: {stock.get('sector')}, Industry: {stock.get('industry')}\n"
        f"Today's change: {stock['changesPercentage']:.2f}%\n"
        f"Business description: {stock.get('description', 'No description available.')}\n\n"
        "In 2-3 short sentences: (1) explain simply what this company does, "
        "and (2) suggest a plausible general reason why a stock like this "
        "might be seeing a big price move today. Be clear this is a general "
        "possibility, not a confirmed fact, since you don't have real-time news."
    )

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    all_stocks = get_gainers_with_profiles()

    print("\nExamples: Auto, Biotechnology, Railroad, Oil, Software, Semiconductors")
    industry_keyword = input("\nEnter an industry keyword to search for: ").strip()

    matches = filter_by_industry(all_stocks, industry_keyword)

    print("\nFound " + str(len(matches)) + " gainers matching industry '" + industry_keyword + "':\n")

    if len(matches) == 0:
        print("No matches found.")
    else:
        for stock in matches:
            print(stock["symbol"] + " - " + stock["name"])
            print("  Sector: " + str(stock.get("sector")) + " | Industry: " + str(stock.get("industry")))
            print("  Change: " + str(stock["changesPercentage"]) + "% | Price: $" + str(stock["price"]))
            print("  AI Insight: " + explain_why_trending(stock))
            print("")