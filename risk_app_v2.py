import streamlit as st
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Portfolio Risk Analyzer", layout="centered")
st.title("Portfolio Risk Analyzer")

st.markdown("This tool analyzes the risk of your portfolio based on individual stock risk and weighted exposure.")

st.markdown("### Enter Your Portfolio")

if "tickers" not in st.session_state:
    st.session_state.tickers = [""]

def add_row():
    st.session_state.tickers.append("")

st.button("➕ Add Stock", on_click=add_row)

portfolio = []
total_investment = 0

for i, ticker in enumerate(st.session_state.tickers):
    cols = st.columns([2, 1])
    stock = cols[0].text_input(f"Ticker {i+1}", value=st.session_state.tickers[i], key=f"ticker_{i}")
    amount = cols[1].number_input(f"Amount ${i+1}", min_value=0.0, step=100.0, key=f"amount_{i}")
    if stock:
        portfolio.append((stock.upper(), amount))
        total_investment += amount

# ----------------- Risk Scoring Functions -----------------

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

# ----------------- Portfolio Risk Calculation -----------------

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

            pe = score_pe(info.get("forwardPE"))
            ps = score_ps(info.get("priceToSalesTrailing12Months"))
            dy = score_div_yield(info.get("dividendYield"))
            dte = score_debt_to_equity(info.get("debtToEquity"))
            margin = score_operating_margin(info.get("operatingMargins"))
            vol = score_volatility(np.std(returns))
            dd = score_drawdown((close / close.cummax() - 1).min())
            beta = score_beta(info.get("beta"))

            # Base risk
            risk = np.mean([pe, ps, dy, dte, margin, vol, dd, beta])

            # Conditional multiplier: risky combo booster
            if ps > 10 and info.get("operatingMargins", 1) < 0.05:
                risk *= 1.2
            if pe > 50 and dte > 250:
                risk *= 1.15

            risk = min(risk, 100)

            weight = amount / total_investment
            weighted_risks.append(risk * weight)
            risk_contributions.append((ticker, risk, round(weight * 100, 1)))

        except Exception as e:
            st.error(f"{ticker}: Failed to analyze. {e}")

    if weighted_risks:
        total_risk = sum(weighted_risks)
        st.subheader(f"🔎 Total Portfolio Risk: {round(total_risk, 1)}%")

        if total_risk <= 20:
            st.success("Risk Level: Very Low")
        elif total_risk <= 40:
            st.success("Risk Level: Low")
        elif total_risk <= 60:
            st.warning("Risk Level: Moderate")
        elif total_risk <= 80:
            st.warning("Risk Level: High")
        else:
            st.error("Risk Level: Very High")

        st.markdown("### 📌 Stock Contributions")
        for t, r, w in risk_contributions:
            st.write(f"**{t}** — Risk: {round(r,1)}% | Weight: {w}%")
    else:
        st.warning("No valid stock data to calculate portfolio risk.")
