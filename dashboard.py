from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from analysis import (
    PART2_SUMMARY_PATH,
    PART3_STATS_PATH,
    PART4_B_CELL_AVERAGE_PATH,
    PART4_PROJECT_COUNTS_PATH,
    PART4_RESPONSE_COUNTS_PATH,
    PART4_SEX_COUNTS_PATH,
    PART4_SUBSET_PATH,
    build_part3_analysis_df,
    main as run_analysis,
)
from db import CELL_COLUMNS, DB_PATH, engine
from load_data import load_data


REQUIRED_OUTPUTS = [
    PART2_SUMMARY_PATH,
    PART3_STATS_PATH,
    PART4_SUBSET_PATH,
    PART4_PROJECT_COUNTS_PATH,
    PART4_RESPONSE_COUNTS_PATH,
    PART4_SEX_COUNTS_PATH,
    PART4_B_CELL_AVERAGE_PATH,
]


st.set_page_config(
    page_title="Loblaw Bio Immune Cell Trial Dashboard",
    layout="wide",
)


def ensure_artifacts() -> None:
    if not DB_PATH.exists():
        load_data()

    if any(not path.exists() for path in REQUIRED_OUTPUTS):
        run_analysis()


@st.cache_data(show_spinner=False)
def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def load_part3_data() -> pd.DataFrame:
    return build_part3_analysis_df()


@st.cache_data(show_spinner=False)
def load_database_metrics() -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            COUNT(DISTINCT samples.sample_id) AS samples,
            COUNT(DISTINCT subjects.subject_id) AS subjects,
            COUNT(DISTINCT projects.project_id) AS projects,
            COUNT(*) AS cell_count_rows
        FROM samples
        JOIN subjects ON samples.subject_id = subjects.subject_id
        JOIN projects ON subjects.project_id = projects.project_id
        JOIN cells ON samples.sample_id = cells.sample_id
        """,
        engine,
    )


@st.cache_data(show_spinner=False)
def load_explorer_data() -> pd.DataFrame:
    return pd.read_sql(
        """
        SELECT
            projects.project_id,
            subjects.subject_id,
            subjects.condition,
            subjects.treatment,
            subjects.response,
            subjects.sex,
            samples.sample_id,
            samples.sample_type,
            samples.time_from_treatment,
            cells.cell_type,
            cells.cell_count
        FROM samples
        JOIN subjects ON samples.subject_id = subjects.subject_id
        JOIN projects ON subjects.project_id = projects.project_id
        JOIN cells ON samples.sample_id = cells.sample_id
        """,
        engine,
    )


def response_boxplot(part3_df: pd.DataFrame, selected_populations: list[str], show_points: bool):
    filtered_df = part3_df[part3_df["cell_type"].isin(selected_populations)]
    fig = px.box(
        filtered_df,
        x="cell_type",
        y="percentage",
        color="response",
        points="all" if show_points else False,
        category_orders={"cell_type": CELL_COLUMNS, "response": ["yes", "no"]},
        color_discrete_map={"yes": "#1d7f68", "no": "#b6463a"},
        labels={
            "cell_type": "Immune Cell Population",
            "percentage": "Relative Frequency (%)",
            "response": "Response",
        },
        title="Miraclib PBMC Response Comparison",
    )
    fig.update_layout(
        boxmode="group",
        template="plotly_white",
        margin={"l": 60, "r": 30, "t": 70, "b": 60},
    )
    return fig


def style_page() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(16, 88, 88, 0.16), transparent 32rem),
                linear-gradient(180deg, #fbf5e8 0%, #f7efe0 42%, #f3ead9 100%);
            color: #142620;
        }
        .hero {
            border: 1px solid rgba(20, 38, 32, 0.12);
            border-radius: 24px;
            padding: 2rem;
            background: rgba(255, 252, 244, 0.82);
            box-shadow: 0 18px 52px rgba(48, 36, 18, 0.12);
        }
        .hero h1 {
            font-size: clamp(2.2rem, 4vw, 4rem);
            line-height: 1;
            letter-spacing: -0.06em;
            margin: 0 0 0.6rem;
            color: #173b34;
        }
        .hero p {
            font-size: 1.05rem;
            margin: 0;
            color: #5c4934;
        }
        [data-testid="stMetricValue"] {
            color: #173b34;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def format_percent_columns(df: pd.DataFrame):
    return df.style.format(
        {
            "responder_mean_pct": "{:.2f}",
            "non_responder_mean_pct": "{:.2f}",
            "mean_difference_pct": "{:.2f}",
            "responder_median_pct": "{:.2f}",
            "non_responder_median_pct": "{:.2f}",
            "mannwhitney_u": "{:.0f}",
            "p_value": "{:.4g}",
            "fdr_q_value": "{:.4g}",
        }
    )


def main() -> None:
    ensure_artifacts()
    style_page()

    part2_df = read_csv(PART2_SUMMARY_PATH)
    part3_stats_df = read_csv(PART3_STATS_PATH)
    part3_df = load_part3_data()
    part4_subset_df = read_csv(PART4_SUBSET_PATH)
    project_counts_df = read_csv(PART4_PROJECT_COUNTS_PATH)
    response_counts_df = read_csv(PART4_RESPONSE_COUNTS_PATH)
    sex_counts_df = read_csv(PART4_SEX_COUNTS_PATH)
    b_cell_average_df = read_csv(PART4_B_CELL_AVERAGE_PATH)
    metrics_df = load_database_metrics()

    st.markdown(
        """
        <div class="hero">
            <h1>Loblaw Bio immune cell atlas</h1>
            <p>
                A compact dashboard for Bob Loblaw's miraclib trial: sample frequencies,
                response-linked population shifts, and baseline PBMC subset checks.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics = metrics_df.iloc[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Samples", f"{int(metrics['samples']):,}")
    col2.metric("Subjects", f"{int(metrics['subjects']):,}")
    col3.metric("Projects", f"{int(metrics['projects']):,}")
    col4.metric("Cell Count Rows", f"{int(metrics['cell_count_rows']):,}")

    st.sidebar.header("Dashboard Controls")
    selected_populations = st.sidebar.multiselect(
        "Cell populations",
        CELL_COLUMNS,
        default=CELL_COLUMNS,
    )
    if not selected_populations:
        st.sidebar.warning("Select at least one population; showing all populations for now.")
        selected_populations = CELL_COLUMNS
    show_points = st.sidebar.checkbox("Show individual samples on boxplots", value=False)
    st.sidebar.caption(
        "Note: quintazide is mentioned in the prompt text, but this analysis filters the "
        "provided trial data for miraclib as requested."
    )

    overview_tab, response_tab, baseline_tab, explorer_tab = st.tabs(
        ["Frequency Overview", "Response Analysis", "Baseline Subset", "Data Explorer"]
    )

    with overview_tab:
        st.subheader("Part 2: Relative Frequencies by Sample")
        sample_search = st.text_input("Filter sample IDs", placeholder="Example: sample00000")
        overview_df = part2_df[part2_df["population"].isin(selected_populations)]
        if sample_search:
            overview_df = overview_df[
                overview_df["sample"].astype(str).str.contains(sample_search, case=False, na=False)
            ]

        st.dataframe(
            overview_df.style.format({"percentage": "{:.2f}", "total_count": "{:.0f}", "count": "{:.0f}"}),
            use_container_width=True,
            hide_index=True,
        )

    with response_tab:
        st.subheader("Part 3: Miraclib PBMC Responders vs Non-Responders")
        st.plotly_chart(
            response_boxplot(part3_df, selected_populations, show_points),
            use_container_width=True,
        )

        st.write("Mann-Whitney U tests by cell population:")
        st.dataframe(format_percent_columns(part3_stats_df), use_container_width=True, hide_index=True)

        significant_df = part3_stats_df[part3_stats_df["significant"]]
        if significant_df.empty:
            st.info("No populations met the unadjusted p < 0.05 threshold.")
        else:
            populations = ", ".join(significant_df["population"].tolist())
            st.success(f"Unadjusted p < 0.05 populations: {populations}")

    with baseline_tab:
        st.subheader("Part 4: Baseline Melanoma PBMC Samples")
        st.caption(
            "Subset count tables use melanoma PBMC baseline samples treated with miraclib. "
            "The B-cell average follows the final prompt check: melanoma male responders at time 0."
        )
        avg_row = b_cell_average_df.iloc[0]
        avg_col, sample_col, subject_col = st.columns(3)
        avg_col.metric("Male responder avg B-cell count", f"{avg_row['average_count']:.2f}")
        sample_col.metric("Samples in average", f"{int(avg_row['sample_count']):,}")
        subject_col.metric("Subjects in average", f"{int(avg_row['subject_count']):,}")

        left_col, middle_col, right_col = st.columns(3)
        left_col.write("Samples by project")
        left_col.dataframe(project_counts_df, use_container_width=True, hide_index=True)
        middle_col.write("Subjects by response")
        middle_col.dataframe(response_counts_df, use_container_width=True, hide_index=True)
        right_col.write("Subjects by sex")
        right_col.dataframe(sex_counts_df, use_container_width=True, hide_index=True)

        st.write("Baseline subset rows")
        st.dataframe(part4_subset_df, use_container_width=True, hide_index=True)

    with explorer_tab:
        st.subheader("Queryable Trial Data")
        explorer_df = load_explorer_data()
        condition_filter = st.multiselect(
            "Condition",
            sorted(explorer_df["condition"].dropna().unique()),
            default=sorted(explorer_df["condition"].dropna().unique()),
        )
        treatment_filter = st.multiselect(
            "Treatment",
            sorted(explorer_df["treatment"].dropna().unique()),
            default=sorted(explorer_df["treatment"].dropna().unique()),
        )
        response_filter = st.multiselect(
            "Response",
            sorted(explorer_df["response"].dropna().unique()),
            default=sorted(explorer_df["response"].dropna().unique()),
        )

        filtered_explorer_df = explorer_df[
            explorer_df["condition"].isin(condition_filter)
            & explorer_df["treatment"].isin(treatment_filter)
            & explorer_df["response"].isin(response_filter)
            & explorer_df["cell_type"].isin(selected_populations)
        ]
        st.dataframe(filtered_explorer_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
