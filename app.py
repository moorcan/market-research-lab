import json
from dataclasses import asdict
from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
from market_lab.data import AlpacaDaily, Store, UNIVERSE, require_adjusted_provenance
from market_lab.strategies import Strategy
from market_lab.backtest import run, metrics, trade_statistics, Costs
from market_lab.experiments import record
from market_lab.providers.routing import ResearchDataService
from market_lab.providers.robinhood import RobinhoodDaily

st.set_page_config(page_title="Market Research Lab", layout="wide")
st.title("Market Research Lab")
st.warning("Research and fictional paper simulation only. No brokerage connection or real orders. Starting fictional cash: $2,700.")
st.info("Adjusted-price exploratory backtests only. Realistic executable-price simulations are not implemented.")
st.caption("Exploratory historical results are not predictions. This MVP does not qualify strategies for forward paper trading.")
store = Store()
section = st.sidebar.radio("Workspace", ["Overview", "Strategy Lab", "Risk Center", "Paper Portfolio", "Research Journal", "Probability Lab", "Event Intelligence"])
if section == "Overview":
    st.subheader("Read-only market data")
    st.write("Alpaca IEX daily adjusted research bars; no synthetic fallback. Provider keys are read from environment variables.")
    st.info("Robinhood official Trading MCP is being evaluated as a primary research-data candidate. It remains disabled pending verified official documentation, data-only authorization, tool schemas and provider comparison. Alpaca remains available.")
    with st.form("fetch"):
        provider = st.selectbox("Data provider", ["alpaca", "robinhood_mcp"])
        fallback = st.checkbox("Explicitly permit Alpaca fallback if the selected provider is unavailable", value=False)
        symbol = st.selectbox("ETF research universe", UNIVERSE)
        start = st.date_input("First session range", date(2020,1,1))
        end = st.date_input("Last session range (completed days only)", date.today()-timedelta(days=1))
        submit = st.form_submit_button("Retrieve and cache genuine data")
    if submit:
        try:
            if start > end or end >= date.today():
                raise ValueError("Choose a past, ordered range")
            service = ResearchDataService({"alpaca": AlpacaDaily(), "robinhood_mcp": RobinhoodDaily()})
            result = service.fetch(provider, symbol, start.isoformat(), end.isoformat(), fallback="alpaca" if fallback and provider != "alpaca" else None)
            bars, meta = result.bars, result.provenance
            st.write("Selected provider:", result.selected_provider, "Fallback used:", result.used_fallback)
            version = store.save(symbol,bars,meta)
            st.success(f"Validated and cached {len(bars)} sessions: {version}")
        except Exception as exc:
            st.error(f"Retrieval failed ({type(exc).__name__}). Check keys, date range, provider access and session completeness. No data was substituted.")
    st.dataframe(store.versions(), hide_index=True)
elif section in ["Strategy Lab", "Risk Center", "Paper Portfolio"]:
    versions = store.versions()
    if versions.empty:
        st.info("No real data cached. Retrieve market data in Overview. Fixtures are used only by automated tests.")
    else:
        version = st.selectbox("Immutable dataset version", versions.version)
        bars, meta = store.load(version)
        st.json(asdict(meta))
        if meta.fixture:
            st.error("SYNTHETIC TEST FIXTURE — development output only, not market research.")
        try:
            require_adjusted_provenance(meta)
        except ValueError as exc:
            st.error(str(exc))
            st.stop()
        name = st.selectbox("Strategy", ["trend", "mean_reversion"])
        window = st.number_input("Trailing sessions",2,252,50)
        threshold = st.slider("Mean-reversion entry deviation",0.01,0.20,0.03)
        fee = st.number_input("Fee per side (bps)",0.0,1000.0,1.0)
        spread = st.number_input("Full spread (bps)",0.0,1000.0,5.0)
        slip = st.number_input("Slippage per side (bps)",0.0,1000.0,5.0)
        initial = st.number_input("Fictional starting cash",100.0,1000000.0,2700.0)
        if st.button("Run reproducible historical simulation"):
            strategy = Strategy(name,int(window),threshold)
            costs = Costs(fee,spread,slip)
            result = run(bars,strategy.signals(bars),initial,costs)
            benchmark = run(bars,pd.Series(1.0,index=bars.index),initial,costs)
            stress = run(bars,strategy.signals(bars),initial,Costs(fee*2,spread*3,slip*3))
            if len(bars) < 2:
                st.warning("Fewer than two sessions: annualized and distributional risk metrics are unavailable. No inference is supported.")
            elif len(bars) < 252:
                st.warning("Fewer than 252 sessions: risk and annualized statistics are especially unstable. This is exploratory output only.")
            st.caption("Adjusted research units; next-session open execution proxy, 95% allocation, 1% volume cap; idle cash earns zero. Benchmark uses identical constraints and costs.")
            curves = pd.DataFrame({"strategy":result.equity,"passive benchmark":benchmark.equity,"cash":initial,"higher cost stress":stress.equity})
            st.plotly_chart(px.line(curves, labels={"value":"Fictional equity ($)","index":"Session"}),use_container_width=True)
            st.dataframe(pd.DataFrame({"strategy":metrics(result),"passive":metrics(benchmark),"stress":metrics(stress)}))
            st.plotly_chart(px.area(result.equity/result.equity.cummax().clip(lower=initial)-1, labels={"value":"Drawdown"}),use_container_width=True)
            st.write("Ending fictional cash",float(result.cash.iloc[-1]),"Ending research units",float(result.shares.iloc[-1]))
            st.json(trade_statistics(result))
            if result.equity.iloc[-1] <= max(benchmark.equity.iloc[-1], initial):
                st.info("This exploratory run did not beat both the passive benchmark and cash after modeled costs.")
            st.dataframe(result.journal)
            st.download_button("Download hypothetical trade journal",result.journal.to_csv(index=False),"trades.csv")
            identifier = record("reports",version,meta,strategy,costs,result)
            st.success(f"Saved exploratory experiment {identifier}")
elif section == "Research Journal":
    from pathlib import Path
    files = sorted(Path("reports").glob("*.json"),reverse=True) if Path("reports").exists() else []
    st.write("Experiments retain data version, parameters, costs, evaluation status and historical outputs locally.")
    for path in files:
        with st.expander(path.stem): st.json(json.loads(path.read_text()))
elif section == "Probability Lab":
    st.info("Not implemented. No probabilities are produced. Holdout design, walk-forward validation and calibration are required in Milestone 2.")
else:
    st.info("Timestamp-safe event contracts and tests are implemented. SEC Form 4 monitoring, insider alerts, historical political events and news analysis are scheduled for Milestone 3 and remain unimplemented.")
    st.write("Use first-publication and ingestion timestamps, not underlying transaction dates. SEC code P alone does not prove discretionary buying or exclude an automatic plan.")
    st.write("Initial case: November 3, 2026 U.S. midterm election. No outcomes, market expectations or returns are seeded without verifiable public sources.")
