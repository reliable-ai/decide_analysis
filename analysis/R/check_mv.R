# Check whether a multiverse is a full factorial design, i.e. whether every
# combination of judgment-call options is realised in the data. decide()'s
# total_effect handles ragged designs via imputation, but other metrics (e.g.
# calc_between_bucket_variation) assume a full design and will silently
# average over fewer contexts than intended if it isn't one.
check_full_design <- function (mv, dim_prefix = "mv_dim_") {
  dims <- mv |> select(starts_with(dim_prefix)) |> colnames()

  observed <- mv |> select(all_of(dims)) |> distinct()

  full_grid <- do.call(
    expand_grid,
    lapply(mv[dims], function (x) sort(unique(x)))
  )

  is_full <- nrow(observed) == nrow(full_grid)

  if (!is_full) {
    missing <- full_grid |> anti_join(observed, by = dims)
    pct_missing <- 100 * nrow(missing) / nrow(full_grid)

    by_dim <- summarize_missing_by_dim(mv, dims) |>
      filter(n_missing > 0) |>
      arrange(desc(pct_missing))

    message(
      sprintf(
        "Multiverse is not a full design: %d of %d possible combinations are realised (%d missing, %.1f%%).",
        nrow(observed), nrow(full_grid), nrow(missing), pct_missing
      ),
      "\nMissingness by decision (relative to contexts where the decision's other options do occur):\n",
      paste(utils::capture.output(print(by_dim)), collapse = "\n")
    )
  }

  invisible(is_full)
}

# For each dimension `d`, treats the other dimensions as a "context" and
# checks, among the contexts that occur at least once, what fraction of
# (context, option-of-d) cells never occur. This attributes raggedness to
# the decision(s) actually responsible for it, rather than just to whichever
# decision happens to be listed first in a fully-missing combination.
summarize_missing_by_dim <- function (mv, dims) {
  map_dfr(dims, function (d) {
    other_dims <- setdiff(dims, d)
    values <- sort(unique(mv[[d]]))

    full <- if (length(other_dims) == 0) {
      tibble(!!d := values)
    } else {
      mv |> select(all_of(other_dims)) |> distinct() |> crossing(!!d := values)
    }

    observed <- mv |> select(all_of(c(other_dims, d))) |> distinct()
    n_missing <- nrow(full) - nrow(observed)

    tibble(
      dimension = d,
      n_options = length(values),
      n_missing = n_missing,
      pct_missing = 100 * n_missing / nrow(full)
    )
  })
}
