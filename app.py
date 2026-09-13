
from __future__ import annotations

from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from src.data_utils import (
    diagnose_missing,
    profile_dataframe,
)


BIG_MAC_URL = (
    "https://raw.githubusercontent.com/"
    "TheEconomist/big-mac-data/"
    "master/output-data/big-mac-full-index.csv"
)


def guess_time_column(df: pd.DataFrame) -> str:
    """
    Guess which column represents time.
    """

    preferred_names = [
        "date",
        "time",
        "year",
        "period",
        "month",
        "quarter",
    ]

    lower_names = {
        str(col).lower(): col
        for col in df.columns
    }

    # Auto-detection first checks common time-column names.
    for name in preferred_names:
        if name in lower_names:
            return lower_names[name]

    # If no obvious name exists, choose the column that
    # can most successfully be interpreted as dates.
    best_col = df.columns[0]
    best_score = -1.0

    for col in df.columns:
        parsed = pd.to_datetime(
            df[col],
            errors="coerce",
        )

        score = parsed.notna().mean()

        if score > best_score:
            best_score = score
            best_col = col

    return best_col


def guess_unit_column(
    df: pd.DataFrame,
    time_col: str,
) -> str:
    """
    Guess which column identifies units such as countries.
    """

    preferred_names = [
        "name",
        "country",
        "entity",
        "unit",
        "iso_a3",
        "id",
    ]

    lower_names = {
        str(col).lower(): col
        for col in df.columns
    }

    for name in preferred_names:
        if (
            name in lower_names
            and lower_names[name] != time_col
        ):
            return lower_names[name]

    candidates = [
        col
        for col in df.columns
        if col != time_col
    ]

    # Repeated values are useful for identifying panel units.
    for col in candidates:
        n_unique = df[col].nunique()

        if 1 < n_unique < len(df):
            return col

    return candidates[0]


st.set_page_config(
    page_title="Data Quality Profiling",
    layout="wide",
)

st.title("Data Quality Profiling — Big Mac Index")

st.write(
    """
    This dashboard profiles a dataset's structure,
    examines missing-data patterns, and measures the
    bias introduced by dropping incomplete panel units.
    """
)


# ---------------------------------------------------------
# DATA SOURCE
# ---------------------------------------------------------

source = st.sidebar.radio(
    "Choose a data source",
    [
        "Big Mac Index",
        "Upload CSV",
    ],
)


if source == "Upload CSV":

    uploaded_file = st.sidebar.file_uploader(
        "Upload a CSV file",
        type=["csv"],
    )

    if uploaded_file is None:
        st.info("Upload a CSV file to begin.")
        st.stop()

    file_bytes = uploaded_file.getvalue()

    file_key = (
        uploaded_file.name,
        len(file_bytes),
        hash(file_bytes),
    )

    # Streamlit reruns the script whenever a widget changes.
    # session_state keeps the uploaded data available between
    # those reruns instead of reading it from scratch each time.
    if st.session_state.get("file_key") != file_key:

        st.session_state["file_key"] = file_key

        st.session_state["uploaded_df"] = pd.read_csv(
            BytesIO(file_bytes)
        )

    df = st.session_state["uploaded_df"].copy()


else:

    @st.cache_data
    def load_big_mac() -> pd.DataFrame:
        return pd.read_csv(
            BIG_MAC_URL,
            parse_dates=["date"],
        )

    df = load_big_mac()


# ---------------------------------------------------------
# PREVIEW
# ---------------------------------------------------------

st.subheader("1. Data Preview")

st.dataframe(
    df.head(20),
    width="stretch",
)


# ---------------------------------------------------------
# AUTO-DETECT STRUCTURE
# ---------------------------------------------------------

auto_time = guess_time_column(df)

time_col = st.sidebar.selectbox(
    "Time column",
    options=list(df.columns),
    index=list(df.columns).index(auto_time),
)

auto_unit = guess_unit_column(
    df,
    time_col,
)

unit_col = st.sidebar.selectbox(
    "Unit column",
    options=list(df.columns),
    index=list(df.columns).index(auto_unit),
)


profile = profile_dataframe(
    df,
    unit_col=unit_col,
    time_col=time_col,
)


st.subheader("2. Data Structure")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Rows",
    profile["shape"][0],
)

col2.metric(
    "Units",
    profile["n_units"],
)

col3.metric(
    "Periods",
    profile["n_periods"],
)

col4.metric(
    "Structure",
    profile["structure"],
)


col5, col6 = st.columns(2)

col5.metric(
    "Complete units",
    profile["complete_units"],
)

col6.metric(
    "Balanced panel?",
    str(profile["balanced"]),
)


# ---------------------------------------------------------
# MISSING DATA
# ---------------------------------------------------------

st.subheader("3. Missing Data")

missing_df = diagnose_missing(
    df,
    unit_col=unit_col,
    time_col=time_col,
)

st.dataframe(
    missing_df,
    width="stretch",
)


missing_bar = px.bar(
    missing_df.sort_values(
        "missing_pct",
        ascending=False,
    ),
    x="column",
    y="missing_pct",
    title="Missing Values by Column (%)",
)

st.plotly_chart(
    missing_bar,
    width="stretch",
)


missing_matrix = (
    df.head(200)
    .isna()
    .astype(int)
    .T
)

missing_heatmap = px.imshow(
    missing_matrix,
    aspect="auto",
    title="Missing-Data Pattern",
)

st.plotly_chart(
    missing_heatmap,
    width="stretch",
)


# ---------------------------------------------------------
# PANEL BIAS
# ---------------------------------------------------------

if profile["structure"] == "panel":

    st.subheader(
        "4. Complete-Panel vs All-Available Analysis"
    )

    numeric_cols = list(
        df.select_dtypes(
            include="number"
        ).columns
    )

    if not numeric_cols:

        st.warning(
            "No numeric variable is available for comparison."
        )

    else:

        if "dollar_price" in numeric_cols:
            default_variable = "dollar_price"
        else:
            default_variable = numeric_cols[0]

        value_col = st.selectbox(
            "Variable to average",
            options=numeric_cols,
            index=numeric_cols.index(
                default_variable
            ),
        )

        display_mode = st.radio(
            "Display",
            [
                "Compare both",
                "All available",
                "Complete-panel only",
            ],
            horizontal=True,
        )

        n_periods = df[time_col].nunique()

        periods_per_unit = (
            df.groupby(unit_col)[time_col]
            .nunique()
        )

        complete_units = (
            periods_per_unit[
                periods_per_unit == n_periods
            ]
            .index
        )

        complete_df = df[
            df[unit_col].isin(complete_units)
        ].copy()

        complete_only = (
            complete_df
            .groupby(time_col)[value_col]
            .mean()
        )

        all_available = (
            df
            .groupby(time_col)[value_col]
            .mean()
        )

        comparison = pd.concat(
            [
                complete_only.rename(
                    "complete_only"
                ),
                all_available.rename(
                    "all_available"
                ),
            ],
            axis=1,
        ).dropna()

        comparison["gap"] = (
            comparison["complete_only"]
            - comparison["all_available"]
        )

        comparison["gap_pct"] = (
            comparison["gap"]
            / comparison["all_available"]
            * 100
        )

        # The complete-panel filter is not random.
        # Units that joined late or left early are removed.
        # Because sample membership depends on continuity
        # of observation, the resulting global average can
        # differ systematically from the all-available sample.

        mean_gap = comparison["gap"].mean()

        mean_gap_pct = (
            comparison["gap_pct"].mean()
        )

        higher_periods = int(
            (comparison["gap"] > 0).sum()
        )

        metric1, metric2, metric3 = st.columns(3)

        metric1.metric(
            "Mean bias",
            f"${mean_gap:+.3f}",
        )

        metric2.metric(
            "Mean bias (%)",
            f"{mean_gap_pct:+.1f}%",
        )

        metric3.metric(
            "Complete-panel higher",
            f"{higher_periods} of {len(comparison)} periods",
        )


        if display_mode == "All available":

            plot_df = comparison[
                ["all_available"]
            ]

        elif display_mode == "Complete-panel only":

            plot_df = comparison[
                ["complete_only"]
            ]

        else:

            plot_df = comparison[
                [
                    "complete_only",
                    "all_available",
                ]
            ]


        plot_df = (
            plot_df
            .reset_index()
            .melt(
                id_vars=[time_col],
                var_name="sample",
                value_name=value_col,
            )
        )

        comparison_plot = px.line(
            plot_df,
            x=time_col,
            y=value_col,
            color="sample",
            markers=True,
            title=(
                "Complete-Panel vs "
                "All-Available Average"
            ),
        )

        st.plotly_chart(
            comparison_plot,
            width="stretch",
        )


# ---------------------------------------------------------
# EVALUATION
# ---------------------------------------------------------

st.subheader("5. Evaluation")

st.markdown(
    """
The dashboard shows that data quality is not simply a
data-cleaning issue; it can change an economic conclusion.

Missing observations may be concentrated in particular
countries or time periods. Dropping every unit with an
incomplete history therefore changes the composition of the
sample rather than removing observations randomly.

This is a form of **selection bias**. The arithmetic for the
complete-panel sample may be correct, but the sample itself
has been selected according to continuity of observation.

Comparing complete-panel and all-available averages makes
the direction and magnitude of that bias visible instead of
assuming that the restricted sample represents the full
population.
"""
)
