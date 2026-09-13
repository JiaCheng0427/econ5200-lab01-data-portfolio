
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency


def profile_dataframe(
    df: pd.DataFrame,
    unit_col: str = "name",
    time_col: str = "date",
) -> dict:
    """
    Profile the structure and completeness of a DataFrame.

    Returns information about shape, number of units and periods,
    panel structure, balance, and missing values.
    """
    assert isinstance(df, pd.DataFrame), "df must be a pandas DataFrame."
    assert not df.empty, "df cannot be empty."
    assert unit_col in df.columns, f"{unit_col} is not in the DataFrame."
    assert time_col in df.columns, f"{time_col} is not in the DataFrame."

    profile = {}

    profile["shape"] = df.shape
    profile["n_units"] = df[unit_col].nunique()
    profile["n_periods"] = df[time_col].nunique()

    if profile["n_units"] > 1 and profile["n_periods"] > 1:
        profile["structure"] = "panel"
    elif profile["n_periods"] > 1:
        profile["structure"] = "time series"
    else:
        profile["structure"] = "cross-sectional"

    periods_per_unit = (
        df.groupby(unit_col)[time_col].nunique()
    )

    complete_units = periods_per_unit[
        periods_per_unit == profile["n_periods"]
    ]

    profile["complete_units"] = len(complete_units)
    profile["balanced"] = (
        len(complete_units) == profile["n_units"]
    )

    profile["missing"] = (
        df.isna().mean() * 100
    ).round(1).to_dict()

    return profile


def compute_valuation(
    df: pd.DataFrame,
    benchmark: str = "USA",
) -> pd.DataFrame:
    """
    Compute implied PPP and currency valuation relative to a benchmark.

    Positive valuation_pct indicates overvaluation.
    Negative valuation_pct indicates undervaluation.
    """
    assert isinstance(df, pd.DataFrame), "df must be a DataFrame."

    required = {
        "date",
        "local_price",
        "dollar_ex",
        "dollar_price",
    }

    assert required.issubset(df.columns), (
        f"Missing required columns: {required - set(df.columns)}"
    )

    result = df.copy()

    if "iso_a3" in result.columns:
        benchmark_col = "iso_a3"
    elif "name" in result.columns:
        benchmark_col = "name"
    else:
        raise AssertionError(
            "Data must contain either iso_a3 or name."
        )

    benchmark_prices = (
        result.loc[
            result[benchmark_col] == benchmark,
            ["date", "dollar_price"],
        ]
        .drop_duplicates("date")
        .rename(columns={"dollar_price": "benchmark_price"})
    )

    assert not benchmark_prices.empty, (
        f"Benchmark '{benchmark}' was not found."
    )

    result = result.merge(
        benchmark_prices,
        on="date",
        how="left",
    )

    result["implied_ppp"] = (
        result["local_price"] / result["benchmark_price"]
    )

    result["valuation_pct"] = (
        (
            result["implied_ppp"]
            - result["dollar_ex"]
        )
        / result["dollar_ex"]
        * 100
    )

    return result


def diagnose_missing(
    df: pd.DataFrame,
    unit_col: str = "name",
    time_col: str = "date",
) -> pd.DataFrame:
    """
    Diagnose missing-data patterns by column.

    Chi-square tests check whether missingness is associated
    with units or time. These flags are diagnostics only;
    they do not prove that data are MCAR or MAR.
    """
    assert isinstance(df, pd.DataFrame), "df must be a DataFrame."
    assert unit_col in df.columns, f"{unit_col} is missing."
    assert time_col in df.columns, f"{time_col} is missing."

    rows = []

    for col in df.columns:
        missing = df[col].isna()

        missing_count = int(missing.sum())
        missing_pct = float(missing.mean() * 100)

        unit_p = np.nan
        time_p = np.nan

        if missing_count > 0 and missing.nunique() > 1:

            unit_table = pd.crosstab(
                df[unit_col],
                missing,
            )

            if (
                unit_table.shape[0] > 1
                and unit_table.shape[1] > 1
            ):
                _, unit_p, _, _ = chi2_contingency(
                    unit_table
                )

            time_table = pd.crosstab(
                df[time_col],
                missing,
            )

            if (
                time_table.shape[0] > 1
                and time_table.shape[1] > 1
            ):
                _, time_p, _, _ = chi2_contingency(
                    time_table
                )

        if missing_count == 0:
            flag = "No missing data"

        elif (
            (not pd.isna(unit_p) and unit_p < 0.05)
            or
            (not pd.isna(time_p) and time_p < 0.05)
        ):
            flag = "MAR-like pattern / not MCAR"

        else:
            flag = "MCAR plausible (not proven)"

        rows.append(
            {
                "column": col,
                "missing_count": missing_count,
                "missing_pct": round(missing_pct, 1),
                "unit_assoc_p": unit_p,
                "time_assoc_p": time_p,
                "missingness_flag": flag,
            }
        )

    return pd.DataFrame(rows)
