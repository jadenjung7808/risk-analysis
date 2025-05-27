import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Risk Analyzer", layout="centered")
st.title("Portfolio Risk Analyzer")

# ✅ 통합 설명 버튼
with st.expander("ℹ️ How We Calculate Risk & What Data We Use"):
    st.markdown("""
    ### 🔢 How We Calculate the Risk Score
    Our score is based on 10 indicators. Each is normalized and weighted:

    **Valuation Risk**
    - PE Ratio: Higher = more overvalued → Higher Risk
    - PS Ratio: Higher = more expensive vs. revenue → Higher Risk

    **Financial Health**
    - Debt-to-Equity: Higher = more leverage → Higher Risk
    - Operating Margin: Lower = less profitable → Higher Risk
    - Dividend Yield: Low or none = uncertain income → Higher Risk

    **Market Behavior**
    - Volatility: Higher = more unstable → Higher Risk
    - Drawdown: Larger = more vulnerable to loss → Higher Risk
    - Beta: Higher = more sensitive to market → Higher Risk

    **Liquidity**
    - Avg Volume: Lower = harder to sell → Higher Risk

    **Sustainability**
    - ESG Score: Higher = more governance/environment/social concern → Higher Risk

    ### 📘 Data Limitations
    - ✅ Uses Yahoo Finance for all financials
    - ✅ ESG scores if available
    - ❌ No legal, news, controversy, employee ratings
    """)

# 📥 사용자 입력
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

def calculate_components(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        spy = yf.Ticker("SPY").history(period=period)
        if hist.empty or spy.empty:
            return None, {}

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
            "Volatility": score(np.std(returns), 0.05) * weights["Volatility"],
            "Drawdown": score((close / close.cummax() - 1).min(), 0.3) * weights["Drawdown"],
            "Beta": score(np.cov(returns, spy_returns)[0,1] / np.cov(returns, spy_returns)[1,1], 2) * weights["Beta"],
            "Liquidity": score(1000000 / avg_volume, 1) * weights["Liquidity"],
            "ESG": score(esg, 100) * weights["ESG"]
        }

        return round(sum(scores.values()), 2), scores
    except:
        return None, {}

# 📊 결과 표시
if st.button("📊 Analyze Risk"):
    if not portfolio:
        st.warning("⚠️ Please enter at least one valid stock and amount.")
    else:
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
                <h2>📌 Total Portfolio Risk: {portfolio_risk}%</h2>
                <p><b>Risk Level:</b> {label}</p>
                </div>
            """, unsafe_allow_html=True)

        for ticker, risk, amt in risks:
            st.subheader(f"📍 {ticker} ({selected_period})")
            _, scores = calculate_components(ticker, selected_period)
            contribution = (risk * amt / total_amount)
            st.markdown(f"📌 Contribution to Portfolio Risk: **{contribution:.1f}%**")

            top_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
            labels = [x[0] for x in top_scores]
            values = [x[1] for x in top_scores]

            col1, col2 = st.columns(2)

            with col1:
                fig, ax = plt.subplots()
                ax.bar(labels, values, color=["#3498db80", "#f39c1280", "#e74c3c80"])
                ax.set_ylabel("Contribution (%)")
                ax.set_title("Top 3 Risk Drivers")
                st.pyplot(fig)

            with col2:
                radar_labels = list(scores.keys())
                radar_values = [scores[k] for k in radar_labels]
                angles = np.linspace(0, 2 * np.pi, len(radar_labels), endpoint=False).tolist()
                radar_values += radar_values[:1]
                angles += angles[:1]
                fig, ax = plt.subplots(subplot_kw=dict(polar=True))
                ax.plot(angles, radar_values, 'o-', linewidth=2)
                ax.fill(angles, radar_values, alpha=0.25)
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(radar_labels)
                ax.set_title("Risk Profile (Radar Chart)", size=12)
                st.pyplot(fig)

# 📊 리스크 퍼센트 의미 설명
with st.expander(" Risk % ?"):
    st.markdown("""
    - **0–20%: Extremely Low Risk**  
      → Blue-chip stocks like JNJ, KO. Ideal for long-term safety.  
    - **20–33%: Very Low Risk**  
      → Solid fundamentals with minimal volatility  
    - **33–45%: Low Risk**  
      → Generally stable, but some weakness  
    - **45–55%: Moderate Risk**  
      → Balanced but with noticeable risk signals  
    - **55–67%: High Risk**  
      → Volatile, growth-heavy or overvalued firms  
    - **67–80%: Very High Risk**  
      → Speculative or unstable business model  
    - **80–100%: Extremely High Risk**  
      → Loss-making, hype-driven, or distressed companies
    """)
