"""Shared ticker config for top-weight NIFTY 50 companies.

These are used by earnings and market-signal scraping scripts.
"""

from __future__ import annotations

TOP5_NIFTY50 = [
    {
        "symbol": "RELIANCE",
        "company_name": "Reliance Industries Ltd",
        "moneycontrol_quote_url": "https://www.moneycontrol.com/india/stockpricequote/refineries/relianceindustries/RI",
    },
    {
        "symbol": "HDFCBANK",
        "company_name": "HDFC Bank Ltd",
        "moneycontrol_quote_url": "https://www.moneycontrol.com/india/stockpricequote/banks-private-sector/hdfcbank/HDF01",
    },
    {
        "symbol": "ICICIBANK",
        "company_name": "ICICI Bank Ltd",
        "moneycontrol_quote_url": "https://www.moneycontrol.com/india/stockpricequote/banks-private-sector/icicibank/ICI02",
    },
    {
        "symbol": "TCS",
        "company_name": "Tata Consultancy Services Ltd",
        "moneycontrol_quote_url": "https://www.moneycontrol.com/india/stockpricequote/computers-software/tataconsultancyservices/TCS",
    },
    {
        "symbol": "BHARTIARTL",
        "company_name": "Bharti Airtel Ltd",
        "moneycontrol_quote_url": "https://www.moneycontrol.com/india/stockpricequote/telecommunications-service/bhartiairtel/BA08",
    },
]

