calc_fanova <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  use_virtualenv("../.venv/")

  feature_names <- mv %>%
    select(starts_with(dim_prefix)) %>%
    colnames()

  X <- mv %>% select(all_of(feature_names))
  y <- mv[[colname_metric]]

  # Call the existing Python MultiverseFanova class via reticulate
  pd <- import("pandas")
  py_run_string("import sys; sys.path.append('..')")
  mv_fanova_mod <- import("src.metrics.functional_anova")
  X_pd <- r_to_py(X)
  y_pd <- pd$Series(y)

  result_csv <- tempfile(fileext = ".csv")

  mv_fav <- mv_fanova_mod$MultiverseFanova(features = X_pd, outcome = y_pd)
  result_pd <- mv_fav$quantify_importance(save_to = result_csv)

  importance <- read_csv(result_csv)

  return(importance)
}

calc_regression <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  features <- mv %>%
    select(starts_with(dim_prefix)) %>%
    colnames()

  formula <- as.formula(
    paste(colname_metric, "~", paste(features, collapse = " + "))
  )

  lm_fitted <- lm(formula, data = mv)

  result <- tidy(lm_fitted)
  attr(result, "model") <- lm_fitted
  attr(result, "formula") <- formula

  return(result)
}
