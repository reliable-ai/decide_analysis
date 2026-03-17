# Note: Vibe-coded conversion from Python code; I don't trust these yet!

calc_within_bucket_variation <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  dims <- mv |> select(starts_with(dim_prefix)) |> colnames()
  n_dims <- length(dims)

  # Compute mean within-group variance at each depth.
  # mean_var[1] = total variance (depth 0, no grouping).
  # mean_var[d+1] = average variance when grouping by first d dimensions.
  mean_var <- numeric(n_dims)
  mean_var[1] <- var(mv[[colname_metric]])

  for (d in seq_len(n_dims - 1)) {
    mean_var[d + 1] <- mv |>
      group_by(across(all_of(dims[1:d]))) |>
      summarise(v = var(.data[[colname_metric]]), .groups = "drop") |>
      pull(v) |>
      mean()
  }

  # Mean decrease in variance at each depth. The last depth's decrease
  # is the remaining variance itself (no further splits).
  decreases <- c(mean_var[-n_dims] - mean_var[-1], mean_var[n_dims])
  names(decreases) <- dims

  decreases
}

calc_between_bucket_variation <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  dims <- mv |> select(starts_with(dim_prefix)) |> colnames()

  result <- setNames(numeric(length(dims)), dims)

  for (target_dim in dims) {
    other_dims <- setdiff(dims, target_dim)

    group_vars <- mv |>
      group_by(across(all_of(other_dims))) |>
      summarise(v = var(.data[[colname_metric]]), .groups = "drop")

    result[target_dim] <- mean(group_vars$v)
  }

  result
}
