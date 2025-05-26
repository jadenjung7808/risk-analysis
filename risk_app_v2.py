
import streamlit as st
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Investment Risk Analyzer", layout="centered")
st.title("Investment Risk Percentage Calculator")

st.subheader("Enter stock information")
ticker = st.text_input("Stock Ticker (e.g., AAPL, MSFT, TSLA)", value="AAPL")
investment = st.number_input("Investment Amount (USD)", min_value=100.0, step=100.0)

weights = {
    "volatility": 0.25,
    "max_drawdown": 0.10,
    "beta": 0.05,
    "sector": 0.05,
    "concentration": 0.05,
    "debt_to_equity": 0.20,
    "operating_margin": 0.10,
    "dividend_yield": 0.03,
    "ps_ratio": 0.10,
    "forward_pe": 0.07
}

sector_risk_map = {
    "Technology": 60, "Energy": 80, "Healthcare": 40, "Financial Services": 55,
    "Industrials": 65, "Consumer Defensive": 35, "Utilities": 30,
    "Communication Services": 50, "Consumer Cyclical": 70,
    "Basic Materials": 60, "Real Estate": 70, "Unknown": 50
}

def score_pe(pe):
    if pe is None or pe <= 0:
        return 90
    elif pe < 10:
        return 40
    elif pe <= 25:
        return 60
    elif pe <= 40:
        return 75
    else:
        return 90

def score_ps(ps):
    if ps is None or ps <= 0:
        return 80
    elif ps < 2:
        return 30
    elif ps <= 6:
        return 50
    elif ps <= 10:
        return 70
    else:
        return 90

def score_div_yield(dy):
    if dy is None or dy <= 0:
        return 75
    elif dy >= 0.05:
        return 30
    elif dy >= 0.03:
        return 50
    else:
        return 65

if st.button("Analyze Risk") and ticker:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")

        if hist.empty:
            st.error("Failed to load historical price data.")
        else:
            info = stock.info
            close = hist["Close"]
            returns = close.pct_change().dropna()

            volatility = np.std(returns)
            volatility_score = min(volatility * 1000, 100)

            running_max = close.cummax()
            drawdown = (close - running_max) / running_max
            max_dd = drawdown.min()
            drawdown_score = min(abs(max_dd) * 100, 100)

            beta_score = min(abs(info.get("beta", 1)) * 50, 100)

            sector = info.get("sector", "Unknown")
            sector_score = sector_risk_map.get(sector, 50)

            concentration_score = 80

            dte = info.get("debtToEquity", None)
            debt_score = 80 if dte is None else min(dte * 0.2, 100)

            margin = info.get("operatingMargins", None)
            margin_score = 80
            if margin is not None:
                margin_score = 100 - (margin * 200)
                margin_score = max(min(margin_score, 100), 0)

            div_yield = info.get("dividendYield", None)
            div_score = score_div_yield(div_yield)

            ps = info.get("priceToSalesTrailing12Months", None)
            ps_score = score_ps(ps)

            pe = info.get("forwardPE", None)
            pe_score = score_pe(pe)

            risk_percent = (
                weights["volatility"] * volatility_score +
                weights["max_drawdown"] * drawdown_score +
                weights["beta"] * beta_score +
                weights["sector"] * sector_score +
                weights["concentration"] * concentration_score +
                weights["debt_to_equity"] * debt_score +
                weights["operating_margin"] * margin_score +
                weights["dividend_yield"] * div_score +
                weights["ps_ratio"] * ps_score +
                weights["forward_pe"] * pe_score
            )

            st.subheader(f"Overall Risk: {round(risk_percent, 1)}%")
            if risk_percent <= 20:
                st.success("Risk Level: Very Low")
            elif risk_percent <= 40:
                st.success("Risk Level: Low")
            elif risk_percent <= 60:
                st.warning("Risk Level: Moderate")
            elif risk_percent <= 80:
                st.warning("Risk Level: High")
            else:
                st.error("Risk Level: Very High")

            st.markdown("### Breakdown by Indicator")
            st.write(f"Volatility: {round(volatility_score)}")
            st.write(f"Max Drawdown: {round(drawdown_score)}")
            st.write(f"Beta: {round(beta_score)}")
            st.write(f"Sector Risk: {round(sector_score)}")
            st.write(f"Concentration: {concentration_score}")
            st.write(f"Debt to Equity: {round(debt_score)}")
            st.write(f"Operating Margin: {round(margin_score)}")
            st.write(f"Dividend Yield: {round(div_score)}")
            st.write(f"P/S Ratio: {round(ps_score)}")
            st.write(f"Forward P/E: {round(pe_score)}")

    except Exception as e:
        st.error(f"An error occurred: {e}")
