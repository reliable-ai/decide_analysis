dir_data <- "data"
dir_multiverse_results <- here(dir_data, "multiverse_results")

load_multiverse <- function (name) {
  path <- here(dir_multiverse_results, paste0(name, ".csv.gz"))

  read_csv(path)
}
