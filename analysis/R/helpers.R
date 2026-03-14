get_multiverse_decisions <- function (mv, dim_prefix = "mv_dim_") {
  opts <- mv %>%
    select(starts_with(dim_prefix)) %>%
    lapply(unique)
  names(opts) <- sub(paste0("^", dim_prefix), "", names(opts))
  opts
}
