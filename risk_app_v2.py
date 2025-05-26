import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Risk Analyzer", layout="centered")
st.title("Portfolio Risk Analyzer")

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
        if hist.empty or spy.empty:
            return None, {}

        close = hist["Close"]
        returns = close.pct_change().dropna()
        spy_returns = spy["Close"].pct_change().dropna()

        pe = stock.info.get("forwardPE") or 60
        ps = stock.info.get("priceToSalesTrailing12Months") or 15
        dy = stock.info.get("dividendYield")
        dte = stock.info.get("debtToEquity") or 300
        margin = stock.info.get("operatingMargins") or 0.2

        vol = volatility(returns)
        dd = drawdown(close)
        beta = beta_calc(returns, spy_returns)

        weights = {"PE": 0.18, "PS": 0.12, "D/E": 0.12, "Margin": 0.12,
                   "Dividend": 0.06, "Volatility": 0.16, "Drawdown": 0.12, "Beta": 0.12}

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
            <h2>Total Portfolio Risk: {portfolio_risk}%</h2>
            <p><b>Risk Level:</b> {label}</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown(" This percentage quantifies your portfolio’s total risk level based on valuation, debt, volatility, and market sensitivity.")

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

with st.expander("❓Risk %?"):
    st.markdown("""
    - **0–20%: Extremely Low Risk** — Very stable companies with strong financials and low volatility  
    - **20–33%: Very Low Risk** — Reliable firms with low debt and steady returns  
    - **33–45%: Low Risk** — Generally stable, may have modest risk factors  
    - **45–55%: Moderate Risk** — Balanced, but some volatility or debt  
    - **55–67%: High Risk** — Growth-oriented but potentially overvalued or volatile  
    - **67–80%: Very High Risk** — Speculative or financially stressed stocks  
    - **80–100%: Extremely High Risk** — Structurally weak, highly volatile, or hype-driven
    """)

with st.expander("❓Risk Indicators"):
    st.markdown("""
    - **PE (Price-to-Earnings Ratio)**: High PE means potentially overvalued → **Higher = Higher Risk**  
    - **PS (Price-to-Sales Ratio)**: High PS suggests high price vs revenue → **Higher = Higher Risk**  
    - **D/E (Debt-to-Equity Ratio)**: More debt = more risk → **Higher = Higher Risk**  
    - **Operating Margin**: Low margin = inefficiency → **Lower = Higher Risk**  
    - **Dividend Yield**: No dividends = uncertain returns → **Lower = Higher Risk**  
    - **Volatility**: Fluctuating price → **Higher = Higher Risk**  
    - **Drawdown**: Large past losses → **Larger = Higher Risk**  
    - **Beta**: Sensitivity to market → **Higher = Higher Risk**
    """)
