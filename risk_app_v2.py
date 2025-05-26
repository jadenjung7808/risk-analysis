import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Risk Analyzer", layout="centered")
st.title("Portfolio Risk Analyzer")

# 🔍 Risk explanation (before stock inputs)
with st.expander("ℹ️ How We Calculate the Risk Score"):
    st.markdown("""
    Our risk score combines multiple indicators:

    - **Valuation Risk** → PE, PS (high = overvalued)  
    - **Financial Health** → D/E, Margin (low margin or high debt = high risk)  
    - **Market Sensitivity** → Beta, Volatility, Drawdown (unstable stocks)  
    - **Liquidity Risk** → Low trading volume = harder to exit  
    - **ESG Risk** → Higher ESG score = more sustainability concerns

    Each metric is normalized and weighted. The total score is on a 0–100 scale.
    """)

# 📘 What's not included
with st.expander("📘 Data Coverage & Limitations"):
    st.markdown("""
    - ✅ Public financial & market data from Yahoo Finance  
    - ✅ ESG score included (if available)  
    - ❌ Legal issues, controversy events, social media, employee ratings  
    - ❌ News-based or reputation risk

    This tool only covers measurable, publicly available quantitative data.
    """)

# 📥 Input section
if "tickers" not in st.session_state:
    st.session_state.tickers = [{"name": "", "amount": ""}]

def add_row():
    st.session_state.tickers.append({"name": "", "amount": ""})

def remove_row(index):
    st.session_state.tickers.pop(index)

st.button("➕ Add Stock", on_click=add_row)

portfolio = []
for i, entry in enumerate(st.session_state.tickers):
    cols = st.columns([2, 1, 0.3])
    name = cols[0].text_input(f"Stock {i+1}", value=entry["name"], key=f"name_{i}", placeholder="e.g., AAPL")
    amount = cols[1].text_input("Amount ($)", value=entry["amount"], key=f"amount_{i}", placeholder="$")
    remove = cols[2].button("❌", key=f"remove_{i}")
    if remove:
        remove_row(i)
        st.rerun()
    st.session_state.tickers[i]["name"] = name
    st.session_state.tickers[i]["amount"] = amount
    if name and amount.replace(".", "", 1).isdigit():
        portfolio.append((name.upper(), float(amount)))

selected_period = st.selectbox("Select Investment Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

#  Risk functions
def interpret_risk(score):
    if score is None: return "N/A"
    elif score <= 20: return "Extremely Low Risk"
    elif score <= 33: return "Very Low Risk"
    elif score <= 45: return "Low Risk"
    elif score <= 55: return "Moderate Risk"
    elif score <= 67: return "High Risk"
    elif score <= 80: return "Very High Risk"
    else: return "Extremely High Risk"

def risk_color(score):
    if score is None: return "#ecf0f1"
    elif score <= 20: return "rgba(52, 152, 219, 0.25)"
    elif score <= 33: return "rgba(93, 173, 226, 0.25)"
    elif score <= 45: return "rgba(46, 204, 113, 0.25)"
    elif score <= 55: return "rgba(244, 208, 63, 0.25)"
    elif score <= 67: return "rgba(230, 126, 34, 0.25)"
    elif score <= 80: return "rgba(231, 76, 60, 0.25)"
    else: return "rgba(0, 0, 0, 0.25)"

def volatility(returns): return np.std(returns)
def drawdown(close): return (close / close.cummax() - 1).min()
def beta_calc(returns, benchmark_returns):
    if len(returns) != len(benchmark_returns): return None
    cov_matrix = np.cov(returns, benchmark_returns)
    return cov_matrix[0, 1] / cov_matrix[1, 1]

def calculate_components(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        spy = yf.Ticker("SPY").history(period=period)
        if hist.empty or spy.empty: return None, {}

        close = hist["Close"]
        volume = hist["Volume"].mean()
        returns = close.pct_change().dropna()
        spy_returns = spy["Close"].pct_change().dropna()

        pe = stock.info.get("forwardPE") or 60
        ps = stock.info.get("priceToSalesTrailing12Months") or 15
        dy = stock.info.get("dividendYield")
        dte = stock.info.get("debtToEquity") or 300
        margin = stock.info.get("operatingMargins") or 0.2
        avg_volume = volume or 1000000
        esg = stock.info.get("esgScores", {}).get("totalEsg", 50)

        weights = {
            "PE": 0.14, "PS": 0.10, "D/E": 0.10, "Margin": 0.10,
            "Dividend": 0.05, "Volatility": 0.16, "Drawdown": 0.12,
            "Beta": 0.09, "Liquidity": 0.09, "ESG": 0.05
        }

        def score(x, scale): return min(x / scale, 1) * 100
        scores = {
            "PE": score(pe, 60) * weights["PE"],
            "PS": score(ps, 15) * weights["PS"],
            "D/E": score(dte, 300) * weights["D/E"],
            "Margin": score((1 - margin), 1) * weights["Margin"],
            "Dividend": (0 if dy else 100) * weights["Dividend"],
            "Volatility": score(vol, 0.05) * weights["Volatility"],
            "Drawdown": score(abs(dd), 0.3) * weights["Drawdown"],
            "Beta": score(beta or 1, 2) * weights["Beta"],
            "Liquidity": score(1000000 / avg_volume, 1) * weights["Liquidity"],
            "ESG": score(esg, 100) * weights["ESG"]
        }

        total_risk = round(sum(scores.values()), 2)
        return total_risk, scores
    except:
        return None, {}
if st.button("📊 Analyze Risk") and portfolio:
    st.markdown("---")
    risks = []
    total_amount = sum([amt for _, amt in portfolio])

    for ticker, amt in portfolio:
        r, _ = calculate_components(ticker, selected_period)
        if r is not None:
            risks.append((ticker, r, amt))

    if risks:
        portfolio_risk = round(sum(r * a for _, r, a in risks) / total_amount, 2)
        label = interpret_risk(portfolio_risk)
        bg_color = risk_color(portfolio_risk)
        st.markdown(f"""
            <div style="background-color:{bg_color}; padding:20px; border-radius:10px">
            <h2> Total Portfolio Risk: {portfolio_risk}%</h2>
            <p><b>Risk Level:</b> {label}</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("🔍 This percentage quantifies your portfolio’s total risk level based on valuation, volatility, fundamentals, liquidity, and ESG concerns.")

    for ticker, risk, amt in risks:
        st.subheader(f" {ticker} ({selected_period})")
        _, scores = calculate_components(ticker, selected_period)
        label = interpret_risk(risk)
        contribution = (risk * amt / total_amount)
        st.markdown(f" Contribution to Portfolio Risk: **{contribution:.1f}%**")

        top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        labels = [x[0] for x in top_scores]
        values = [x[1] for x in top_scores]
        colors = ["#3498db80", "#f39c1280", "#e74c3c80"]

        fig, ax = plt.subplots()
        bars = ax.bar(labels, values, color=colors)
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.1f}%', va='bottom', ha='center')
        ax.set_ylabel("Risk Contribution (%)")
        ax.set_title(f"{ticker} - Top 3 Risk Drivers")
        st.pyplot(fig)

#  Risk % Meaning Explanation
with st.expander("📘 Risk % ?"):
    st.markdown("""
    - **0–20%: Extremely Low Risk** — Very stable companies with strong financials and low volatility  
    - **20–33%: Very Low Risk** — Reliable firms with low debt and steady returns  
    - **33–45%: Low Risk** — Generally stable, may have modest risk factors  
    - **45–55%: Moderate Risk** — Balanced, but some volatility or debt  
    - **55–67%: High Risk** — Growth-oriented but potentially overvalued or volatile  
    - **67–80%: Very High Risk** — Speculative or financially stressed stocks  
    - **80–100%: Extremely High Risk** — Structurally weak, highly volatile, or hype-driven
    """)

# 📘 Risk Indicator Explanation
with st.expander("📘 Risk Indicators"):
    st.markdown("""
    - **PE (Price-to-Earnings Ratio)**: High PE = potentially overvalued → **Higher = Higher Risk**  
    - **PS (Price-to-Sales Ratio)**: High PS = poor revenue efficiency → **Higher = Higher Risk**  
    - **D/E (Debt-to-Equity)**: Higher debt load → **Higher = Higher Risk**  
    - **Operating Margin**: Low margin = weak profitability → **Lower = Higher Risk**  
    - **Dividend Yield**: No dividend = uncertain cash return → **Lower = Higher Risk**  
    - **Volatility**: Price fluctuation → **Higher = Higher Risk**  
    - **Drawdown**: Past large drops → **Larger = Higher Risk**  
    - **Beta**: Market sensitivity → **Higher = Higher Risk**  
    - **Liquidity (Avg Volume)**: Thin trading → **Lower volume = Higher Risk**  
    - **ESG Score**: High ESG score = more governance/social/environmental risk → **Higher = Higher Risk**
    """)
