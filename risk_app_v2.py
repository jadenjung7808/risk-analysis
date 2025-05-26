import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Investment Risk Analyzer", layout="centered")
st.title("🎯 Enhanced Risk Analyzer")

st.markdown("Enter a stock ticker and investment amount to analyze risk based on selected time period.")

st.markdown("### Enter Your Portfolio")

ticker = st.text_input("Stock Name", value="", placeholder="e.g., AAPL")
amount = st.text_input("Investment Amount (USD)", value="", placeholder="$")

selected_period = st.selectbox("Select Investment Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

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
    elif score <= 20: return "rgba(52, 152, 219, 0.25)"     # Blue
    elif score <= 33: return "rgba(93, 173, 226, 0.25)"     # Sky
    elif score <= 45: return "rgba(46, 204, 113, 0.25)"     # Green
    elif score <= 55: return "rgba(244, 208, 63, 0.25)"     # Yellow
    elif score <= 67: return "rgba(230, 126, 34, 0.25)"     # Orange
    elif score <= 80: return "rgba(231, 76, 60, 0.25)"      # Red
    else: return "rgba(0, 0, 0, 0.25)"                      # Black

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
        if hist.empty or spy.empty:
            return None, {}

        close = hist["Close"]
        returns = close.pct_change().dropna()
        spy_returns = spy["Close"].pct_change().dropna()

        pe = stock.info.get("forwardPE")
        ps = stock.info.get("priceToSalesTrailing12Months")
        dy = stock.info.get("dividendYield")
        dte = stock.info.get("debtToEquity")
        margin = stock.info.get("operatingMargins")

        vol = volatility(returns)
        dd = drawdown(close)
        beta = beta_calc(returns, spy_returns)

        weights = {"PE": 0.18, "PS": 0.12, "D/E": 0.12, "Margin": 0.12,
                   "Dividend": 0.06, "Volatility": 0.16, "Drawdown": 0.12, "Beta": 0.12}

        def score(x, scale): return 100 if x is None else min(x / scale, 1) * 100
        scores = {
            "PE": score(pe if pe and pe > 0 else 60, 60) * weights["PE"],
            "PS": score(ps if ps and ps > 0 else 15, 15) * weights["PS"],
            "D/E": score(dte if dte and dte > 0 else 300, 300) * weights["D/E"],
            "Margin": score((1 - margin) if margin else 0.8, 1) * weights["Margin"],
            "Dividend": (0 if dy else 100) * weights["Dividend"],
            "Volatility": score(vol, 0.05) * weights["Volatility"],
            "Drawdown": score(abs(dd), 0.3) * weights["Drawdown"],
            "Beta": score(beta, 2) * weights["Beta"],
        }

        total_risk = sum(scores.values())
        return total_risk, scores
    except:
        return None, {}

if st.button("Analyze Risk") and ticker and amount.replace(".", "", 1).isdigit():
    ticker = ticker.upper()
    st.markdown("---")
    st.subheader(f"🧾 {ticker} — Period: {selected_period}")
    risk, components = calculate_components(ticker, selected_period)

    if risk is not None:
        interpretation = interpret_risk(risk)
        bg_color = risk_color(risk)
        st.markdown(f"""
            <div style="background-color:{bg_color}; padding:20px; border-radius:10px">
            <h3>📌 Total Risk: {round(risk,1)}%</h3>
            <p><b>Risk Level:</b> {interpretation}</p>
            </div>
        """, unsafe_allow_html=True)

        sorted_scores = sorted(components.items(), key=lambda x: x[1], reverse=True)[:3]
        labels = [item[0] for item in sorted_scores]
        values = [item[1] for item in sorted_scores]
        colors = ["#3498db80", "#f39c1280", "#e74c3c80"]

        fig, ax = plt.subplots()
        ax.bar(labels, values, color=colors)
        ax.set_ylabel("Risk Contribution (%)")
        ax.set_title("Top 3 Risk Contributors")
        st.pyplot(fig)

with st.expander("ℹ️ Indicator Descriptions"):
    st.markdown("""
    - **PE (Price-to-Earnings Ratio)**: Indicates how much investors are paying for $1 of earnings. High PE may signal overvaluation.
    - **PS (Price-to-Sales Ratio)**: Compares stock price to revenues. High PS may indicate overpricing relative to sales.
    - **D/E (Debt-to-Equity)**: Measures financial leverage. High D/E = high risk of default.
    - **Operating Margin**: Profitability indicator. Low margin = inefficient operations = higher risk.
    - **Dividend Yield**: Indicates cash return. No dividend = potentially risky growth stock.
    - **Volatility**: Price fluctuation intensity. Higher volatility = higher risk.
    - **Drawdown**: Maximum historical drop from peak. Reflects loss potential.
    - **Beta**: Sensitivity to market movements. Higher beta = more reactive to market swings.
    """)
