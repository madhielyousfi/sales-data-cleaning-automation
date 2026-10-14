"""Modern Streamlit UI for the Sales Data Cleaning & Automation pipeline."""

from __future__ import annotations

import html
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st

from src.cleaning import clean_data
from src.generate_data import generate_sales_data
from src.profiling import profile_dataframe
from src.reporting import generate_quality_report, generate_summary_metrics
from src.validation import run_analytics, run_quality_checks

EXPECTED_COLS = [
    "row_id", "order_id", "order_date", "customer_id", "customer_name",
    "customer_email", "product_id", "product_name", "category",
    "quantity", "unit_price", "discount", "payment_method",
    "country", "order_status",
]
STEPS = ["Upload", "Profile", "Quarantine", "Validate", "Export"]


def _inject_css() -> None:
    css_path = Path(__file__).parent / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def _to_excel_bytes(df: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    df.to_excel(buffer, index=False)
    return buffer.getvalue()


def _load_uploaded(uploaded: Any) -> pd.DataFrame:
    if uploaded.name.endswith(".csv"):
        return pd.read_csv(uploaded, dtype=str)
    return pd.read_excel(uploaded, dtype=str)


def _load_sample() -> pd.DataFrame:
    sample = Path("data/raw/raw_sales.csv")
    if not sample.exists():
        msg = "Run `python -m src.cli generate` first to create sample data."
        raise FileNotFoundError(msg)
    return pd.read_csv(sample, dtype=str)


def _hero(active: int = 5) -> None:
    steps = "".join(
        f"<span class='step{' active' if i < active else ''}'>"
        f"<span class='dot'></span>{s}</span>"
        for i, s in enumerate(STEPS)
    )
    st.markdown(
        "<div class='hero'>"
        "<span class='badge'>Pandas · DuckDB · Audited pipeline</span>"
        "<h1>Sales Data Cleaning &amp; Automation</h1>"
        "<p>Upload a messy export, profile defects, quarantine bad rows "
        "with reasons, validate with independent SQL checks, and ship "
        "analytics-ready outputs.</p>"
        f"<div class='stepper'>{steps}</div></div>",
        unsafe_allow_html=True,
    )


def _kpis(total: int, n_clean: int, n_q: int, revenue: float, src: str) -> None:
    keep = n_clean / total * 100 if total else 0
    flagged = n_q / total * 100 if total else 0
    st.markdown(
        "<div class='kpis'>"
        f"<div class='kpi accent'><div class='label'>Raw rows</div>"
        f"<div class='value'>{total:,}</div>"
        f"<div class='delta info'>{html.escape(src[:42])}</div></div>"
        f"<div class='kpi accent'><div class='label'>Cleaned</div>"
        f"<div class='value'>{n_clean:,}</div>"
        f"<div class='delta up'>{keep:.1f}% kept</div></div>"
        f"<div class='kpi accent'><div class='label'>Quarantined</div>"
        f"<div class='value'>{n_q:,}</div>"
        f"<div class='delta warn'>{flagged:.1f}% flagged</div></div>"
        f"<div class='kpi accent'><div class='label'>Realized revenue</div>"
        f"<div class='value'>${revenue:,.0f}</div>"
        "<div class='delta info'>refunds excluded</div></div>"
        "</div>",
        unsafe_allow_html=True,
    )


def _quality_with_status(
    cleaned: pd.DataFrame,
) -> tuple[pd.DataFrame, list[pd.DataFrame]]:
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        cleaned.to_csv(tmp.name, index=False)
        quality_df = run_quality_checks(Path(tmp.name))
        analytics = run_analytics(Path(tmp.name))
    quality_df = quality_df.copy()
    quality_df["status"] = quality_df["issue_count"].apply(
        lambda n: "Pass" if int(n) == 0 else "Review"
    )
    return quality_df, analytics


def _quarantine_breakdown(quarantined: pd.DataFrame) -> pd.DataFrame:
    if quarantined.empty or "quarantine_reason" not in quarantined.columns:
        return pd.DataFrame(columns=["reason", "count"])
    exploded = (
        quarantined["quarantine_reason"].astype(str).str.split(";").explode().str.strip()
    )
    exploded = exploded[exploded.ne("") & exploded.ne("nan")]
    return exploded.value_counts().rename_axis("reason").reset_index(name="count")


def _sidebar() -> tuple[Any, bool, int, bool, tuple[int, int] | None]:
    st.sidebar.title("Sales Cleaner")
    st.sidebar.caption("Raw → Clean → Validate → Report")
    uploaded = st.sidebar.file_uploader(
        "Upload raw sales file",
        type=["csv", "xlsx"],
        help="CSV or single-sheet Excel with the sales columns.",
    )
    use_sample = st.sidebar.button("Use sample dataset", use_container_width=True)
    st.sidebar.divider()
    st.sidebar.markdown("**Synthetic data**")
    gen_rows = st.sidebar.number_input("Rows", 100, 20000, 2000, step=100)
    gen_seed = st.sidebar.number_input("Seed", 0, 999999, 42)
    generate = st.sidebar.button("Generate", use_container_width=True)
    st.sidebar.divider()
    preview_n = st.sidebar.slider("Preview rows", 5, 50, 20)
    show_emails = st.sidebar.toggle("Show customer emails", value=True)
    with st.sidebar.expander("Cleaning rules"):
        st.markdown(
            "- Dates valid from 2010-01-01 to today.\n"
            "- Quantity and unit price must be above 0.\n"
            "- Discount coerced to the 0.0–0.80 range.\n"
            "- Duplicate order keys are kept once.\n"
            "- Missing IDs are quarantined, never dropped.\n"
            "- Canceled/refunded orders skip revenue.\n"
            "- Total = qty * price * (1 - discount)."
        )
    st.sidebar.caption("Pandas clean → quarantine → DuckDB checks.")
    gen_request = (int(gen_rows), int(gen_seed)) if generate else None
    return uploaded, use_sample, preview_n, show_emails, gen_request


def _empty_state() -> None:
    _hero(active=1)
    st.info("Upload a file or use the sample dataset to start the pipeline.")
    c1, c2, c3 = st.columns(3)
    for col, title, body in [
        (c1, "1 · Upload", "CSV or single-sheet Excel. Originals are never modified."),
        (c2, "2 · Quarantine", "Bad rows kept aside with an explicit reason code."),
        (c3, "3 · Validate", "DuckDB re-checks dates, quantities, prices, emails."),
    ]:
        with col, st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(body)
    with st.expander("Expected columns"):
        st.code(", ".join(EXPECTED_COLS))
        st.caption("Missing IDs, bad dates and non-positive amounts are quarantined.")


def _themed_bar(data: pd.DataFrame, x: str, y: str, y_title: str) -> Any:
    """Indigo bar chart with angled labels that never clip."""
    return (
        alt.Chart(data)
        .mark_bar(color="#4F46E5", cornerRadiusTopLeft=6, cornerRadiusTopRight=6)
        .encode(
            x=alt.X(f"{x}:N", sort="-y", axis=alt.Axis(labelAngle=-30, title=None)),
            y=alt.Y(f"{y}:Q", title=y_title),
            tooltip=[x, y],
        )
        .properties(height=250)
    )


def _themed_line(data: pd.DataFrame, x: str, y: str) -> Any:
    """Indigo trend line with points and tooltips."""
    return (
        alt.Chart(data)
        .mark_line(color="#4F46E5", strokeWidth=2.5, point=True)
        .encode(
            x=alt.X(f"{x}:T", title=None),
            y=alt.Y(f"{y}:Q", title="revenue"),
            tooltip=[x, y],
        )
        .properties(height=260)
    )


def _stat_cards(stats: list[tuple[str, str]]) -> None:
    """Render small themed stat cards (label + value pairs)."""
    cards = "".join(
        f"<div class='stat'><div class='label'>{label}</div>"
        f"<div class='value'>{value}</div></div>"
        for label, value in stats
    )
    st.markdown(f"<div class='stats'>{cards}</div>", unsafe_allow_html=True)


def _tab_profile(raw_df: pd.DataFrame, preview_n: int) -> None:
    with st.container(border=True):
        st.markdown("**Raw preview**")
        st.caption(f"{len(raw_df):,} rows × {len(raw_df.columns)} columns")
        st.dataframe(
            raw_df.head(preview_n),
            use_container_width=True,
            hide_index=True,
            height=min(120 + preview_n * 35, 700),
        )
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        st.markdown("**Profile snapshot**")
        profile = profile_dataframe(raw_df)
        _stat_cards(
            [
                ("Columns", str(profile["total_columns"])),
                ("Dup keys", str(profile["duplicate_business_keys"])),
                ("Memory MB", str(profile["memory_mb"])),
            ]
        )
        st.caption("Duplicate key = order_id + product_id + order_date.")
    with c2, st.container(border=True):
        st.markdown("**Columns with nulls**")
        nulls = pd.Series(profile["null_counts"]).sort_values(ascending=False)
        nulls = nulls[nulls > 0]
        if not nulls.empty:
            missing = nulls.head(10).rename_axis("column").reset_index(name="rows")
            st.altair_chart(
                _themed_bar(missing, "column", "rows", "missing values"),
                use_container_width=True,
            )
        else:
            st.success("No nulls detected.")


def _tab_review(
    quarantined: pd.DataFrame, display_cleaned: pd.DataFrame, preview_n: int
) -> None:
    breakdown = _quarantine_breakdown(quarantined)
    with st.container(border=True):
        st.markdown("**Quarantine reasons**")
        c1, c2 = st.columns([1, 2])
        with c1:
            if breakdown.empty:
                st.success("Nothing quarantined.")
            else:
                st.dataframe(breakdown, use_container_width=True, hide_index=True)
        with c2:
            if not breakdown.empty:
                st.altair_chart(
                    _themed_bar(breakdown, "reason", "count", "rows"),
                    use_container_width=True,
                )

    with st.container(border=True):
        st.markdown("**Quarantine explorer**")
        if quarantined.empty:
            st.success("No quarantined rows.")
        else:
            reasons = sorted(breakdown["reason"].tolist()) if not breakdown.empty else []
            selected = st.multiselect("Filter by reason", reasons, default=reasons)
            query = st.text_input("Search order, customer or product", "")
            view = quarantined.copy()
            if selected:
                mask = view["quarantine_reason"].astype(str).apply(
                    lambda s: any(r in s for r in selected)
                )
                view = view[mask]
            if query:
                q = query.lower()
                str_cols = view.select_dtypes(include="object").columns
                contains = view[str_cols].apply(
                    lambda r: r.str.lower().str.contains(q, na=False)
                )
                view = view[contains.any(axis=1)]
            st.caption(f"{len(view):,} of {len(quarantined):,} rows shown")
            st.dataframe(view.head(preview_n * 5), use_container_width=True)

    with st.container(border=True):
        st.markdown("**Cleaned preview**")
        st.dataframe(display_cleaned.head(preview_n), use_container_width=True)


def _tab_quality(cleaned: pd.DataFrame) -> None:
    with st.container(border=True):
        st.markdown("**Independent DuckDB checks**")
        with st.spinner("Running SQL checks…"):
            quality_df, analytics = _quality_with_status(cleaned)
        st.session_state["analytics_n"] = len(analytics)
        passed = int((quality_df["issue_count"].astype(int) == 0).sum())
        pills = "".join(
            f"<span class='pill {'pass' if int(r['issue_count']) == 0 else 'review'}'>"
            f"{r['check_name']}: {r['issue_count']}</span>"
            for _, r in quality_df.iterrows()
        )
        st.markdown(f"<div class='pills'>{pills}</div>", unsafe_allow_html=True)
        st.dataframe(quality_df, use_container_width=True, hide_index=True)
        if passed == len(quality_df):
            st.success("All hard checks pass.")
        else:
            st.warning(f"{len(quality_df) - passed} check(s) need review.")


def _tab_insights(cleaned: pd.DataFrame) -> None:
    with st.container(border=True):
        st.markdown("**Business insights · realized revenue only**")
        try:
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                cleaned.to_csv(tmp.name, index=False)
                analytics = run_analytics(Path(tmp.name))
            monthly = analytics[2]
            by_cat = analytics[3]
            by_country = analytics[4]
            top_products = analytics[5]
            m1, m2 = st.columns(2)
            with m1:
                st.caption("Monthly revenue trend")
                ts = monthly.copy()
                ts["month"] = pd.to_datetime(ts["month"])
                st.altair_chart(
                    _themed_line(ts, "month", "revenue"), use_container_width=True
                )
            with m2:
                st.caption("Revenue by category")
                st.altair_chart(
                    _themed_bar(by_cat, "category", "revenue", "revenue"),
                    use_container_width=True,
                )
            i1, i2 = st.columns(2)
            with i1:
                st.caption("Top countries")
                st.dataframe(by_country.head(10), use_container_width=True)
            with i2:
                st.caption("Top products by quantity")
                st.dataframe(top_products.head(10), use_container_width=True)
        except Exception as exc:
            st.error(f"Could not compute insights: {exc}")


def _tab_export(cleaned: pd.DataFrame, quarantined: pd.DataFrame) -> None:
    with st.container(border=True):
        st.markdown("**Downloads**")
        d1, d2, d3 = st.columns(3)
        d1.download_button(
            "Cleaned CSV",
            cleaned.to_csv(index=False).encode(),
            "cleaned_sales.csv",
            "text/csv",
            use_container_width=True,
        )
        d2.download_button(
            "Quarantined CSV",
            quarantined.to_csv(index=False).encode(),
            "quarantined_sales.csv",
            "text/csv",
            use_container_width=True,
        )
        d3.download_button(
            "Cleaned Excel",
            _to_excel_bytes(cleaned),
            "cleaned_sales.xlsx",
            use_container_width=True,
        )
        e1, e2 = st.columns(2)
        with e1:
            quality_csv = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                    cleaned.to_csv(tmp.name, index=False)
                    qc = run_quality_checks(Path(tmp.name)).to_csv(index=False)
                    quality_csv = qc.encode()
            except Exception:
                quality_csv = None
            if quality_csv:
                st.download_button(
                    "Quality checks CSV",
                    quality_csv,
                    "quality_checks.csv",
                    "text/csv",
                    use_container_width=True,
                )
        with e2:
            st.download_button(
                "Quarantined Excel",
                _to_excel_bytes(quarantined),
                "quarantined_sales.xlsx",
                use_container_width=True,
            )
        st.markdown("**Stakeholder reports**")
        r1, r2, r3 = st.columns(3)
        try:
            with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
                cleaned.to_csv(tmp.name, index=False)
                tmp_path = Path(tmp.name)
                quality_df = run_quality_checks(tmp_path)
                analytics = run_analytics(tmp_path)
            with tempfile.TemporaryDirectory() as td:
                md_path = Path(td) / "data_quality_report.md"
                json_path = Path(td) / "data_quality_report.json"
                csv_path = Path(td) / "summary_metrics.csv"
                generate_quality_report(quality_df, md_path, json_path)
                generate_summary_metrics(analytics, csv_path)
                md_bytes = md_path.read_bytes()
                json_bytes = json_path.read_bytes()
                summary_bytes = csv_path.read_bytes()
            r1.download_button(
                "Quality report (MD)",
                md_bytes,
                "data_quality_report.md",
                "text/markdown",
                use_container_width=True,
            )
            r2.download_button(
                "Quality report (JSON)",
                json_bytes,
                "data_quality_report.json",
                "application/json",
                use_container_width=True,
            )
            r3.download_button(
                "Summary metrics (CSV)",
                summary_bytes,
                "summary_metrics.csv",
                "text/csv",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Could not build reports: {exc}")
        st.caption("Quarantine rows carry a reason. Cleaned rows add totals + revenue flag.")


def main() -> None:
    """Render the Streamlit app."""
    st.set_page_config(
        page_title="Sales Data Cleaner",
        page_icon="◈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    _inject_css()

    uploaded, use_sample, preview_n, show_emails, gen_request = _sidebar()

    raw_df: pd.DataFrame | None = None
    source_label = ""
    if uploaded is not None:
        try:
            raw_df = _load_uploaded(uploaded)
            source_label = uploaded.name
            st.session_state["use_sample"] = False
        except Exception as exc:
            _hero(active=1)
            st.error(f"Could not read file: {exc}")
            return
    elif gen_request is not None:
        rows, seed = gen_request
        with st.spinner("Generating synthetic data…"):
            raw_df = generate_sales_data(rows=rows, seed=seed)
        source_label = f"synthetic · {rows} rows · seed {seed}"
        st.session_state["generated_df"] = raw_df
        st.session_state["generated_label"] = source_label
        st.session_state["use_sample"] = False
    elif "generated_df" in st.session_state:
        raw_df = st.session_state["generated_df"]
        source_label = str(st.session_state["generated_label"])
    elif use_sample or st.session_state.get("use_sample"):
        try:
            raw_df = _load_sample()
            source_label = "sample · raw_sales.csv"
            st.session_state["use_sample"] = True
            st.session_state.pop("generated_df", None)
            st.session_state.pop("generated_label", None)
        except FileNotFoundError as exc:
            _hero(active=1)
            st.error(str(exc))
            return

    if raw_df is None:
        _empty_state()
        return

    _hero(active=5)

    missing = [c for c in EXPECTED_COLS if c not in raw_df.columns]
    if missing:
        st.warning(f"Missing columns: {', '.join(missing)}. More rows may be quarantined.")

    if (
        "cleaned" not in st.session_state
        or st.session_state.get("source_label") != source_label
        or st.session_state.get("raw_shape") != raw_df.shape
    ):
        with st.spinner("Cleaning data…"):
            cleaned, quarantined, _log = clean_data(raw_df)
        st.session_state.update(
            {
                "cleaned": cleaned,
                "quarantined": quarantined,
                "source_label": source_label,
                "raw_shape": raw_df.shape,
            }
        )
    cleaned = st.session_state["cleaned"]
    quarantined = st.session_state["quarantined"]

    revenue = 0.0
    if "total_amount" in cleaned.columns and "is_revenue_realized" in cleaned.columns:
        realized = cleaned[cleaned["is_revenue_realized"].astype(str) == "True"]
        revenue = float(pd.to_numeric(realized["total_amount"], errors="coerce").sum())
    _kpis(len(raw_df), len(cleaned), len(quarantined), revenue, source_label)

    if show_emails:
        display_cleaned = cleaned
    else:
        display_cleaned = cleaned.drop(columns=["customer_email"], errors="ignore")

    tabs = ["Profile", "Review", "Validation", "Insights", "Export"]
    tab_raw, tab_clean, tab_quality, tab_insights, tab_export = st.tabs(tabs)
    with tab_raw:
        _tab_profile(raw_df, preview_n)
    with tab_clean:
        _tab_review(quarantined, display_cleaned, preview_n)
    with tab_quality:
        _tab_quality(cleaned)
    with tab_insights:
        _tab_insights(cleaned)
    with tab_export:
        _tab_export(cleaned, quarantined)

    st.markdown(
        "<div class='footer'>Sales Data Cleaner · Pandas + DuckDB · "
        "audit-friendly quarantine</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
