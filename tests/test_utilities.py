"""
test_utilities.py — Verification script for NEXUS API Expansion.
"""

import asyncio
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def verify_apis():
    print("🚀 Starting NEXUS API Expansion Verification...")
    print("="*50)

    # 1. Finance MCP
    print("\n[1/4] Testing Finance MCP...")
    try:
        from nexus.mcp_servers.finance_mcp import FinanceMCP
        fin = FinanceMCP(demo_mode=False)
        rate = await fin.get_exchange_rate("USD", "INR")
        if "rate" in rate:
            print(f"  ✅ Currency: 1 USD = {rate['rate']} INR")
        else:
            print(f"  ❌ Currency Error: {rate}")

        crypto = await fin.get_crypto_price("ethereum")
        if "price" in crypto:
            print(f"  ✅ Crypto: ETH = {crypto['price']} USD")
        else:
            print(f"  ❌ Crypto Error: {crypto}")
    except Exception as e:
        print(f"  💥 Finance Exception: {e}")

    # 2. Info MCP
    print("\n[2/4] Testing Info MCP...")
    try:
        from nexus.mcp_servers.info_mcp import InfoMCP
        info = InfoMCP(demo_mode=False)
        country = await info.get_country_info("Japan")
        if "capital" in country:
            print(f"  ✅ Geography: Japan Capital = {country['capital']}")
        else:
            print(f"  ❌ Geography Error: {country}")

        word = await info.get_definition("synergy")
        if isinstance(word, list) and len(word) > 0:
            print(f"  ✅ Dictionary: 'synergy' defined.")
        else:
            print(f"  ❌ Dictionary Error: {word}")
    except Exception as e:
        print(f"  💥 Info Exception: {e}")

    # 3. News MCP
    print("\n[3/4] Testing News MCP...")
    try:
        from nexus.mcp_servers.news_mcp import NewsMCP
        news = NewsMCP(demo_mode=False)
        hn = await news.get_tech_trends("OpenAI")
        if len(hn) > 0 and "title" in hn[0]:
            print(f"  ✅ Tech News: Top HN story: {hn[0]['title'][:50]}...")
        else:
            print(f"  ❌ News Error: {hn}")
    except Exception as e:
        print(f"  💥 News Exception: {e}")

    # 4. Tools Agent (End-to-End Routing)
    print("\n[4/4] Testing ToolsAgent Routing...")
    try:
        from nexus.agents.blackboard import Blackboard
        from nexus.agents.tools_agent import ToolsAgent
        
        bb = Blackboard()
        agent = ToolsAgent(bb)
        
        print("  - Input: 'What is the current price of Solana?'")
        result = await agent.think("What is the current price of Solana?")
        
        if result.summary and "Retrieved data" in result.summary:
            print(f"  ✅ Routing Success: {result.summary}")
        elif "Demo response" in result.markdown_content or "AI Response" in result.markdown_content:
            print(f"  ⚠️  Routing Fallback: Agent returned a Demo/Mock response (No API Key).")
        else:
            print(f"  ❌ Routing Failed: {result.summary}")
    except Exception as e:
        print(f"  💥 Agent Exception: {e}")

    print("\n" + "="*50)
    print("✨ Verification Complete.")

if __name__ == "__main__":
    asyncio.run(verify_apis())
