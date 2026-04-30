from pathlib import Path

import pandas as pd
import plotly.express as px
from scipy.stats import mannwhitneyu

from db import CELL_COLUMNS, engine


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"

PART2_SUMMARY_PATH = OUTPUT_DIR / "part2_summary.csv"
PART3_STATS_PATH = OUTPUT_DIR / "part3_stats_summary.csv"
PART3_BOXPLOT_PATH = OUTPUT_DIR / "part3_response_boxplot.html"
PART4_SUBSET_PATH = OUTPUT_DIR / "part4_baseline_subset.csv"
PART4_PROJECT_COUNTS_PATH = OUTPUT_DIR / "part4_project_counts.csv"
PART4_RESPONSE_COUNTS_PATH = OUTPUT_DIR / "part4_response_counts.csv"
PART4_SEX_COUNTS_PATH = OUTPUT_DIR / "part4_sex_counts.csv"
PART4_B_CELL_AVERAGE_PATH = OUTPUT_DIR / "part4_male_responder_b_cell_average.csv"

SIGNIFICANCE_LEVEL = 0.05


FREQUENCY_QUERY = """
SELECT
    samples.sample_id,
    cells.cell_type,
    cells.cell_count
FROM samples
JOIN cells ON samples.sample_id = cells.sample_id
"""


PART3_METADATA_QUERY = """
SELECT
    samples.sample_id,
    subjects.response
FROM samples
JOIN subjects ON samples.subject_id = subjects.subject_id
WHERE subjects.condition = 'melanoma'
  AND subjects.treatment = 'miraclib'
  AND samples.sample_type = 'PBMC'
  AND subjects.response IN ('yes', 'no')
"""


PART4_SUBSET_QUERY = """
SELECT
    projects.project_id,
    subjects.subject_id,
    subjects.response,
    subjects.sex,
    samples.sample_id,
    samples.sample_type,
    samples.time_from_treatment
FROM samples
JOIN subjects ON samples.subject_id = subjects.subject_id
JOIN projects ON subjects.project_id = projects.project_id
WHERE subjects.condition = 'melanoma'
  AND subjects.treatment = 'miraclib'
  AND samples.sample_type = 'PBMC'
  AND samples.time_from_treatment = 0
"""


PART4_B_CELL_AVERAGE_QUERY = """
SELECT
    'melanoma_male_responders_time_0' AS cohort,
    'b_cell' AS population,
    COUNT(DISTINCT samples.sample_id) AS sample_count,
    COUNT(DISTINCT subjects.subject_id) AS subject_count,
    ROUND(AVG(cells.cell_count), 2) AS average_count
FROM samples
JOIN subjects ON samples.subject_id = subjects.subject_id
JOIN cells ON samples.sample_id = cells.sample_id
WHERE subjects.condition = 'melanoma'
  AND samples.time_from_treatment = 0
  AND subjects.response = 'yes'
  AND subjects.sex = 'M'
  AND cells.cell_type = 'b_cell'
"""


def load_frequency_df() -> pd.DataFrame:
    df = pd.read_sql(FREQUENCY_QUERY, engine)
    df["total_count"] = df.groupby("sample_id")["cell_count"].transform("sum")
    df["percentage"] = df["cell_count"] / df["total_count"] * 100
    return df


def build_part2_summary_df() -> pd.DataFrame:
    df = load_frequency_df().rename(
        columns={
            "sample_id": "sample",
            "cell_type": "population",
            "cell_count": "count",
        }
    )
    return df[["sample", "total_count", "population", "count", "percentage"]].sort_values(
        ["sample", "population"]
    )


def build_part3_analysis_df() -> pd.DataFrame:
    frequency_df = load_frequency_df()
    metadata_df = pd.read_sql(PART3_METADATA_QUERY, engine)
    return frequency_df.merge(metadata_df, on="sample_id", how="inner").sort_values(
        ["cell_type", "response", "sample_id"]
    )


def build_part3_boxplot(part3_df: pd.DataFrame):
    fig = px.box(
        part3_df,
        x="cell_type",
        y="percentage",
        color="response",
        points=False,
        category_orders={"cell_type": CELL_COLUMNS, "response": ["yes", "no"]},
        color_discrete_map={"yes": "#1d7f68", "no": "#b6463a"},
        labels={
            "cell_type": "Immune Cell Population",
            "percentage": "Relative Frequency (%)",
            "response": "Response",
        },
        title="PBMC Relative Frequencies: Miraclib Responders vs Non-Responders",
    )
    fig.update_layout(
        boxmode="group",
        template="plotly_white",
        legend_title_text="Response",
        margin={"l": 70, "r": 40, "t": 80, "b": 70},
    )
    return fig


def benjamini_hochberg_q_values(p_values: list[float]) -> list[float]:
    indexed_p_values = sorted(enumerate(p_values), key=lambda item: item[1])
    q_values = [1.0] * len(p_values)
    running_min = 1.0

    for rank in range(len(indexed_p_values), 0, -1):
        original_index, p_value = indexed_p_values[rank - 1]
        adjusted = min(running_min, p_value * len(indexed_p_values) / rank, 1.0)
        q_values[original_index] = adjusted
        running_min = adjusted

    return q_values


def build_part3_stats_df(part3_df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for cell_type in CELL_COLUMNS:
        cell_df = part3_df[part3_df["cell_type"] == cell_type]
        responder_values = cell_df[cell_df["response"] == "yes"]["percentage"]
        non_responder_values = cell_df[cell_df["response"] == "no"]["percentage"]

        statistic, p_value = mannwhitneyu(
            responder_values,
            non_responder_values,
            alternative="two-sided",
        )

        results.append(
            {
                "population": cell_type,
                "responder_n": responder_values.shape[0],
                "non_responder_n": non_responder_values.shape[0],
                "responder_mean_pct": responder_values.mean(),
                "non_responder_mean_pct": non_responder_values.mean(),
                "mean_difference_pct": responder_values.mean() - non_responder_values.mean(),
                "responder_median_pct": responder_values.median(),
                "non_responder_median_pct": non_responder_values.median(),
                "mannwhitney_u": statistic,
                "p_value": p_value,
                "significant": p_value < SIGNIFICANCE_LEVEL,
            }
        )

    stats_df = pd.DataFrame(results)
    stats_df["fdr_q_value"] = benjamini_hochberg_q_values(stats_df["p_value"].tolist())
    stats_df["significant_fdr"] = stats_df["fdr_q_value"] < SIGNIFICANCE_LEVEL
    return stats_df.sort_values("p_value")


def build_part4_subset_df() -> pd.DataFrame:
    return pd.read_sql(PART4_SUBSET_QUERY, engine).sort_values(
        ["project_id", "subject_id", "sample_id"]
    )


def build_part4_project_counts_df(part4_subset_df: pd.DataFrame) -> pd.DataFrame:
    return (
        part4_subset_df.groupby("project_id", as_index=False)["sample_id"]
        .nunique()
        .rename(columns={"sample_id": "sample_count"})
        .sort_values("project_id")
    )


def build_part4_response_counts_df(part4_subset_df: pd.DataFrame) -> pd.DataFrame:
    return (
        part4_subset_df.groupby("response", as_index=False)["subject_id"]
        .nunique()
        .rename(columns={"subject_id": "subject_count"})
        .sort_values("response")
    )


def build_part4_sex_counts_df(part4_subset_df: pd.DataFrame) -> pd.DataFrame:
    return (
        part4_subset_df.groupby("sex", as_index=False)["subject_id"]
        .nunique()
        .rename(columns={"subject_id": "subject_count"})
        .sort_values("sex")
    )


def build_part4_b_cell_average_df() -> pd.DataFrame:
    return pd.read_sql(PART4_B_CELL_AVERAGE_QUERY, engine)


def save_outputs(
    part2_df: pd.DataFrame,
    part3_stats_df: pd.DataFrame,
    part3_boxplot,
    part4_subset_df: pd.DataFrame,
    part4_project_counts_df: pd.DataFrame,
    part4_response_counts_df: pd.DataFrame,
    part4_sex_counts_df: pd.DataFrame,
    part4_b_cell_average_df: pd.DataFrame,
) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    part2_df.to_csv(PART2_SUMMARY_PATH, index=False)
    part3_stats_df.to_csv(PART3_STATS_PATH, index=False)
    part3_boxplot.write_html(str(PART3_BOXPLOT_PATH), include_plotlyjs="cdn")
    part4_subset_df.to_csv(PART4_SUBSET_PATH, index=False)
    part4_project_counts_df.to_csv(PART4_PROJECT_COUNTS_PATH, index=False)
    part4_response_counts_df.to_csv(PART4_RESPONSE_COUNTS_PATH, index=False)
    part4_sex_counts_df.to_csv(PART4_SEX_COUNTS_PATH, index=False)
    part4_b_cell_average_df.to_csv(PART4_B_CELL_AVERAGE_PATH, index=False)


def main() -> None:
    part2_df = build_part2_summary_df()
    part3_df = build_part3_analysis_df()
    part3_stats_df = build_part3_stats_df(part3_df)
    part3_boxplot = build_part3_boxplot(part3_df)
    part4_subset_df = build_part4_subset_df()
    part4_project_counts_df = build_part4_project_counts_df(part4_subset_df)
    part4_response_counts_df = build_part4_response_counts_df(part4_subset_df)
    part4_sex_counts_df = build_part4_sex_counts_df(part4_subset_df)
    part4_b_cell_average_df = build_part4_b_cell_average_df()

    save_outputs(
        part2_df,
        part3_stats_df,
        part3_boxplot,
        part4_subset_df,
        part4_project_counts_df,
        part4_response_counts_df,
        part4_sex_counts_df,
        part4_b_cell_average_df,
    )

    print(f"Part 2 summary rows: {part2_df.shape[0]:,}")
    print(f"Part 3 analysis rows: {part3_df.shape[0]:,}")
    print("Part 3 statistical summary:")
    print(part3_stats_df.to_string(index=False))
    print("Part 4 baseline subset counts:")
    print(part4_project_counts_df.to_string(index=False))
    print(part4_response_counts_df.to_string(index=False))
    print(part4_sex_counts_df.to_string(index=False))
    print("Part 4 male responder average B-cell count:")
    print(part4_b_cell_average_df.to_string(index=False))
    print(f"Saved outputs under: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
