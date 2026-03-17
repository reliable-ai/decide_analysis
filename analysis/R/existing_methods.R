remove_fake_decisions <- function (mv, dim_prefix = "mv_dim_") {
  dim_cols <- mv |> select(starts_with(dim_prefix)) |> colnames()
  fake <- dim_cols[sapply(mv[dim_cols], n_distinct) <= 1]
  if (length(fake) > 0) {
    message("Dropping fake decisions: ", paste(sub(paste0("^", dim_prefix), "", fake), collapse = ", "))
  }
  mv |> select(-all_of(fake))
}

calc_fanova <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  use_virtualenv("../.venv/")

  feature_names <- mv |>
    select(starts_with(dim_prefix)) |>
    colnames()

  X <- mv |> select(all_of(feature_names))
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

  importance <- read_csv(result_csv) |>
    rename(
      individual_importance = `individual importance`,
      total_importance = `total importance`
    )

  return(importance)
}

fanova_to_vec <- function (importance_df) {
  importance_vec <- importance_df |>
    # Get all columns starting with level_ and collapse them
    unite("path", starts_with("level_"), sep = "|") |>
    mutate(path = str_replace_all(path, "\\|NA", "")) |>
    select(path, individual_importance) |>
    deframe() |>
    sort(decreasing = TRUE)

  return(importance_vec)
}

calc_regression <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  features <- mv |>
    select(starts_with(dim_prefix)) |>
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
