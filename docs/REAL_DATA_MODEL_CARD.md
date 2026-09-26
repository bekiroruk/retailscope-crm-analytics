# Model card — UCI real-data track

## Intended use

Rank previously active customers by the probability of no sale in the next 90
days and estimate their next-90-day net revenue for analysis. The models support
portfolio exploration and interview discussion, not automated communication.

## Population and target

The population contains customers with an identified `Customer ID` and a sale
within 180 days before each snapshot. The classification target is no sale in
the following 90 days. The regression target is signed net revenue in that
period, including returns.

## Features

Only pre-cutoff behavior is used: recency, tenure, order counts, net revenue,
average order value, unique products, units, return-value rate, and recent order
trend. Country is reported but excluded from modeling.

## Selection and evaluation

Dummy, logistic-regression, and histogram-gradient-boosting classifiers are
compared on Average Precision. Mean and histogram-gradient-boosting regressors
are compared on MAE. Selection uses June 2011 validation; September 2011 is a
held-out test. See `REAL_DATA_VALIDATION.md` for results.

## Limitations

The dataset covers one UK non-store retailer from 2009–2011 and may not
generalize to contemporary retail, Turkey, or baby products. There is no
consent history, cost, campaign exposure, household identity, acquisition
source, category, or brand. Scores must not be interpreted as causality,
eligibility, or predicted profit.
