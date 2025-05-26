import streamlit as st
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Portfolio Risk Analyzer", layout="centered")
st.title("Portfolio Risk Analyzer")

st.markdown("This tool analyzes the risk of your portfolio based on 10 financial and volatility indicators using a weighted model.")

# Risk % explanation
with st.expander("❓ What does the risk % mean?"):
    st.markdown("""
    - **0–20%**: Extremely Low Risk  
    - **20–33%**: Very Low Risk  
    - **33–45%**: Low Risk  
    - **45–55%**: Moderate Risk  
    - **55–67%**: High Risk  
    - **67–80%**: Very High Risk  
    - **80–100%**: Extremely High Risk  
    """)

# Fixed input table
st.markdown("### 📌 Enter Up to 5 Stocks")
portfolio = []
total_investment = 0

for i in range(5):
    cols = st.columns([2, 1])
    name = cols[0].text_input(f"Stock Name {i+1}", key=f"name_{i}", placeholder="e.g., AAPL")
    amount = cols[1].number_input("Amount ($)", min_value=0.0, step=100.0, key=f"amount_{i}")
    
    if name:
        portfolio.append((name.upper(), amount))
        total_investment += amount

# ----------------- Scoring Functions -----------------

def score_pe(pe):
    if pe is None or pe <= 0:
        return 100
    elif pe > 60:
        return 100
    elif pe > 40:
        return 85
    elif pe > 25:
        return 65
    elif pe > 10:
        return 50
    else:
        return 30

def score_ps(ps):
    if ps is None or ps <= 0:
        return 90
    elif ps > 15:
        return 100
    elif ps > 10:
        return 85
    elif ps > 6:
        return 65
    elif ps > 2:
        return 50
    else:
        return 30

def score_div_yield(dy):
    if dy is None or dy <= 0:
        return 80
    elif dy >= 0.05:
        return 30
    elif dy >= 0.03:
        return 50
    else:
        return 65

def score_debt_to_equity(dte):
    if dte is None or dte <= 0:
        return 85
    elif dte > 300:
        return 100
    elif dte > 200:
        return 85
    elif dte > 100:
        return 65
    elif dte > 50:
        return 50
    else:
        return 30

def score_operating_margin(margin):
    if margin is None:
        return 80
    elif margin > 0.2:
        return 30
    elif margin > 0.1:
        return 50
    else:
        return 75

def score_volatility(std):
    return min(std * 1500, 100)

def score_drawdown(mdd):
    return min(abs(mdd) * 130, 100)

def score_beta(beta):
    if beta is None:
        return 50
    return min(abs(beta) * 60, 100)

# ----------------- Risk Calculation -----------------

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
    if score <= 20:
        return "Extremely Low Risk"
    elif score <= 33:
        return "Very Low Risk"
    elif score <= 45:
        return "Low Risk"
    elif score <= 55:
        return "Moderate Risk"
    elif score <= 67:
        return "High Risk"
    elif score <= 80:
        return "Very High Risk"
    else:
        return "Extremely High Risk"

# ----------------- Portfolio Analysis -----------------

if st.button("Analyze Portfolio Risk") and portfolio and total_investment > 0:
    st.markdown("---")
    st.markdown("## Portfolio Risk Results")
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

        st.markdown("### Stock Contributions")
        for t, r, w in risk_contributions:
            st.write(f"**{t}** — Risk: {round(r,1)}% | Weight: {w}%")
    else:
        st.warning("No valid stock data to calculate portfolio risk.")
