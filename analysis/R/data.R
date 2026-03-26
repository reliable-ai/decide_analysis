dir_data <- "data"
dir_multiverse_results <- here(dir_data, "multiverse_results")

load_multiverse <- function (name, dim_prefix = "mv_dim_") {
  path <- here(dir_multiverse_results, paste0(name, ".csv.gz"))

  df <- read_csv(path)

  df <- df |>
    mutate(across(starts_with(dim_prefix), as.factor))

  df
}
