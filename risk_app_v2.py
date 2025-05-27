import streamlit as st
import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Portfolio Risk Analyzer", layout="centered")
st.title("Portfolio Risk Analyzer")

# ✅ 가중치와 스케일
weights = {
    "PE": 0.18, "PS": 0.12, "D/E": 0.15, "Margin": 0.15,
    "Dividend": 0.03, "Volatility": 0.10, "Drawdown": 0.10,
    "Beta": 0.07, "Liquidity": 0.05, "ESG": 0.05
}

scales = {
    "PE": 60, "PS": 15, "D/E": 300, "Margin": 1.0,
    "Volatility": 0.05, "Drawdown": 0.3, "Beta": 2.0,
    "Liquidity": 1_000_000, "ESG": 100
}

def normalize(x, key):
    if key == "Dividend":
        return 0 if x else 100
    return min(x / scales[key], 1) * 100

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

# ✅ 종목 입력 처리
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

# ✅ 투자 기간 선택
selected_period = st.selectbox("Select Investment Period", ["1mo", "3mo", "6mo", "1y", "2y"], index=2)

# ✅ 리스크 해석과 색상
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

# ✅ 리스크 계산 함수
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
        avg_volume = volume or 1_000_000
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
            "Liquidity": normalize(1_000_000 / avg_volume, "Liquidity"),
            "ESG": normalize(esg, "ESG")
        }

        weighted_scores = {k: raw_scores[k] * weights[k] for k in raw_scores}
        total_risk = round(sum(weighted_scores.values()), 2)

        return total_risk, weighted_scores, raw_scores
    except:
        return None, {}, {}

# ✅ 분석 버튼
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
            st.markdown(f"## 💡 Total Portfolio Risk: **{portfolio_risk}%** — {interpret_risk(portfolio_risk)}")
            st.markdown(f"<div style='background-color:{risk_color(portfolio_risk)}; height:20px'></div>", unsafe_allow_html=True)

        for ticker, risk, amt in risks:
            st.subheader(f"📍 {ticker}")
            total, weighted, raw = calculate_components(ticker, selected_period)
            st.markdown(f"Risk: **{total}%** — {interpret_risk(total)}")
            st.markdown(f"<div style='background-color:{risk_color(total)}; height:15px'></div>", unsafe_allow_html=True)

            # 막대 그래프
            top3 = sorted(weighted.items(), key=lambda x: x[1], reverse=True)[:3]
            labels = [x[0] for x in top3]
            values = [x[1] for x in top3]
            fig, ax = plt.subplots()
            ax.bar(labels, values)
            st.pyplot(fig)

            # 레이더 차트
            raw_vals = [raw[k] for k in raw]
            angles = np.linspace(0, 2 * np.pi, len(raw), endpoint=False).tolist()
            raw_vals += raw_vals[:1]
            angles += angles[:1]
            fig2, ax2 = plt.subplots(subplot_kw=dict(polar=True))
            ax2.plot(angles, raw_vals, 'o-', linewidth=2)
            ax2.fill(angles, raw_vals, alpha=0.25)
            ax2.set_xticks(angles[:-1])
            ax2.set_xticklabels(list(raw.keys()))
            st.pyplot(fig2)

            # 설명
            st.markdown("### Explanation of Top Risk Factors")
            for k in labels:
                st.markdown(f"- **{k}**: {explanations[k]}")

# ✅ 리스크 의미 설명
with st.expander("Risk % ?"):
    st.markdown("""
- **0–20%**: Extremely Low Risk - stable, minimal volatility  
- **20–33%**: Very Low Risk - Conservative, low-debt companies  
- **33–45%**: Low Risk - Financially sound with minor concerns  
- **45–55%**: Moderate Risk - Balanced profile- risk & profit
- **55–67%**: High Risk - Growth-focused, some valuation stretch  
- **67–80%**: Very High Risk - Speculative or structurally weak  
- **80–100%**: Extremely High Risk - Red flags: overvalued, distressed  
""")

# ✅ 계산 방식 설명
with st.expander("How Do We Calculate Risk?"):
    st.markdown("""
- Risk is calculated from 10 indicators using weighted normalization.
- Each score is scaled relative to financial norms (e.g., PE 60, D/E 300).
- Final portfolio risk = weighted average based on input dollar amount.
""")
