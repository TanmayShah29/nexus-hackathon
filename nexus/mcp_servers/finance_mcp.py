"""
finance_mcp.py — Finance MCP (Currency + Crypto + Stocks)
"""

import logging
from typing import Any, Dict
import aiohttp

from nexus.utils.retry import RetryConfig
from nexus.config import get_demo_mode

logger = logging.getLogger("nexus")
DEMO_MODE = get_demo_mode()

FINANCE_RETRY_CONFIG = RetryConfig(max_attempts=2, base_delay=0.5)

class FinanceMCP:
    """
    Financial data: Currency rates, Crypto prices, and Stock market.
    """

    def __init__(self, demo_mode: bool = DEMO_MODE):
        self.demo_mode = demo_mode

    async def get_exchange_rate(self, from_currency: str, to_currency: str) -> Dict[str, Any]:
        """Convert currency using ExchangeRate-API (No Auth)."""
        if self.demo_mode:
            return {"rate": 83.5, "from": from_currency, "to": to_currency, "status": "demo"}

        url = f"https://open.er-api.com/v6/latest/{from_currency.upper()}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {"error": "API Unavailable", "status": resp.status}
                data = await resp.json()
                rate = data.get("rates", {}).get(to_currency.upper())
                if not rate:
                    return {"error": f"Currency {to_currency} not found."}
                return {
                    "from": from_currency.upper(),
                    "to": to_currency.upper(),
                    "rate": rate,
                    "last_updated": data.get("time_last_update_utc")
                }

    async def get_crypto_price(self, coin_id: str = "bitcoin", vs_currency: str = "usd") -> Dict[str, Any]:
        """Get crypto price using CoinGecko (Public API)."""
        if self.demo_mode:
            return {"coin": coin_id, "price": 65000, "currency": vs_currency, "status": "demo"}

        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id.lower(), "vs_currencies": vs_currency.lower()}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return {"error": "CoinGecko Unavailable"}
                data = await resp.json()
                price = data.get(coin_id.lower(), {}).get(vs_currency.lower())
                return {
                    "coin": coin_id,
                    "price": price,
                    "currency": vs_currency.upper()
                }

    async def get_stock_price(self, symbol: str) -> Dict[str, Any]:
        """Get stock price (Mocked for Demo/Public fallback)."""
        # Alpha Vantage requires a key, so we use a fallback/mock for the hackathon
        # unless the user provides one in .env
        return {
            "symbol": symbol.upper(),
            "price": 150.25,
            "change": "+1.2%",
            "status": "mocked (requires Alpha Vantage API Key)"
        }
