import streamlit as st
import pandas as pd
from nsepython import *
import time

# Page Setup
st.set_page_config(layout="wide", page_title="Nifty Masterclass Tracker")

# Custom CSS for Mobile View
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 25px; color: #00ff00; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Control Panel")

# 1. Manual Base Price Selection
base_price_input = st.sidebar.number_input("Set Manual Base Price (ATM)", value=0, step=50)

# 2. Refresh Rate Option
refresh_seconds = st.sidebar.selectbox("Refresh Interval (Seconds)", options=[5, 10, 30, 60], index=0)

# --- DATA FETCHING ---
def fetch_data():
    try:
        # Fetching raw data from NSE
        payload = nse_optionchain_scrapper('NIFTY')
        return payload
    except:
        return None

payload = fetch_data()

if payload:
    # Get Spot Price and Timestamp
    spot_price = payload['records']['underlyingValue']
    timestamp = payload['records']['timestamp']
    
    # Header Info
    col1, col2 = st.columns(2)
    col1.metric("NIFTY LIVE", spot_price)
    col2.write(f"**Last Sync:** {timestamp}")
    
    # Determine the ATM Strike
    # If user hasn't typed a base price, auto-calculate it
    if base_price_input == 0:
        strike_list = payload['records']['strikePrices']
        atm_strike = min(strike_list, key=lambda x:abs(x-spot_price))
    else:
        atm_strike = base_price_input

    st.sidebar.info(f"Analyzing around: {atm_strike}")

    # Process Option Chain for 9 Strikes (4 up, 4 down)
    expiry_date = payload['records']['expiryDates'][0]
    strikes = payload['records']['strikePrices']
    atm_idx = strikes.index(atm_strike)
    selected_strikes = strikes[atm_idx-4 : atm_idx+5]

    master_data = []
    for s in selected_strikes:
        # Filter logic to extract CE and PE data for the strike
        ce_data = next((x for x in payload['records']['data'] if x['strikePrice'] == s and 'CE' in x), None)
        pe_data = next((x for x in payload['records']['data'] if x['strikePrice'] == s and 'PE' in x), None)
        
        row = {
            "Strike": s,
            "CALL OI Chg": ce_data['CE']['changeinOpenInterest'] if ce_data else 0,
            "CALL % Chg": ce_data['CE']['pchangeinOpenInterest'] if ce_data else 0,
            "PE % Chg": pe_data['PE']['pchangeinOpenInterest'] if pe_data else 0,
            "PUT OI Chg": pe_data['PE']['changeinOpenInterest'] if pe_data else 0,
        }
        master_data.append(row)

    # Create DataFrame
    df = pd.DataFrame(master_data)

    # --- DISPLAY TABLE ---
    # Apply coloring (Green for Bullish OI, Red for Bearish)
    st.table(df.style.background_gradient(subset=['CALL OI Chg', 'PUT OI Chg'], cmap='RdYlGn'))

    # Auto-Refresh Trigger
    time.sleep(refresh_seconds)
    st.rerun()

else:
    st.warning("Waiting for NSE Server Response... Make sure market is open.")