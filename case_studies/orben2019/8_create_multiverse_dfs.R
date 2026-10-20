##########################################################################################
# Additional script to extract the multiverse data frames from the saved results and
# export save them as CSVs. Have a look at the README for details on where to put the script.
##########################################################################################

library(readr)
library(dplyr)

# Helper: collapse a list-column element to a sorted, comma-separated string
list_to_str <- function(x) sapply(x, function(v) paste(sort(v), collapse = ", "))

##########################################################################################
# 1. YRBS  (Youth Risk Behavior Survey)
#    Decisions: x_variable, y_variable(s), controls, combination method
##########################################################################################
load("2_1_sca_yrbs_results.rda")

df_yrbs <- results_yrbs_sca %>%
  mutate(
    # Operationalizing technology use
    mv_dim_x_variable = unlist(x_variable),
    # Operationalizing adolescent well-being
    mv_dim_y_variable = list_to_str(y_variable),
    # Which co-variates to include
    mv_dim_controls = controls,
    # Other specifications: Either take mean of dichotomous well-being measures,
    # or code all cohort members who answered ‘yes’ to one or more as 1 and
    # all others as 0
    mv_dim_combination = combination
  ) %>%
  select(
    mv_dim_x_variable, mv_dim_y_variable,
    mv_dim_controls, mv_dim_combination,
    effect, t_value, p_value, standard_error, number, rsqrd
  )

write_csv(df_yrbs, "orben2019nhb_yrbs.csv.gz")
message("Saved orben2019nhb_yrbs.csv.gz  (", nrow(df_yrbs), " universes)")

##########################################################################################
# 2. MTF  (Monitoring the Future)
#    Two participant subsets answered different technology-use questions, so
#    mv_dim_mtf_subset distinguishes them.
#    Decisions: x_variable, y_variable(s), controls, subset
##########################################################################################
load("2_2_sca_mtf_results.rda")

df_mtf <- results_mtf_ds_total %>%
  mutate(
    # Operationalizing technology use
    mv_dim_x_variable = sapply(x_variable, function(v) paste(v, collapse = ", ")),
    # Operationalizing adolescent well-being
    mv_dim_y_variable = list_to_str(y_variable),
    # Which co-variates to include
    mv_dim_controls = controls
  ) %>%
  select(
    mv_dim_x_variable, mv_dim_y_variable,
    mv_dim_controls,
    effect, t_value, p_value, standard_error, number, rsqrd
  )

write_csv(df_mtf, "orben2019nhb_mtf.csv.gz")
message("Saved orben2019nhb_mtf.csv.gz  (", nrow(df_mtf), " universes)")

##########################################################################################
# 3 & 4. MCS  (Millennium Cohort Study)
#    Two respondent perspectives: cohort members (self-report) and parents.
#    Decisions: x_variable, y_variable(s), controls
##########################################################################################

make_mcs_df <- function(results) {
  results %>%
    mutate(
      # Operationalizing technology use
      mv_dim_x_variable = sapply(x_variable, function(v) paste(v, collapse = ", ")),
      # Operationalizing adolescent well-being
      mv_dim_y_variable = list_to_str(y_variable),
      # Which co-variates to include
      mv_dim_controls = controls
    ) %>%
    # Use well-being measures declared by cohort members or those declared by their caregivers
    # Only available in the combined multiverse.
    rename(mv_dim_respondent = any_of("respondent")) %>%
    select(
      mv_dim_x_variable, mv_dim_y_variable, mv_dim_controls,
      any_of("mv_dim_respondent"),
      effect, t_value, p_value, standard_error, number, rsqrd
    )
}

# Cohort members => cm
load("2_3_sca_mcs_results_cm.rda")
df_mcs_cm <- make_mcs_df(results_mcs_sca_cm)
write_csv(df_mcs_cm, "_orben2019nhb_mcs_cm.csv.gz")
message("Saved _orben2019nhb_mcs_cm.csv.gz  (", nrow(df_mcs_cm), " universes)")

# Parents => pr
load("2_3_sca_mcs_results_pr.rda")
df_mcs_pr <- make_mcs_df(results_mcs_sca_pr)
write_csv(df_mcs_pr, "_orben2019nhb_mcs_pr.csv.gz")
message("Saved _orben2019nhb_mcs_pr.csv.gz  (", nrow(df_mcs_pr), " universes)")

# Combined total (cm + pr)
load("2_3_sca_mcs_results.rda")
df_mcs_total <- make_mcs_df(results_mcs_sca_total)
write_csv(df_mcs_total, "orben2019nhb_mcs_total.csv.gz")
message("Saved orben2019nhb_mcs_total.csv.gz  (", nrow(df_mcs_total), " universes)")
