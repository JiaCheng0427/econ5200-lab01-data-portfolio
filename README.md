# econ5200-lab01-data-portfolio
# Data Quality Profiling — Big Mac Index

## Objective

This project examines data quality issues in the Big Mac Index and shows how coding and methodological errors can affect economic conclusions.

## Methodology

- Diagnosed and corrected an error in the PPP valuation formula.
- Compared corrected currency valuation results across countries.
- Examined missing observations in an unbalanced panel dataset.
- Compared complete-panel averages with averages using all available observations.
- Built a `profile_dataframe()` function to summarize the structure and completeness of a dataset.

## Key Findings

- Correcting the PPP formula changed the currency ranking substantially, with Switzerland appearing as the most overvalued currency in July 2024.
- Removing every country with an incomplete panel excluded 32 of 57 country labels and created an upward bias in the estimated average Big Mac price.
- The complete-panel average was approximately $0.081 higher, or 2.1%, than the all-available average and was higher in 33 of 45 periods.
- The Big Mac dataset contains 57 units and 45 periods and is an unbalanced panel.
- Only 25 units appear in every period, and 7 columns have more than 10% missing values.
