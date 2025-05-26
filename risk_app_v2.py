import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Investment Risk Analyzer", layout="centered")
st.title("Investment Risk Analyzer")

st.markdown("Analyze risk of individual stocks based on financial and volatility indicators across different investment periods.")

if "tickers" not in st.session_state:
    st.session_state.tickers = [{"name": "", "amount": ""}]

def add_row():
    st.session_state.tickers.append({"name": "", "amount": ""})

def remove_row(index):
    st.session_state.tickers.pop(index)

portfolio = []
total_investment = 0

st.button("➕ Add Stock", on_click=add_row)

for i, entry in enumerate(st.session_state.tickers):
    cols = st.columns([2, 1, 0.3])
    name = cols[0].text_input(f"Stock Name {i+1}", value=entry["name"], key=f"name_{i}", placeholder="e.g., AAPL")
    amount = cols[1].text_input("Amount ($)", value=entry["amount"], key=f"amount_{i}", placeholder="$")
    remove = cols[2].button("❌", key=f"remove_{i}")
    if remove:
        remove_row(i)
        st.rerun()
    st.session_state.tickers[i]["name"] = name
    st.session_state.tickers[i]["amount"] = amount
    if name and amount.replace(".", "", 1).isdigit():
        portfolio.append((name.upper(), float(amount)))
        total_investment += float(amount)

custom_periods = st.multiselect("Select additional custom periods", ["1mo", "3mo", "6mo", "1y", "2y"], default=["6mo"])

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
    if score is None: return "#bdc3c7"
    elif score <= 20: return "#3498db"
    elif score <= 33: return "#5dade2"
    elif score <= 45: return "#2ecc71"
    elif score <= 55: return "#f4d03f"
    elif score <= 67: return "#e67e22"
    elif score <= 80: return "#e74c3c"
    else: return "#000000"

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

if st.button("Analyze Risk") and portfolio:
    for ticker, amount in portfolio:
        st.markdown(f"---\n### 🧾 {ticker}")
        short, _ = calculate_components(ticker, "1mo")
        long, _ = calculate_components(ticker, "1y")
        st.markdown(f"**Short-Term Risk (1mo):** `{round(short,1) if short else 'N/A'}%` — {interpret_risk(short)}")
        st.markdown(f"**Long-Term Risk (1y):** `{round(long,1) if long else 'N/A'}%` — {interpret_risk(long)}")

        for cp in custom_periods:
            risk, scores = calculate_components(ticker, cp)
            st.markdown(f"**Custom Period Risk ({cp}):** `{round(risk,1) if risk else 'N/A'}%` — {interpret_risk(risk)}")
            if scores:
                labels = list(scores.keys())
                values = list(scores.values())
                fig, ax = plt.subplots()
                ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
                ax.axis("equal")
                st.markdown(f"**Risk Contribution Breakdown (Period: {cp})**")
                st.pyplot(fig)

with st.expander("ℹ️ risk %?"):
    st.markdown("""
    <div style='font-size:15px'>
    <b>Risk Level Interpretation</b><br><br>
    <span style='color:#3498db'><b>0–20%</b>: Extremely Low Risk</span> — peaceful<br>
    <span style='color:#5dade2'><b>20–33%</b>: Very Low Risk</span> — Reliable companies with low volatility<br>
    <span style='color:#2ecc71'><b>33–45%</b>: Low Risk</span> — Generally stable but some risk factors<br>
    <span style='color:#f4d03f'><b>45–55%</b>: Moderate Risk</span> — Balanced profile<br>
    <span style='color:#e67e22'><b>55–67%</b>: High Risk</span> — Volatile or overvalued stocks<br>
    <span style='color:#e74c3c'><b>67–80%</b>: Very High Risk</span> — Speculative or financially stressed companies<br>
    <span style='color:#000000'><b>80–100%</b>: Extremely High Risk</span> — Loss-making, hype-driven, or structurally weak firms
    </div>
    """, unsafe_allow_html=True)
