import streamlit as st
import yfinance as yf
import numpy as np

st.set_page_config(page_title="Risk Analyzer", layout="centered")
st.title("Investment Risk Analyzer")

st.subheader("Enter stock information")
ticker = st.text_input("Stock Ticker (e.g., AAPL, MSFT, TSLA)", value="AAPL")
investment = st.number_input("Investment Amount (USD)", min_value=100.0, step=100.0)

# Risk category weights
category_weights = {
    "market": 0.4,
    "financial": 0.3,
    "valuation": 0.3
}

# Sector risk mapping
sector_risk_map = {
    "Technology": 60, "Energy": 80, "Healthcare": 40, "Financial Services": 55,
    "Industrials": 65, "Consumer Defensive": 35, "Utilities": 30,
    "Communication Services": 50, "Consumer Cyclical": 70,
    "Basic Materials": 60, "Real Estate": 70, "Unknown": 50
}

# Scoring functions
def score_volatility(std):
    return min(std * 1000, 100)

def score_drawdown(mdd):
    return min(abs(mdd) * 100, 100)

def score_beta(beta):
    return 50 if beta is None else min(abs(beta) * 50, 100)

def score_sector(sector):
    return sector_risk_map.get(sector, 50)

def score_debt_to_equity(dte):
    if dte is None or dte <= 0:
        return 80
    elif dte < 50:
        return 30
    elif dte <= 200:
        return 60
    else:
        return 90

def score_operating_margin(margin):
    if margin is None:
        return 80
    elif margin > 0.2:
        return 30
    elif margin > 0.1:
        return 50
    else:
        return 80

def score_div_yield(dy):
    if dy is None or dy <= 0:
        return 75
    elif dy >= 0.05:
        return 30
    elif dy >= 0.03:
        return 50
    else:
        return 65

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

# Main logic
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

            # MARKET RISK
            volatility_score = score_volatility(np.std(returns))
            drawdown_score = score_drawdown((close / close.cummax() - 1).min())
            beta_score = score_beta(info.get("beta"))
            sector_score = score_sector(info.get("sector", "Unknown"))

            market_risk = np.mean([volatility_score, drawdown_score, beta_score, sector_score])

            # FINANCIAL RISK
            dte_score = score_debt_to_equity(info.get("debtToEquity"))
            margin_score = score_operating_margin(info.get("operatingMargins"))
            dividend_score = score_div_yield(info.get("dividendYield"))

            financial_risk = np.mean([dte_score, margin_score, dividend_score])

            # VALUATION RISK
            ps_score = score_ps(info.get("priceToSalesTrailing12Months"))
            pe_score = score_pe(info.get("forwardPE"))

            valuation_risk = np.mean([ps_score, pe_score])

            # Weighted total risk
            overall_risk = (
                category_weights["market"] * market_risk +
                category_weights["financial"] * financial_risk +
                category_weights["valuation"] * valuation_risk
            )

            # Display result
            st.subheader(f"Total Risk Score: {round(overall_risk, 1)}%")
            if overall_risk <= 20:
                st.success("Risk Level: Very Low")
            elif overall_risk <= 40:
                st.success("Risk Level: Low")
            elif overall_risk <= 60:
                st.warning("Risk Level: Moderate")
            elif overall_risk <= 80:
                st.warning("Risk Level: High")
            else:
                st.error("Risk Level: Very High")

            st.markdown("### Risk Breakdown")
            st.write(f"Market Risk: {round(market_risk)}%")
            st.write(f"Financial Risk: {round(financial_risk)}%")
            st.write(f"Valuation Risk: {round(valuation_risk)}%")

            st.markdown("### Indicator Scores")
            st.write(f"Volatility: {round(volatility_score)}")
            st.write(f"Max Drawdown: {round(drawdown_score)}")
            st.write(f"Beta: {round(beta_score)}")
            st.write(f"Sector: {round(sector_score)}")
            st.write(f"Debt to Equity: {round(dte_score)}")
            st.write(f"Operating Margin: {round(margin_score)}")
            st.write(f"Dividend Yield: {round(dividend_score)}")
            st.write(f"P/S Ratio: {round(ps_score)}")
            st.write(f"Forward P/E: {round(pe_score)}")

    except Exception as e:
        st.error(f"An error occurred: {e}")
