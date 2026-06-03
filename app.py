from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf


APP_TITLE = "WealthTrack: AI Portfolio Monitor"
DEFAULT_CSV = Path("Stock Portfolio - Sheet1.csv")


st.set_page_config(page_title=APP_TITLE, page_icon="📈", layout="wide")

st.markdown(
    """
    <style>
    :root {
        --panel: #171717;
        --line: #3a3a3a;
        --muted: #a9a9a9;
        --green: #5dd39e;
        --red: #ff7777;
    }
    .stApp { background: #0f0f10; color: #f3f3f3; }
    [data-testid="stSidebar"] { background: #151515; border-right: 1px solid var(--line); }
    h1, h2, h3 { letter-spacing: 0 !important; }
    .metric-strip {
        display: grid;
        grid-template-columns: repeat(3, minmax(160px, 1fr));
        gap: 14px;
        margin: 10px 0 24px;
    }
    .metric-box, .info-card, .news-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 14px 16px;
    }
    .metric-label { color: var(--muted); font-size: .82rem; text-transform: uppercase; }
    .metric-value { font-size: 1.28rem; font-weight: 750; margin-top: 3px; }
    .positive { color: var(--green); font-weight: 750; }
    .negative { color: var(--red); font-weight: 750; }
    .muted { color: var(--muted); }
    .section-title { font-size: 1.05rem; font-weight: 800; margin: 16px 0 10px; }
    .holdings-table-wrap {
        overflow-x: auto;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--panel);
    }
    .holdings-table {
        width: 100%;
        min-width: 980px;
        border-collapse: collapse;
    }
    .holdings-table th {
        background: #232323;
        color: #fff;
        font-size: .82rem;
        font-weight: 800;
        padding: 13px 16px;
        text-align: left;
        text-transform: uppercase;
        border-bottom: 1px solid var(--line);
    }
    .holdings-table td {
        padding: 14px 16px;
        border-bottom: 1px solid #2d2d2d;
        vertical-align: middle;
        color: #f3f3f3;
    }
    .holdings-table tr:last-child td { border-bottom: 0; }
    .symbol-cell { position: relative; width: 120px; }
    .symbol-link, .open-link {
        color: #7eb6ff !important;
        font-weight: 800;
        text-decoration: none;
    }
    .symbol-link:hover, .open-link:hover { text-decoration: underline; }
    .info-dot {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 18px;
        height: 18px;
        margin-left: 7px;
        border-radius: 50%;
        background: #2b5cff;
        color: #fff;
        font-size: 12px;
        font-weight: 800;
        cursor: default;
    }
    .hover-card {
        display: none;
        position: absolute;
        left: 14px;
        top: 42px;
        z-index: 20;
        width: 340px;
        padding: 14px;
        border: 1px solid #4a4a4a;
        border-radius: 8px;
        background: #101010;
        box-shadow: 0 18px 34px rgba(0,0,0,.48);
        white-space: normal;
    }
    .symbol-cell:hover .hover-card { display: block; }
    .sparkline { width: 100%; height: 76px; margin: 8px 0; }
    .stock-summary { color: var(--muted); font-size: .84rem; line-height: 1.35; }
    .qty-cell { text-align: right; }
    .news-card { margin-bottom: 12px; }
    .news-title { color: #7eb6ff !important; font-weight: 750; }
    .news-meta { color: var(--muted); font-size: .84rem; margin-top: 4px; }
    div[data-testid="stButton"] > button {
        background: #171717;
        color: #7eb6ff;
        border: 1px solid #333;
        border-radius: 6px;
        min-height: 34px;
        padding: 4px 10px;
        font-weight: 750;
    }
    div[data-testid="stButton"] > button:hover {
        background: #222;
        color: #a9cfff;
        border-color: #555;
    }
    div[data-testid="stButton"] > button:focus,
    div[data-testid="stButton"] > button:active {
        color: #a9cfff;
        border-color: #7eb6ff;
        box-shadow: none;
    }
    div[data-testid="stPopover"] button {
        background: #202020;
        color: #f3f3f3 !important;
        border: 1px solid #3a3a3a;
        border-radius: 999px;
        min-height: 30px;
        padding: 2px 10px;
    }
    div[data-testid="stPopover"] button:hover {
        background: #2a2a2a;
        border-color: #555;
    }
    div[data-testid="stPopover"] button *,
    div[data-testid="stPopover"] button p,
    div[data-testid="stPopover"] button svg {
        color: #f3f3f3 !important;
        fill: #f3f3f3 !important;
    }
    .native-table-head {
        display: grid;
        grid-template-columns: 1.2fr 2.2fr 1fr 1fr .7fr 1.1fr 1fr .8fr;
        gap: 12px;
        padding: 12px 14px;
        background: #232323;
        border: 1px solid var(--line);
        border-radius: 8px 8px 0 0;
        font-size: .82rem;
        font-weight: 800;
        text-transform: uppercase;
    }
    .native-row-rule {
        height: 1px;
        background: #2d2d2d;
        margin: 6px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"


def signed_money(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):,.2f}"


def pct(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:+.2f}%"


@st.cache_data(ttl=900, show_spinner=False)
def load_history(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    frame = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=False)
    if frame.empty:
        return pd.DataFrame()
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    frame = frame.reset_index()
    frame["Date"] = pd.to_datetime(frame["Date"])
    return frame


@st.cache_data(ttl=1800, show_spinner=False)
def load_profile(symbol: str) -> dict:
    try:
        info = yf.Ticker(symbol).get_info()
    except Exception:
        info = {}
    return {
        "name": info.get("longName") or info.get("shortName") or symbol,
        "sector": info.get("sector") or "Unknown",
        "industry": info.get("industry") or "Unknown",
        "summary": info.get("longBusinessSummary") or "No company summary available.",
    }


@st.cache_data(ttl=900, show_spinner=False)
def load_news(symbol: str) -> list[dict]:
    try:
        raw_items = yf.Ticker(symbol).news or []
    except Exception:
        raw_items = []

    items = []
    for raw in raw_items:
        content = raw.get("content", raw)
        provider = content.get("provider") or {}
        url = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
        title = content.get("title") or raw.get("title")
        link = url.get("url") if isinstance(url, dict) else raw.get("link")
        publisher = provider.get("displayName") if isinstance(provider, dict) else raw.get("publisher")
        published = content.get("pubDate") or raw.get("providerPublishTime")
        if title and link:
            items.append({"title": title, "link": link, "publisher": publisher or "Market news", "published": published})
    return items


def read_portfolio(uploaded_file) -> pd.DataFrame:
    source = uploaded_file if uploaded_file is not None else DEFAULT_CSV
    frame = pd.read_csv(source)
    frame.columns = [column.strip() for column in frame.columns]
    frame["Stock Symbol"] = frame["Stock Symbol"].astype(str).str.upper().str.strip()
    frame["Purchase Date"] = pd.to_datetime(frame["Purchase Date"], errors="coerce")
    frame["Quantity"] = pd.to_numeric(frame["Quantity"], errors="coerce").fillna(0)
    return frame.dropna(subset=["Stock Symbol", "Purchase Date"])


def price_on_or_after(history: pd.DataFrame, purchase_date: pd.Timestamp) -> float | None:
    if history.empty:
        return None
    rows = history[history["Date"].dt.date >= purchase_date.date()]
    if rows.empty:
        rows = history.tail(1)
    return float(rows.iloc[0]["Close"])


def trend_from_sma(history: pd.DataFrame) -> str:
    if len(history) < 9:
        return "N/A"
    closes = history["Close"].dropna()
    sma_9 = closes.rolling(9).mean().iloc[-1]
    latest = closes.iloc[-1]
    if pd.isna(sma_9):
        return "N/A"
    return "▲ Bullish" if latest >= sma_9 else "▼ Bearish"


def enrich_portfolio(frame: pd.DataFrame) -> pd.DataFrame:
    records = []
    for item in frame.to_dict("records"):
        symbol = item["Stock Symbol"]
        history = load_history(symbol, period="2y", interval="1d")
        profile = load_profile(symbol)
        latest_price = None if history.empty else float(history.iloc[-1]["Close"])
        purchase_price = item.get("Purchase price")
        if pd.isna(purchase_price) or purchase_price in ("", None):
            purchase_price = price_on_or_after(history, item["Purchase Date"])
        purchase_price = float(purchase_price) if purchase_price is not None and not pd.isna(purchase_price) else None
        quantity = float(item["Quantity"])
        profit = None if latest_price is None or purchase_price is None else (latest_price - purchase_price) * quantity
        cost_basis = None if purchase_price is None else purchase_price * quantity
        current_value = None if latest_price is None else latest_price * quantity
        records.append(
            {
                "symbol": symbol,
                "company": profile["name"],
                "sector": profile["sector"],
                "quantity": quantity,
                "current_price": latest_price,
                "purchase_price": purchase_price,
                "profit": profit,
                "profit_pct": None if profit is None or not cost_basis else profit / cost_basis * 100,
                "cost_basis": cost_basis,
                "current_value": current_value,
                "trend": trend_from_sma(history),
                "history": history,
                "profile": profile,
            }
        )
    return pd.DataFrame(records)


def render_metric_strip(portfolio: pd.DataFrame) -> None:
    total_value = portfolio["current_value"].fillna(0).sum()
    total_cost = portfolio["cost_basis"].fillna(0).sum()
    total_profit = portfolio["profit"].fillna(0).sum()
    total_profit_pct = 0 if total_cost == 0 else total_profit / total_cost * 100
    yesterday_value = 0.0
    current_value = 0.0
    for row in portfolio.to_dict("records"):
        history = row["history"]
        if len(history) >= 2:
            yesterday_value += float(history.iloc[-2]["Close"]) * row["quantity"]
            current_value += float(history.iloc[-1]["Close"]) * row["quantity"]
    day_change = current_value - yesterday_value
    st.markdown(
        f"""
        <div class="metric-strip">
          <div class="metric-box"><div class="metric-label">Total Value</div><div class="metric-value">{money(total_value)}</div></div>
          <div class="metric-box"><div class="metric-label">Total P&L</div><div class="metric-value {'positive' if total_profit >= 0 else 'negative'}">{signed_money(total_profit)} ({pct(total_profit_pct)})</div></div>
          <div class="metric-box"><div class="metric-label">24h Change</div><div class="metric-value {'positive' if day_change >= 0 else 'negative'}">{signed_money(day_change)}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def make_mini_chart(history: pd.DataFrame, symbol: str) -> go.Figure:
    fig = go.Figure()
    if not history.empty:
        recent = history.tail(45)
        fig.add_trace(go.Scatter(x=recent["Date"], y=recent["Close"], mode="lines", name=symbol))
    fig.update_layout(
        template="plotly_dark",
        height=170,
        margin=dict(l=5, r=5, t=5, b=5),
        showlegend=False,
        paper_bgcolor="#171717",
        plot_bgcolor="#171717",
        xaxis=dict(visible=False),
    )
    return fig


def sparkline_svg(history: pd.DataFrame) -> str:
    values = history.tail(35)["Close"].dropna().tolist()
    if len(values) < 2:
        return "<div class='stock-summary'>No chart data available.</div>"
    low = min(values)
    high = max(values)
    spread = high - low or 1
    points = []
    for index, value in enumerate(values):
        x = index * (320 / (len(values) - 1))
        y = 68 - ((value - low) / spread * 58)
        points.append(f"{x:.1f},{y:.1f}")
    color = "#5dd39e" if values[-1] >= values[0] else "#ff7777"
    return f"""
    <svg class="sparkline" viewBox="0 0 330 78" preserveAspectRatio="none" aria-hidden="true">
      <polyline fill="none" stroke="{color}" stroke-width="3" points="{' '.join(points)}" />
      <line x1="0" y1="72" x2="330" y2="72" stroke="#333" stroke-width="1" />
    </svg>
    """


def render_portfolio_table(portfolio: pd.DataFrame) -> None:
    st.markdown(
        """
        <div class="native-table-head">
          <div>Symbol</div><div>Company Name</div><div>Price</div><div>Avg Cost</div>
          <div>Qty</div><div>Total P&L</div><div>9-Day SMA</div><div>Act</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for row in portfolio.to_dict("records"):
        cols = st.columns([1.2, 2.2, 1, 1, 0.7, 1.1, 1, 0.8], vertical_alignment="center")
        profile = row["profile"]
        with cols[0]:
            if st.button(row["symbol"], key=f"symbol_{row['symbol']}", use_container_width=True):
                st.query_params["symbol"] = row["symbol"]
                st.rerun()
            with st.popover("Info", use_container_width=True):
                st.markdown(f"**{profile['name']}**")
                st.caption(f"{profile['sector']} | {profile['industry']}")
                st.plotly_chart(make_mini_chart(row["history"], row["symbol"]), use_container_width=True)
                st.write(profile["summary"][:360] + ("..." if len(profile["summary"]) > 360 else ""))
        cols[1].write(row["company"])
        cols[2].write(money(row["current_price"]))
        cols[3].write(money(row["purchase_price"]))
        cols[4].write(f"{row['quantity']:,.0f}")
        pnl_color = "green" if (row["profit"] or 0) >= 0 else "red"
        cols[5].markdown(f":{pnl_color}[**{signed_money(row['profit'])}**]")
        trend_color = "green" if "Bullish" in row["trend"] else "red"
        cols[6].markdown(f":{trend_color}[**{row['trend']}**]")
        with cols[7]:
            if st.button("Open", key=f"open_{row['symbol']}", use_container_width=True):
                st.query_params["symbol"] = row["symbol"]
                st.rerun()
        st.markdown('<div class="native-row-rule"></div>', unsafe_allow_html=True)


def make_chart(history: pd.DataFrame, symbol: str, chart_kind: str) -> go.Figure:
    fig = go.Figure()
    if history.empty:
        return fig
    if chart_kind == "Candlestick":
        fig.add_trace(
            go.Candlestick(
                x=history["Date"],
                open=history["Open"],
                high=history["High"],
                low=history["Low"],
                close=history["Close"],
                name=symbol,
            )
        )
    else:
        fig.add_trace(go.Scatter(x=history["Date"], y=history["Close"], mode="lines", name=symbol))
    fig.add_trace(
        go.Scatter(
            x=history["Date"],
            y=history["Close"].rolling(9).mean(),
            mode="lines",
            name="9-day SMA",
            line=dict(color="#f2c94c", width=2),
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=560,
        margin=dict(l=10, r=10, t=35, b=10),
        title=f"{symbol} Price Action",
        xaxis_rangeslider_visible=False,
        paper_bgcolor="#171717",
        plot_bgcolor="#171717",
    )
    return fig


def render_landing(portfolio: pd.DataFrame) -> None:
    st.title(f"🚀 {APP_TITLE}")
    render_metric_strip(portfolio)

    with st.sidebar:
        st.header("📁 Upload/Refresh CSV")
        st.caption("Using uploaded CSV or the local Stock Portfolio sheet.")
        sectors = ["All"] + sorted(portfolio["sector"].dropna().unique().tolist())
        selected_sector = st.selectbox("Sector", sectors, index=0, key="sector_filter")
        selected_trend = st.selectbox("Trend", ["All", "Bullish", "Bearish"], index=0, key="trend_filter")

    filtered = portfolio.copy()
    if selected_sector != "All":
        filtered = filtered[filtered["sector"] == selected_sector]
    if selected_trend != "All":
        filtered = filtered[filtered["trend"].str.contains(selected_trend, na=False)]

    st.markdown('<div class="section-title">📌 Holdings Overview</div>', unsafe_allow_html=True)
    if filtered.empty:
        st.warning("No holdings match the selected filters.")
    else:
        render_portfolio_table(filtered)


def news_time(item: dict) -> str:
    published = item.get("published")
    if not published:
        return ""
    try:
        if isinstance(published, int):
            then = datetime.fromtimestamp(published)
        else:
            then = datetime.fromisoformat(str(published).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return ""
    hours = max(1, int((datetime.now() - then).total_seconds() // 3600))
    return f"{hours}h ago" if hours < 48 else then.strftime("%b %d, %Y")


def render_news(symbol: str) -> None:
    st.markdown('<div class="section-title">📰 Latest News & Market Sentiment</div>', unsafe_allow_html=True)
    news = load_news(symbol)
    if not news:
        st.info("No recent yfinance news available for this stock.")
        return
    for item in news[:8]:
        st.markdown(
            f"""
            <div class="news-card">
              <a class="news-title" href="{item['link']}" target="_blank">{item['title']}</a>
              <div class="news-meta">{item['publisher']} · {news_time(item)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_detail(portfolio: pd.DataFrame, symbol: str) -> None:
    row = portfolio[portfolio["symbol"] == symbol]
    if row.empty:
        st.error(f"{symbol} is not in the current portfolio.")
        if st.button("Back to Dashboard"):
            st.query_params.clear()
            st.rerun()
        return
    data = row.iloc[0].to_dict()
    if st.button("⬅ Back to Dashboard"):
        st.query_params.clear()
        st.rerun()
    st.title(f"📈 Detail Analysis: {symbol}")
    st.caption(data["company"])

    left, right = st.columns([1.12, 1], gap="large")
    with left:
        st.markdown('<div class="section-title">Technical Analytics</div>', unsafe_allow_html=True)
        ranges = {
            "Week": ("5d", "1d"),
            "Month": ("1mo", "1d"),
            "Daily chart": ("6mo", "1d"),
            "Weekly chart": ("1y", "1wk"),
            "Monthly chart": ("5y", "1mo"),
            "For one year": ("1y", "1d"),
        }
        selected = st.radio(
            "Chart range",
            list(ranges.keys()),
            index=list(ranges.keys()).index("For one year"),
            horizontal=True,
            label_visibility="collapsed",
        )
        chart_kind = st.radio("Chart type", ["Candlestick", "Line"], horizontal=True)
        period, interval = ranges[selected]
        chart_history = load_history(symbol, period=period, interval=interval)
        st.plotly_chart(make_chart(chart_history, symbol, chart_kind), use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Current Price", money(data["current_price"]))
        c2.metric("Purchase Price", money(data["purchase_price"]))
        c3.metric("Total P&L", signed_money(data["profit"]), pct(data["profit_pct"]))

        st.markdown(
            f"""
            <div class="info-card">
              <strong>{data['company']}</strong><br>
              <span class="muted">{data['profile']['sector']} | {data['profile']['industry']}</span><br><br>
              {data['profile']['summary']}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        render_news(symbol)


def main() -> None:
    with st.sidebar:
        uploaded_file = st.file_uploader("Choose File", type=["csv"])
        if st.button("Refresh market data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    try:
        portfolio = enrich_portfolio(read_portfolio(uploaded_file))
    except Exception as exc:
        st.error(f"Could not load the portfolio: {exc}")
        st.stop()

    symbol = st.query_params.get("symbol")
    if symbol:
        render_detail(portfolio, symbol.upper())
    else:
        render_landing(portfolio)


if __name__ == "__main__":
    main()
