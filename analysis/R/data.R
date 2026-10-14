dir_data <- "data"
dir_multiverse_results <- here(dir_data, "multiverse_results")

load_multiverse <- function (name, dim_prefix = "mv_dim_") {
  path <- here(dir_multiverse_results, paste0(name, ".csv.gz"))

  df <- read_csv(path)

  df <- df |>
    mutate(across(starts_with(dim_prefix), as.factor))

  # input checks and merging of determined judgment calls (see
  # check_and_merge_decisions() in metrics_new.R), so that every importance
  # method (DECIDE, regression, fANOVA) sees the same judgment calls
  # if unfair to also fix this issue for surrogates, comment out following line
  df <- check_and_merge_decisions(df, dim_prefix = dim_prefix)

  df
}
