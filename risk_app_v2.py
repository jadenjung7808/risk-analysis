import streamlit as st
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Portfolio Risk Analyzer", layout="centered")
st.title("High-Sensitivity Portfolio Risk Analyzer")

st.markdown("This tool analyzes the risk of your portfolio based on 10 financial and volatility indicators using a weighted model.")

# Risk % explanation
with st.expander("❓ What does the risk % mean?"):
    st.markdown("""
    **The risk percentage** represents how risky your stock or portfolio is on a scale from 0 to 100, based on factors like valuation, volatility, debt, and profitability.

    - **0–20%**: Extremely Low Risk — Similar to stable bonds or large-cap defensive stocks  
    - **20–33%**: Very Low Risk — Reliable companies with low volatility  
    - **33–45%**: Low Risk — Generally stable but some risk factors  
    - **45–55%**: Moderate Risk — Balanced profile with pros and cons  
    - **55–67%**: High Risk — Volatile or overvalued stocks  
    - **67–80%**: Very High Risk — Speculative or financially stressed companies  
    - **80–100%**: Extremely High Risk — Loss-making, hype-driven, or structurally weak firms
    """)

# Initialize session state
if "tickers" not in st.session_state:
    st.session_state.tickers = [{"name": "", "amount": ""}]

def add_row():
    st.session_state.tickers.append({"name": "", "amount": ""})

st.markdown("### 📌 Enter Stocks in Your Portfolio")
st.button("➕ Add Another Stock", on_click=add_row)

portfolio = []
total_investment = 0

for i, entry in enumerate(st.session_state.tickers):
    cols = st.columns([2, 1])
    name = cols[0].text_input(f"Stock Name {i+1}", value=entry["name"], key=f"name_{i}", placeholder="e.g., AAPL")
    amount_str = cols[1].text_input("Amount ($)", value=entry["amount"], key=f"amount_{i}")
    
    st.session_state.tickers[i]["name"] = name
    st.session_state.tickers[i]["amount"] = amount_str

    if name and amount_str.replace(".", "", 1).isdigit():
        amount = float(amount_str)
        portfolio.append((name.upper(), amount))
        total_investment += amount

# --- Scoring Functions ---
def score_pe(pe): return 100 if pe is None or pe <= 0 else 30 if pe <= 10 else 50 if pe <= 25 else 65 if pe <= 40 else 85 if pe <= 60 else 100
def score_ps(ps): return 90 if ps is None or ps <= 0 else 30 if ps <= 2 else 50 if ps <= 6 else 65 if ps <= 10 else 85 if ps <= 15 else 100
def score_div_yield(dy): return 80 if dy is None or dy <= 0 else 30 if dy >= 0.05 else 50 if dy >= 0.03 else 65
def score_debt_to_equity(dte): return 85 if dte is None or dte <= 0 else 30 if dte <= 50 else 50 if dte <= 100 else 65 if dte <= 200 else 85 if dte <= 300 else 100
def score_operating_margin(margin): return 80 if margin is None else 30 if margin > 0.2 else 50 if margin > 0.1 else 75
def score_volatility(std): return min(std * 1500, 100)
def score_drawdown(mdd): return min(abs(mdd) * 130, 100)
def score_beta(beta): return 50 if beta is None else min(abs(beta) * 60, 100)

# --- Weighted Risk Calculation ---
def weighted_score(pe, ps, dy, dte, margin, vol, dd, beta):
    weights = {
        "pe": 0.18, "ps": 0.12,
        "dte": 0.12, "margin": 0.12, "div": 0.06,
        "vol": 0.16, "dd": 0.12, "beta": 0.12
    }
    return (
        score_pe(pe) * weights["pe"] +
        score_ps(ps) * weights["ps"] +
        score_div_yield(dy) * weights["div"] +
        score_debt_to_equity(dte) * weights["dte"] +
        score_operating_margin(margin) * weights["margin"] +
        score_volatility(vol) * weights["vol"] +
        score_drawdown(dd) * weights["dd"] +
        score_beta(beta) * weights["beta"]
    )

def interpret_risk(score):
    if score <= 20: return "Extremely Low Risk"
    elif score <= 33: return "Very Low Risk"
    elif score <= 45: return "Low Risk"
    elif score <= 55: return "Moderate Risk"
    elif score <= 67: return "High Risk"
    elif score <= 80: return "Very High Risk"
    else: return "Extremely High Risk"

# --- Portfolio Analysis ---
if st.button("📊 Analyze Portfolio Risk") and portfolio and total_investment > 0:
    st.markdown("---")
    st.markdown("## 🧮 Portfolio Risk Results")
    risk_contributions = []
    weighted_risks = []

    for ticker, amount in portfolio:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1y")
            info = stock.info

            if hist.empty:
                st.warning(f"No data for {ticker}")
                continue

            close = hist["Close"]
            returns = close.pct_change().dropna()

            pe = info.get("forwardPE")
            ps = info.get("priceToSalesTrailing12Months")
            dy = info.get("dividendYield")
            dte = info.get("debtToEquity")
            margin = info.get("operatingMargins")
            vol = np.std(returns)
            dd = (close / close.cummax() - 1).min()
            beta = info.get("beta")

            risk = weighted_score(pe, ps, dy, dte, margin, vol, dd, beta)

            if ps and ps > 10 and (margin or 0) < 0.05:
                risk *= 1.2
            if pe and pe > 50 and dte and dte > 250:
                risk *= 1.15

            risk = min(risk, 100)

            weight = amount / total_investment
            weighted_risks.append(risk * weight)
            risk_contributions.append((ticker, risk, round(weight * 100, 1)))

        except Exception as e:
            st.error(f"{ticker}: Failed to analyze. {e}")

    if weighted_risks:
        total_risk = sum(weighted_risks)
        st.subheader(f"🔎 Total Portfolio Risk: {round(total_risk, 1)}% — {interpret_risk(total_risk)}")

        st.markdown("### 📌 Stock Contributions")
        for t, r, w in risk_contributions:
            st.write(f"**{t}** — Risk: {round(r,1)}% | Weight: {w}%")
    else:
        st.warning("No valid stock data to calculate portfolio risk.")
