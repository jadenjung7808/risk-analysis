import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Risk Analyzer", layout="centered")
st.title("Portfolio Risk Analyzer")

# 리스크 설명 및 데이터 범위
with st.expander("ℹ️ How We Calculate Risk & What Data We Use"):
    st.markdown("""
    ### How We Calculate the Risk Score
    Our score is based on 10 normalized and weighted indicators:

    - PE Ratio: Higher = more overvalued → Higher Risk  
    - PS Ratio: Higher = expensive vs. revenue → Higher Risk  
    - Debt-to-Equity: Higher = more debt → Higher Risk  
    - Operating Margin: Lower = less profit → Higher Risk  
    - Dividend Yield: Low or none → Higher Risk  
    - Volatility: Higher = unstable → Higher Risk  
    - Drawdown: Larger = vulnerable to loss → Higher Risk  
    - Beta: Higher = more sensitive to market → Higher Risk  
    - Liquidity: Lower volume = harder to exit → Higher Risk  
    - ESG Score: Higher = more sustainability concerns → Higher Risk

    ### 📘 Data Limitations
    - ✅ Yahoo Finance data, incl. ESG (if available)  
    - ❌ No news/controversy/employee review data
    """)

# Top 3 설명용 딕셔너리
indicator_explanations = {
    "PE": "A high PE ratio may indicate the stock is overvalued relative to earnings.",
    "PS": "A high PS ratio suggests the stock is expensive compared to its revenue.",
    "D/E": "A high debt-to-equity ratio means the company is heavily leveraged.",
    "Margin": "A low operating margin signals poor profitability.",
    "Dividend": "No or low dividend yield could mean unreliable passive income.",
    "Volatility": "High volatility reflects price instability.",
    "Drawdown": "Severe past drawdowns may indicate vulnerability to crashes.",
    "Beta": "A high beta implies greater sensitivity to market movements.",
    "Liquidity": "Low trading volume can cause difficulty in buying or selling.",
    "ESG": "High ESG score signals environmental, social, or governance concerns."
}

# 종목 입력
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

# 투자 기간
selected_period = st.selectbox("Select Investment Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

# 리스크 해석
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

# 리스크 계산
def calculate_components(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        spy = yf.Ticker("SPY").history(period=period)
        if hist.empty or spy.empty: return None, {}, {}

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

        def normalize(x, scale): return min(x / scale, 1) * 100

        raw_scores = {
            "PE": normalize(pe, 60),
            "PS": normalize(ps, 15),
            "D/E": normalize(dte, 300),
            "Margin": normalize((1 - margin), 1),
            "Dividend": 0 if dy else 100,
            "Volatility": normalize(np.std(returns), 0.05),
            "Drawdown": normalize((close / close.cummax() - 1).min(), 0.3),
            "Beta": normalize(np.cov(returns, spy_returns)[0, 1] / np.cov(returns, spy_returns)[1, 1], 2),
            "Liquidity": normalize(1000000 / avg_volume, 1),
            "ESG": normalize(esg, 100)
        }

        weighted_scores = {k: raw_scores[k] * weights[k] for k in raw_scores}
        total_risk = round(sum(weighted_scores.values()), 2)

        return total_risk, weighted_scores, raw_scores
    except:
        return None, {}, {}

# 분석 시작
if st.button("📊 Analyze Risk"):
    if not portfolio:
        st.warning("⚠️ Please enter at least one valid stock and amount.")
    else:
        risks = []
        total_amount = sum([amt for _, amt in portfolio])
        for ticker, amt in portfolio:
            r, _, _ = calculate_components(ticker, selected_period)
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

        for ticker, risk, amt in risks:
            st.subheader(f"📍 {ticker} ({selected_period})")
            _, weighted_scores, raw_scores = calculate_components(ticker, selected_period)
            contribution = (risk * amt / total_amount)
            st.markdown(f" Contribution to Portfolio Risk: **{contribution:.1f}%**")

            top_scores = sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True)[:3]
            labels = [x[0] for x in top_scores]
            values = [x[1] for x in top_scores]

            col1, col2 = st.columns(2)

            with col1:
                fig, ax = plt.subplots()
                ax.bar(labels, values, color=["#3498db80", "#f39c1280", "#e74c3c80"])
                ax.set_ylabel("Weighted Contribution (%)")
                ax.set_title("Top 3 Risk Drivers")
                st.pyplot(fig)

            with col2:
                radar_labels = list(raw_scores.keys())
                radar_values = [raw_scores[k] for k in radar_labels]
                angles = np.linspace(0, 2 * np.pi, len(radar_labels), endpoint=False).tolist()
                radar_values += radar_values[:1]
                angles += angles[:1]
                fig, ax = plt.subplots(subplot_kw=dict(polar=True))
                ax.plot(angles, radar_values, 'o-', linewidth=2)
                ax.fill(angles, radar_values, alpha=0.25)
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(radar_labels)
                ax.set_title("Risk Profile (Raw Score)", size=11)
                st.pyplot(fig)

            # Top 3 설명 및 뉴스 링크
            st.markdown("### Explanation of Top Risk Factors")
            for factor in labels:
                desc = indicator_explanations.get(factor, "No explanation available.")
                link = f"https://www.google.com/search?q={ticker}+{factor}+stock+news"
                st.markdown(f"**{factor}**: {desc}  \n🔗 [Search News]({link})", unsafe_allow_html=True)

# 리스크 퍼센트 의미 설명
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
