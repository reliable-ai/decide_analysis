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
