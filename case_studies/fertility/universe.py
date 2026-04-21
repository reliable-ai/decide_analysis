"""
Effect of fertility on religiosity and political attitudes

Reimplementation of **Model #2** from Steegen et al. (2016)-

Original R implementation: `example-durante.Rmd` (using the R `multiverse` package).

The model fits: `RelComp ~ Fertility * RelationshipStatus` (OLS)
"""


import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from multiversum import Universe


settings = {
    # Default settings for standalone / interactive use.
    # Automatically overridden when run as part of the multiverse.
    "dimensions": {
        "cycle_length": "cl_option1",
        "certainty": "cer_option1",
        "menstrual_calculation": "mc_option1",
        "fertile": "fer_option1",
        "relationship_status": "rs_option1",
    }
}


universe = Universe(
    settings=settings,
)

dims = universe.dimensions

date_cols = [
    "DateTesting",
    "StartDateofLastPeriod",
    "StartDateofPeriodBeforeLast",
    "StartDateNext",
]
df = pd.read_csv("durante.csv", parse_dates=date_cols)

# Reverse-score items (only used for Models 3-6 in the original paper,
# included here for completeness – they do not affect Model 2).
for col in ["Abortion", "StemCell", "Marijuana", "RichTax", "StLiving", "Profit"]:
    df[col] = abs(7 - df[col]) + 1

df["FiscConsComp"] = (
    df["FreeMarket"]
    + df["PrivSocialSec"]
    + df["RichTax"]
    + df["StLiving"]
    + df["Profit"]
)
df["SocConsComp"] = (
    df["Marriage"]
    + df["RestrictAbortion"]
    + df["Abortion"]
    + df["StemCell"]
    + df["Marijuana"]
)

# ---------------------------------------------------------------------------
# 1. Compute ComputedCycleLength (always needed)
# ---------------------------------------------------------------------------
df["ComputedCycleLength"] = (
    df["StartDateofLastPeriod"] - df["StartDateofPeriodBeforeLast"]
).dt.days

# ---------------------------------------------------------------------------
# 2. Filter by cycle length
# ---------------------------------------------------------------------------
if dims["cycle_length"] == "cl_option2":
    df = df[(df["ComputedCycleLength"] > 25) & (df["ComputedCycleLength"] < 35)]
elif dims["cycle_length"] == "cl_option3":
    df = df[(df["ReportedCycleLength"] > 25) & (df["ReportedCycleLength"] < 35)]
# cl_option1: no exclusion

# ---------------------------------------------------------------------------
# 3. Filter by self-reported certainty
# ---------------------------------------------------------------------------
if dims["certainty"] == "cer_option2":
    df = df[(df["Sure1"] > 6) | (df["Sure2"] > 6)]
# cer_option1: no exclusion

# ---------------------------------------------------------------------------
# 4. Compute NextMenstrualOnset (multiverse branch)
# ---------------------------------------------------------------------------
if dims["menstrual_calculation"] == "mc_option1":
    df["NextMenstrualOnset"] = df["StartDateofLastPeriod"] + pd.to_timedelta(
        df["ComputedCycleLength"], unit="D"
    )
elif dims["menstrual_calculation"] == "mc_option2":
    df["NextMenstrualOnset"] = df["StartDateofLastPeriod"] + pd.to_timedelta(
        df["ReportedCycleLength"], unit="D"
    )
else:  # mc_option3
    df["NextMenstrualOnset"] = df["StartDateNext"]

# ---------------------------------------------------------------------------
# 5. Compute CycleDay
# ---------------------------------------------------------------------------
df["CycleDay"] = 28 - (df["NextMenstrualOnset"] - df["DateTesting"]).dt.days

# Override for specific workers (as in the original analysis)
df.loc[df["WorkerID"] == 15, "CycleDay"] = 11
df.loc[df["WorkerID"] == 16, "CycleDay"] = 18

# Clamp to [1, 28] – replicating R's nested ifelse exactly:
#   ifelse(CycleDay > 1 & CycleDay < 28, CycleDay,
#          ifelse(CycleDay < 1, 1, 28))
df["CycleDay"] = np.where(
    (df["CycleDay"] > 1) & (df["CycleDay"] < 28),
    df["CycleDay"],
    np.where(df["CycleDay"] < 1, 1, 28),
)

# ---------------------------------------------------------------------------
# 6. Compute Fertility (multiverse branch)
#    Options 1-3 produce a three-level variable (high / low / NA),
#    options 4-5 produce a binary variable (high / low).
# ---------------------------------------------------------------------------
df["Fertility"] = pd.Series(np.nan, index=df.index, dtype="object")

if dims["fertile"] == "fer_option1":
    df.loc[(df["CycleDay"] >= 7) & (df["CycleDay"] <= 14), "Fertility"] = "high"
    df.loc[(df["CycleDay"] >= 17) & (df["CycleDay"] <= 25), "Fertility"] = "low"
elif dims["fertile"] == "fer_option2":
    df.loc[(df["CycleDay"] >= 6) & (df["CycleDay"] <= 14), "Fertility"] = "high"
    df.loc[(df["CycleDay"] >= 17) & (df["CycleDay"] <= 27), "Fertility"] = "low"
elif dims["fertile"] == "fer_option3":
    df.loc[(df["CycleDay"] >= 9) & (df["CycleDay"] <= 17), "Fertility"] = "high"
    df.loc[(df["CycleDay"] >= 18) & (df["CycleDay"] <= 25), "Fertility"] = "low"
elif dims["fertile"] == "fer_option4":
    df["Fertility"] = np.where(
        (df["CycleDay"] >= 8) & (df["CycleDay"] <= 14), "high", "low"
    )
else:  # fer_option5
    df["Fertility"] = np.where(
        (df["CycleDay"] >= 8) & (df["CycleDay"] <= 17), "high", "low"
    )
    
# ---------------------------------------------------------------------------
# 7. Compute RelationshipStatus (multiverse branch)
# ---------------------------------------------------------------------------
if dims["relationship_status"] == "rs_option1":
    df["RelationshipStatus"] = np.where(
        (df["Relationship"] == 1) | (df["Relationship"] == 2),
        "Single",
        "Relationship",
    )
elif dims["relationship_status"] == "rs_option2":
    df["RelationshipStatus"] = np.where(
        df["Relationship"] == 1,
        "Single",
        "Relationship",
    )
else:  # rs_option3
    df["RelationshipStatus"] = pd.Series(np.nan, index=df.index, dtype="object")
    df.loc[df["Relationship"] == 1, "RelationshipStatus"] = "Single"
    df.loc[
        (df["Relationship"] == 3) | (df["Relationship"] == 4),
        "RelationshipStatus",
    ] = "Relationship"
    
# ---------------------------------------------------------------------------
# 8. Compute composite religiosity score
# ---------------------------------------------------------------------------
df["RelComp"] = ((df["Rel1"] + df["Rel2"] + df["Rel3"]) / 3).round(2)

# ---------------------------------------------------------------------------
# 9. Fit OLS: RelComp ~ Fertility * RelationshipStatus
#    Rows with NaN in Fertility or RelationshipStatus are dropped
#    (matching R's lm() behaviour with factor NAs).
# ---------------------------------------------------------------------------
model_df = df.dropna(subset=["Fertility", "RelationshipStatus", "RelComp"]).copy()
model_df["Fertility"] = pd.Categorical(
    model_df["Fertility"], categories=["high", "low"]
)
model_df["RelationshipStatus"] = pd.Categorical(
    model_df["RelationshipStatus"], categories=["Relationship", "Single"]
)

fit = smf.ols(
    "RelComp ~ C(Fertility, Treatment('high')) * C(RelationshipStatus, Treatment('Relationship'))",
    data=model_df,
).fit()

# Build a tidy summary (equivalent to broom::tidy with conf.int = TRUE)
conf = fit.conf_int()

# Map statsmodels term names to clean, short names
term_map = {
    "Intercept": "intercept",
    "C(Fertility, Treatment('high'))[T.low]": "fertility_low",
    "C(RelationshipStatus, Treatment('Relationship'))[T.Single]": "relationship_single",
    "C(Fertility, Treatment('high'))[T.low]:C(RelationshipStatus, Treatment('Relationship'))[T.Single]": "fertility_low_x_relationship_single",
}

result = pd.DataFrame(
    {
        "term": [term_map.get(t, t) for t in fit.params.index],
        "estimate": fit.params.values,
        "std_error": fit.bse.values,
        "statistic": fit.tvalues.values,
        "p_value": fit.pvalues.values,
        "conf_low": conf.iloc[:, 0].values,
        "conf_high": conf.iloc[:, 1].values,
    }
)

# Reshape to wide format: one row with combined column names (e.g., "fertility_low_estimate")
result = result.set_index("term").stack()
result.index = [f"{term}_{metric}" for term, metric in result.index]
result = result.to_frame().T.reset_index(drop=True)

universe.save_data(result)