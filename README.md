# Data Quality Profiling — Big Mac Index

## Objective

This project examines how data quality, panel structure, and missing-data decisions can affect economic conclusions using The Economist's Big Mac Index.

## Methodology

- Diagnosed and corrected a PPP valuation formula.
- Compared complete-panel and all-available analyses.
- Profiled the dataset's panel structure and missing-data patterns.
- Built a reusable `data_utils.py` module.
- Created a Streamlit dashboard for interactive data-quality analysis.

## Key Findings

- The dataset contains 57 countries or regions across 45 periods.
- Only 25 units appear in all 45 periods, so the panel is unbalanced.
- After correcting the PPP formula, Switzerland was the most overvalued currency in July 2024 at about 41.8%.
- Restricting the sample to complete-panel countries raised the average Big Mac price by about $0.081, or 2.1%.
- The complete-panel average was higher in 33 of 45 periods.

## Economic Interpretation

Dropping incomplete panel units changes the composition of the sample and can introduce selection bias. This shows that data-cleaning choices can materially affect economic conclusions.
