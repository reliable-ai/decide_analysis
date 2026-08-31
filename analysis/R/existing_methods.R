remove_fake_decisions <- function (mv, dim_prefix = "mv_dim_") {
  dim_cols <- mv |> select(starts_with(dim_prefix)) |> colnames()
  fake <- dim_cols[sapply(mv[dim_cols], n_distinct) <= 1]
  if (length(fake) > 0) {
    message("Dropping fake decisions: ", paste(sub(paste0("^", dim_prefix), "", fake), collapse = ", "))
  }
  mv |> select(-all_of(fake))
}

calc_fanova <- function (mv, colname_metric, dim_prefix = "mv_dim_", use_individual = FALSE) {
  use_virtualenv("../.venv/")

  feature_names <- mv |>
    select(starts_with(dim_prefix)) |>
    colnames()

  # Fanova doesn't work with < features. Potentially surface this issue earlier on the R side.
  if (length(feature_names) < 2) {
    stop(
      "calc_fanova() needs at least two varying decisions, got ",
      length(feature_names), "."
    )
  }

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
  if (use_individual) {
    result_pd <- mv_fav$quantify_individual_importance(save_to = result_csv)
  } else {
    result_pd <- mv_fav$quantify_importance(save_to = result_csv)
  }

  rename_names <- c(
    "decision" = "...1",
    "individual_importance" = "individual importance",
    "total_importance" = "total importance"
  )
  importance <- read_csv(result_csv, show_col_types = FALSE) |>
    rename(any_of(rename_names))

  return(importance)
}

# Total-importance-per-decision vector from a `calc_fanova()` result that was
# computed with `use_individual = FALSE` (i.e. the full interaction
# decomposition from `quantify_importance()`). Only the single-decision rows are
# kept; their `total importance` is the decision's main effect plus every
# interaction it participates in (comparable to DECIDE').
fanova_total_to_vec <- function (importance_df) {
  level_cols <- colnames(importance_df)[startsWith(colnames(importance_df), "level_")]
  higher_level_cols <- setdiff(level_cols, "level_0")

  singletons <- importance_df
  if (length(higher_level_cols) > 0) {
    singletons <- singletons |> filter(if_all(all_of(higher_level_cols), is.na))
  }

  singletons |>
    select(decision = level_0, total_importance) |>
    deframe() |>
    sort(decreasing = TRUE)
}

fanova_to_vec <- function (importance_df) {
  has_level_cols <- any(startsWith(colnames(importance_df), "level_"))
  if (has_level_cols) {
    importance_vec <- importance_df |>
      # Get all columns starting with level_ and collapse them
      unite("path", starts_with("level_"), sep = "|") |>
      mutate(path = str_replace_all(path, "\\|NA", "")) |>
      select(path, individual_importance) |>
      deframe() |>
      sort(decreasing = TRUE)
  } else {
    importance_vec <- importance_df |>
      select(decision, individual_importance) |>
      deframe() |>
      sort(decreasing = TRUE)
  }

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

  attr(lm_fitted, "tidy") <- tidy(lm_fitted)
  attr(lm_fitted, "formula") <- formula
  attr(lm_fitted, "features") <- features

  return(lm_fitted)
}

tidy_regression_coefficients <- function (reg_result, dim_prefix = "mv_dim_") {
  features <- attr(reg_result, "features")

  match_decision <- function (term) {
    matches <- features[startsWith(term, features)]

    if (length(matches) == 0) {
      return(term)
    }

    matches[which.max(nchar(matches))]
  }

  attr(reg_result, "tidy") |>
    filter(term != "(Intercept)") |>
    mutate(
      decision = vapply(term, match_decision, character(1)),
      decision_label = strip_dim_prefix(decision, dim_prefix = dim_prefix),
      option = substring(term, nchar(decision) + 1),
      option = if_else(option == "", decision_label, option)
    )
}

calc_regression_importance <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  calc_regression(mv, colname_metric, dim_prefix = dim_prefix) |>
    tidy_regression_coefficients(dim_prefix = dim_prefix) |>
    group_by(decision) |>
    # One might argue for sum, mean or max here
    summarise(importance = mean(abs(estimate)), .groups = "drop") |>
    arrange(desc(importance)) |>
    deframe()
}
