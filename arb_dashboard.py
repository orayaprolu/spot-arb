import streamlit as st
import asyncio
import threading
import time
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import requests

from libraries.data_ingestion.coinex_data_feed import CoinexDataFeed
from libraries.data_ingestion.mexc_data_feed import MexcDataFeed
from libraries.models.bba import BBA

# --- Configuration ---
DEFAULT_PAIRS = 100
REFRESH_MS = 1000  # Autorefresh interval in milliseconds

# Fetch top USDT pairs by volume
@st.cache_data(show_spinner=False)
def fetch_assets_coinex(num_assets: int = DEFAULT_PAIRS) -> list[str]:
    url = "https://api.coinex.com/v2/spot/ticker"
    resp = requests.get(url)
    resp.raise_for_status()
    tickers = resp.json().get("data", [])
    usdt = [t for t in tickers if t["market"].endswith("USDT")]
    usdt.sort(key=lambda t: float(t["value"]), reverse=True)
    return [f"{t['market'][:-4]}-USDT" for t in usdt[:num_assets]]

# Singleton state and background initialization
@st.cache_resource
def init_feeds(pairs: list[str]):
    # Shared state across reruns
    state: dict[str, dict[str, float]] = {pair: {} for pair in pairs}
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()

    async def update_state_loop(pair: str, coinex_feed: CoinexDataFeed, mexc_feed: MexcDataFeed):
        # Start feeds
        asyncio.create_task(coinex_feed.run(), name=f"coinex_{pair}")
        asyncio.create_task(mexc_feed.run(), name=f"mexc_{pair}")

        # CoinEx queue consumer
        async def coinex_consumer():
            while True:
                bba: BBA = await coinex_feed.bba_queue.get()
                state[pair]["illiquid_bid"] = bba.best_bid_price
                state[pair]["illiquid_ask"] = bba.best_ask_price

        # MexC poll consumer
        async def mexc_consumer():
            while True:
                await asyncio.sleep(0.2)
                bba = mexc_feed.bba
                if bba:
                    state[pair]["liquid_bid"] = bba.best_bid_price
                    state[pair]["liquid_ask"] = bba.best_ask_price

        await asyncio.gather(coinex_consumer(), mexc_consumer())

    # Initialize feeds and background tasks
    for pair in pairs:
        coinex_feed = CoinexDataFeed(pair)
        mexc_feed = MexcDataFeed(pair)
        # Schedule update tasks in background loop
        asyncio.run_coroutine_threadsafe(
            update_state_loop(pair, coinex_feed, mexc_feed), loop
        )

    return state

# Build DataFrame from state
def build_dataframe(state: dict[str, dict[str, float]]) -> pd.DataFrame:
    records = []
    for pair, vals in state.items():
        ib = vals.get("illiquid_bid")
        ia = vals.get("illiquid_ask")
        lb = vals.get("liquid_bid")
        la = vals.get("liquid_ask")
        if ib and ia and lb and la:
            arb_bps = (lb - ib) / ib * 10_000
            taker_bps = (lb - ia) / ia * 10_000
            records.append({
                "Pair": pair,
                "Illiq Ask": ia,
                "Illiq Bid": ib,
                "Liq Ask": la,
                "Liq Bid": lb,
                "Arb (bps)": arb_bps,
                "Taker (bps)": taker_bps,
            })
        else:
            records.append({
                "Pair": pair,
                "Illiq Ask": None,
                "Illiq Bid": None,
                "Liq Ask": None,
                "Liq Bid": None,
                "Arb (bps)": None,
                "Taker (bps)": None,
            })
    df = pd.DataFrame(records)
    return df.sort_values(by="Arb (bps)", ascending=False)

# Streamlit app
st.set_page_config(page_title="Spot Arb Dashboard", layout="wide")
st.title("Spot Arb Monitor")

# Sidebar settings
num_pairs = st.sidebar.slider(
    "Number of pairs to monitor", min_value=10, max_value=200,
    value=DEFAULT_PAIRS, step=10
)

# Fetch pairs and initialize background feeds
pairs = fetch_assets_coinex(num_pairs)
state = init_feeds(pairs)

# Autorefresh every REFRESH_MS milliseconds
st_autorefresh(interval=REFRESH_MS, limit=None, key="arb_refresh")

# Display current data
df = build_dataframe(state)
st.dataframe(df, use_container_width=True)

# Footer
st.markdown(f"Updated every {REFRESH_MS/1000:.1f}s")
