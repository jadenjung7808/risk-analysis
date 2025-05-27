import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Stable Risk Analyzer", layout="centered")
st.title("Portfolio Risk Analyzer (Stable Version)")

# ✅ 균형 잡힌 가중치 (안정성 강조)
weights = {
    "PE": 0.13, "PS": 0.10, "D/E": 0.13, "Margin": 0.13,
    "Dividend": 0.08, "Volatility": 0.10, "Drawdown": 0.10,
    "Beta": 0.08, "Liquidity": 0.10, "ESG": 0.05
}

# ✅ 조정된 스케일
scales = {
    "PE": 60, "PS": 15, "D/E": 300, "Margin": 1.0,
    "Volatility": 0.05, "Drawdown": 0.3, "Beta": 2.0,
    "Liquidity": 1_000_000, "ESG": 100
}

def normalize(x, key):
    try:
        if key == "Dividend":
            return 0 if (x is not None and x > 0) else 100
        x = abs(float(x))
        score = min(x / scales[key], 1.0) * 100
        return round(score, 2)
    except:
        return 50  # fallback 점수

def interpret_risk(score):
    if score <= 20: return "Extremely Low Risk"
    elif score <= 33: return "Very Low Risk"
    elif score <= 45: return "Low Risk"
    elif score <= 55: return "Moderate Risk"
    elif score <= 67: return "High Risk"
    elif score <= 80: return "Very High Risk"
    else: return "Extremely High Risk"

def risk_color(score):
    if score <= 20: return "#3498db"
    elif score <= 33: return "#5dade2"
    elif score <= 45: return "#2ecc71"
    elif score <= 55: return "#f4d03f"
    elif score <= 67: return "#e67e22"
    elif score <= 80: return "#e74c3c"
    else: return "#000000"

explanations = {
    "PE": "High PE = possibly overvalued.",
    "PS": "High PS = expensive vs. revenue.",
    "D/E": "High leverage risk.",
    "Margin": "Low margins = poor profitability.",
    "Dividend": "No dividend = less stable income.",
    "Volatility": "More price swings.",
    "Drawdown": "Biggest loss from peak.",
    "Beta": "Sensitivity to market.",
    "Liquidity": "Harder to sell if low volume.",
    "ESG": "Environmental/social/governance concerns."
}

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

selected_period = st.selectbox("Investment Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=3)

def calculate_risk(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if hist.empty:
            return None, {}, {}, False

        close = hist["Close"]
        returns = close.pct_change().dropna()
        price = close[-1]
        volume = hist["Volume"].mean()

        info = stock.info
        spy = yf.Ticker("SPY").history(period=period)
        spy_returns = spy["Close"].pct_change().dropna()

        pe = info.get("forwardPE", 60)
        ps = info.get("priceToSalesTrailing12Months", 15)
        dy = info.get("dividendYield", 0)
        dte = info.get("debtToEquity", 300)
        margin = info.get("operatingMargins", 0.2)
        beta = np.cov(returns, spy_returns)[0, 1] / np.cov(returns, spy_returns)[1, 1]
        liquidity = volume
        esg = info.get("esgScores", {}).get("totalEsg", 50)

        # 상장폐지 경고 조건
        delist_risk = price < 1 or liquidity < 10000 or info.get("quoteType", "") == "otc"

        raw_scores = {
            "PE": normalize(pe, "PE"),
            "PS": normalize(ps, "PS"),
            "D/E": normalize(dte, "D/E"),
            "Margin": normalize(1 - margin, "Margin"),
            "Dividend": normalize(dy, "Dividend"),
            "Volatility": normalize(np.std(returns), "Volatility"),
            "Drawdown": normalize((close / close.cummax() - 1).min(), "Drawdown"),
            "Beta": normalize(beta, "Beta"),
            "Liquidity": normalize(1_000_000 / liquidity, "Liquidity"),
            "ESG": normalize(esg, "ESG")
        }

        weighted = {k: raw_scores[k] * weights[k] for k in raw_scores}
        total = sum(weighted.values())
        if delist_risk:
            total = min(total + 30, 100)

        return round(total, 2), weighted, raw_scores, delist_risk
    except:
        return None, {}, {}, False

if st.button("📊 Analyze Risk"):
    if not portfolio:
        st.warning("⚠️ Please enter at least one stock.")
    else:
        results = []
        total_amt = sum(amt for _, amt in portfolio)
        for ticker, amt in portfolio:
            r, _, _, _ = calculate_risk(ticker, selected_period)
            if r is not None:
                results.append((ticker, r, amt))

        if results:
            port_score = round(sum(r * a for _, r, a in results) / total_amt, 2)
            st.markdown(f"""
                <div style="background-color:{risk_color(port_score)}; padding:20px; border-radius:10px">
                <h3>📈 Portfolio Risk: {port_score}%</h3>
                <b>{interpret_risk(port_score)}</b>
                </div>
            """, unsafe_allow_html=True)

        for ticker, score, amt in results:
            st.subheader(f"📍 {ticker}")
            score, weighted, raw, delist_flag = calculate_risk(ticker, selected_period)
            if delist_flag:
                st.error("⚠️ Delisting Warning: This stock may have regulatory or liquidity concerns.")

            st.markdown(f"**Risk Score: {score}% — {interpret_risk(score)}**")
            st.markdown(f"<div style='background-color:{risk_color(score)}; height:15px;'></div>", unsafe_allow_html=True)

            top3 = sorted(weighted.items(), key=lambda x: x[1], reverse=True)[:3]
            labels = [x[0] for x in top3]
            values = [x[1] for x in top3]

            col1, col2 = st.columns(2)
            with col1:
                fig, ax = plt.subplots()
                ax.bar(labels, values)
                ax.set_title("Top 3 Risk Drivers")
                st.pyplot(fig)

            with col2:
                angles = np.linspace(0, 2 * np.pi, len(raw), endpoint=False).tolist()
                values = list(raw.values())
                values += values[:1]
                angles += angles[:1]
                fig2, ax2 = plt.subplots(subplot_kw=dict(polar=True))
                ax2.plot(angles, values, 'o-', linewidth=2)
                ax2.fill(angles, values, alpha=0.25)
                ax2.set_xticks(angles[:-1])
                ax2.set_xticklabels(list(raw.keys()))
                ax2.set_title("Risk Radar")
                st.pyplot(fig2)

            st.markdown("### 📰 Related News")
            st.markdown(f"[Search {ticker} News on Google](https://www.google.com/search?q={ticker}+stock+news)")

            st.markdown("### 💡 Risk Factor Explanation")
            for k in labels:
                st.markdown(f"- **{k}**: {explanations[k]}")

with st.expander("Risk % ?"):
    st.markdown("""
- **0–20%**: Extremely Low Risk  
- **20–33%**: Very Low Risk  
- **33–45%**: Low Risk  
- **45–55%**: Moderate Risk  
- **55–67%**: High Risk  
- **67–80%**: Very High Risk  
- **80–100%**: Extremely High Risk  
""")

with st.expander("How We Calculate Risk"):
    st.markdown("""
- Weighted score from 10 indicators  
- Each score normalized and scaled 0–100  
- Delisting warning adds +30 risk  
- Final risk is capped at 100%  
""")
