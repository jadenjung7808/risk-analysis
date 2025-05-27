import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Risk Analyzer", layout="centered")
st.title("Portfolio Risk Analyzer")

# 가중치
weights = {
    "PE": 0.18, "PS": 0.12, "D/E": 0.15, "Margin": 0.15,
    "Dividend": 0.03, "Volatility": 0.10, "Drawdown": 0.10,
    "Beta": 0.07, "Liquidity": 0.05, "ESG": 0.05
}

# 리스크 점수 중심화용 스케일
scales = {
    "PE": 40, "PS": 10, "D/E": 200, "Margin": 0.5,
    "Volatility": 0.03, "Drawdown": 0.2, "Beta": 1.5,
    "Liquidity": 2000000, "ESG": 80
}

# √x 정규화
def normalize(x, key):
    if key == "Dividend":
        return 0 if x else 100
    raw = min(x / scales[key], 1)
    return (raw ** 0.5) * 100

# 설명
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

# 입력창 초기화
if "tickers" not in st.session_state:
    st.session_state.tickers = [{"name": "", "amount": ""}]

def add_row():
    st.session_state.tickers.append({"name": "", "amount": ""})

def remove_row(index):
    st.session_state.tickers.pop(index)

st.button("➕ Add Stock", on_click=add_row)

# 입력창 UI
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

# 기간 선택
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
    elif score <= 20: return "#3498db"
    elif score <= 33: return "#5dade2"
    elif score <= 45: return "#2ecc71"
    elif score <= 55: return "#f4d03f"
    elif score <= 67: return "#e67e22"
    elif score <= 80: return "#e74c3c"
    else: return "#000000"

# 리스크 계산
def calculate_components(ticker, period="1y"):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        spy = yf.Ticker("SPY").history(period=period)
        if hist.empty or spy.empty:
            return None, {}, {}

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

        raw_scores = {
            "PE": normalize(pe, "PE"),
            "PS": normalize(ps, "PS"),
            "D/E": normalize(dte, "D/E"),
            "Margin": normalize(1 - margin, "Margin"),
            "Dividend": normalize(dy, "Dividend"),
            "Volatility": normalize(np.std(returns), "Volatility"),
            "Drawdown": normalize((close / close.cummax() - 1).min(), "Drawdown"),
            "Beta": normalize(np.cov(returns, spy_returns)[0, 1] / np.cov(returns, spy_returns)[1, 1], "Beta"),
            "Liquidity": normalize(1000000 / avg_volume, "Liquidity"),
            "ESG": normalize(esg, "ESG")
        }

        weighted_scores = {k: raw_scores[k] * weights[k] for k in raw_scores}
        total_risk = round(sum(weighted_scores.values()), 2)

        return total_risk, weighted_scores, raw_scores
    except:
        return None, {}, {}

# 분석 실행
if st.button("📊 Analyze Risk"):
    if not portfolio:
        st.warning("⚠️ Please enter at least one stock.")
    else:
        risks = []
        total_amount = sum([amt for _, amt in portfolio])
        for ticker, amt in portfolio:
            r, _, _ = calculate_components(ticker, selected_period)
            if r is not None:
                risks.append((ticker, r, amt))

        if risks:
            total_score = round(sum(r * a for _, r, a in risks) / total_amount, 2)
            st.markdown(f"### 💡 Total Portfolio Risk: **{total_score}%** — {interpret_risk(total_score)}")
            st.markdown(f"<div style='background-color:{risk_color(total_score)}; height:20px'></div>", unsafe_allow_html=True)

        for ticker, risk, amt in risks:
            st.subheader(f" {ticker}")
            _, weighted, raw = calculate_components(ticker, selected_period)
            st.write(f"Risk: **{risk}%** — {interpret_risk(risk)}")

            top3 = sorted(weighted.items(), key=lambda x: x[1], reverse=True)[:3]
            labels = [x[0] for x in top3]
            values = [x[1] for x in top3]

            col1, col2 = st.columns(2)
            with col1:
                fig, ax = plt.subplots()
                ax.bar(labels, values)
                ax.set_title("Top 3 Risk Contributors")
                st.pyplot(fig)

            with col2:
                all_labels = list(raw.keys())
                raw_vals = [raw[k] for k in all_labels]
                angles = np.linspace(0, 2 * np.pi, len(all_labels), endpoint=False).tolist()
                raw_vals += raw_vals[:1]
                angles += angles[:1]
                fig, ax = plt.subplots(subplot_kw=dict(polar=True))
                ax.plot(angles, raw_vals, 'o-', linewidth=2)
                ax.fill(angles, raw_vals, alpha=0.25)
                ax.set_xticks(angles[:-1])
                ax.set_xticklabels(all_labels)
                st.pyplot(fig)

            st.markdown("### Risk Explanation")
            for k in labels:
                st.markdown(f"**{k}**: {explanations[k]}  \n🔗 [Search News](https://www.google.com/search?q={ticker}+{k}+stock+news)", unsafe_allow_html=True)
# 리스크 퍼센트 의미 설명
with st.expander(" What Does the Risk % Mean?"):
    st.markdown("""
    - **0–20%**: Extremely Low Risk — Blue-chip stability, minimal volatility  
    - **20–33%**: Very Low Risk — Conservative, low-debt companies  
    - **33–45%**: Low Risk — Financially sound with minor concerns  
    - **45–55%**: Moderate Risk — Balanced profile  
    - **55–67%**: High Risk — Growth-focused, some valuation stretch  
    - **67–80%**: Very High Risk — Speculative or structurally weak  
    - **80–100%**: Extremely High Risk — Red flags: overvalued, distressed, or hype-driven
    """)

# 리스크 산정 방식 안내 버튼
with st.expander("How Do We Calculate Risk?"):
    st.markdown("""
    ### Risk Score = Weighted Sum of 10 Factors:
    - **PE Ratio (18%)**: Higher → riskier
    - **PS Ratio (12%)**: Higher → riskier
    - **D/E Ratio (15%)**: Higher → riskier
    - **Operating Margin (15%)**: Lower → riskier
    - **Dividend Yield (3%)**: No dividend → riskier
    - **Volatility (10%)**: Higher std dev → riskier
    - **Drawdown (10%)**: Larger past loss → riskier
    - **Beta (7%)**: High market sensitivity
    - **Liquidity (5%)**: Lower avg volume → riskier
    - **ESG Score (5%)**: Higher ESG risk score → riskier

    ### 📌 Scores are normalized using √x scale for more balanced distribution (avg 40–60%).
    """)

# 데이터 한계 설명
with st.expander("🔎 Data Sources & Limitations"):
    st.markdown("""
    - Source: Yahoo Finance via yFinance
    - ESG data may be missing for some tickers
    - No qualitative factors (news sentiment, fraud, litigation)
    - Some microcaps or OTC stocks may lack complete data
    """)
