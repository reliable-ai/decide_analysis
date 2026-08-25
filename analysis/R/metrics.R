# R version of src/metrics/metrics.py.
#
# This file defines the metrics for assessing the downstream impact of judgment
# calls in the multiverse. The supported decision importance measures are:

# - Naive tree-based importance. This measure, which can be thought of as "within-
# bucket" variation, measures the decrease in downstream spread caused by each
# judgment call. When used with mean and variance as the summary statistics, this
# metric is equivalent to mean decrease in impurity.
# - DECIDE. This measure leverages multiverse structure by comparing universes
# which differ only in particular decisions. By measuring the dispersion of each
# comparable set (i.e., the universes which only differ in a particular decision),
# we can attribute the variation in the downstream results to that decision.
# This measure can be thought of as "between-bucket" variation.

# Where the Python version tags columns as "dimension"/"performance_metric" with
# a MultiIndex, this port uses the `dim_prefix` convention of the surrounding R
# code: judgment call columns are those whose name starts with `dim_prefix`, in
# chronological order.

# Population variance, i.e. numpy's np.var(ddof = 0), which is the dispersion
# used throughout metrics.py (base R's var() is the sample variance).
pop_var <- function (x) {
  return(mean((x - mean(x))^2))
}

# Order the judgment calls chronologically and subset the results to the
# columns that apply for our analysis. Judgment call columns are renamed to
# carry `dim_prefix` if they do not already, which is how this port marks a
# column as a dimension rather than a performance metric.
organize_multiverse_results <- function (mv, dimension_order, performance_metrics,
                                         dim_prefix = "mv_dim_") {
  mv <- mv |> select(all_of(c(dimension_order, performance_metrics)))

  names(mv)[seq_along(dimension_order)] <- if_else(
    startsWith(dimension_order, dim_prefix),
    dimension_order,
    paste0(dim_prefix, dimension_order)
  )

  return(mv)
}

# Mean decrease in within-bucket variation for each judgment call. Because the
# judgment calls are ordered chronologically, the buckets at depth d of the
# decision tree are the combinations of the first d judgment calls: the decision
# taken at depth d is credited with the drop in variance from each bucket at
# depth d to each of its children at depth d + 1. At the last split the children
# are leaves, so the whole remaining variance is credited to that decision.
#
# Returns a named numeric vector, keyed by dimension name.
naive_tree_based_importance <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  dims <- mv |> select(starts_with(dim_prefix)) |> colnames()
  n_dims <- length(dims)

  # variance of the metric within each bucket at the given tree depth
  # (depth 0 is the root, i.e. a single bucket holding every universe)
  bucket_var <- function (depth) {
    return(
      mv |>
        group_by(across(all_of(dims[seq_len(depth)]))) |>
        summarise(v = pop_var(.data[[colname_metric]]), .groups = "drop")
    )
  }

  decreases <- setNames(numeric(n_dims), dims)

  for (depth in seq_len(n_dims) - 1) {
    parents <- bucket_var(depth)

    if (depth + 1 == n_dims) {
      # last split: no further splits to compare against, so the decrease in
      # variance is just the variance of the current bucket
      decreases[depth + 1] <- mean(parents$v)
      next
    }

    children <- bucket_var(depth + 1)
    children$v_parent <- if (depth == 0) {
      parents$v # every child descends from the single root bucket
    } else {
      children |>
        left_join(parents, by = dims[seq_len(depth)], suffix = c("", "_parent")) |>
        pull(v_parent)
    }

    decreases[depth + 1] <- mean(children$v_parent - children$v)
  }

  return(decreases)
}

# DECIDE decomposition of a multiverse.
#
# For every non-empty subset S of judgment calls with |S| <= max_order, this
# reports how much of the variation in the performance metric is attributable to
# S. This works for both full-factorial (balanced) multiverses and for
# irregular/ragged ones (e.g., where a judgment call only unlocks certain
# choices conditional on an upstream decision).
#
# Dispersion and aggregation are supplied as the generalized spread function Phi
# (`spread`) and summary function Lambda (`summary`); each takes a numeric vector
# of outcomes and returns a single value. With the defaults (Phi = population
# variance, Lambda = mean) the quantities below reduce to the usual
# (unnormalized) Sobol' indices. Note that `summary` shadows base::summary
# inside this function; the names mirror the Python implementation.
#
# Three quantities are reported per subset S:
#   main_effect         GME(S) = Phi_{s_S}( Lambda_{p_{-S}}(f)): the "closed"
#                       first-to-|S|-order effect of S -- how much the summarised
#                       outcome moves as S's choices vary, aggregating over
#                       everything else. (Var(E[Y|X_S]) by default.)
#   total_effect        DECIDE(S) = Lambda_{p_{-S}}(Phi(comparable set)): the
#                       total effect of S -- the spread across S's choices within
#                       each fixed background context, aggregated over contexts
#                       (with an average-case counterfactual imputed for choices
#                       of S that a context never realised).
#                       (E[Var(Y|X_{-S})] by default.)
#   interaction_effect  the pure marginal (Sobol / functional-ANOVA) interaction
#                       of exactly S, obtained by stripping the lower-order
#                       effects out of main_effect:
#                       interaction_effect(S) = main_effect(S)
#                         - sum over proper subsets T of S of interaction(T).
#                       For |S| == 1 this is identical to main_effect, so it is
#                       reported as NA for singletons (main_effect already
#                       reports it) and filled in only for |S| >= 2. This
#                       decomposition relies on the additivity of variance, so it
#                       is exact only for Phi = variance / Lambda = mean and is a
#                       heuristic for other spread functions. On a ragged tree the
#                       identity total = main + interaction likewise only holds
#                       approximately, since some values are imputed.
#
# `max_order` defaults to 1 (main + total effect for each single judgment call);
# pass a larger value, or NULL for the full power set, to also get interaction
# effects up to that order.
#
# Returns a tibble with one row per subset and columns `dimensions` (a
# list-column of dimension names), `order`, `var_total`, `main_effect`,
# `total_effect` and `interaction_effect`, the last of which is NA for subsets
# with |S| == 1 (see interaction_effect above).
decide <- function (mv, colname_metric, max_order = 1, spread = pop_var,
                    summary = mean, dim_prefix = "mv_dim_") {
  dims <- mv |> select(starts_with(dim_prefix)) |> colnames()

  if (is.null(max_order)) max_order <- length(dims)

  # every non-empty subset of the judgment calls, smallest first
  subsets <- unlist(
    lapply(seq_len(max_order), \(size) combn(dims, size, simplify = FALSE)),
    recursive = FALSE
  )
  subset_key <- \(target_dims) paste(target_dims, collapse = "\r")
  keys <- vapply(subsets, subset_key, character(1))

  # Lambda applied within each group formed by `cols`, returning one summary
  # value per group
  summarize_groups <- function (cols) {
    return(
      mv |>
        group_by(across(all_of(cols))) |>
        summarise(v = summary(.data[[colname_metric]]), .groups = "drop")
    )
  }

  # --- main effects: Phi_{s_S}( Lambda_{p_{-S}}( f ) ) for every subset ---
  main_effect <- setNames(
    vapply(subsets, \(target_dims) spread(summarize_groups(target_dims)$v), numeric(1)),
    keys
  )

  # --- pure marginal (Sobol) interaction ---
  # interaction_effect(S) = main_effect(S) - sum over proper subsets T of S of
  # interaction_effect(T). Because every proper subset of an S with
  # |S| <= max_order is itself enumerated above, this is always well-defined.
  interaction_effect <- setNames(numeric(length(subsets)), keys)
  for (i in seq_along(subsets)) {
    lower <- unlist(lapply(
      seq_len(length(subsets[[i]]) - 1),
      \(r) vapply(combn(subsets[[i]], r, simplify = FALSE), subset_key, character(1))
    ))
    interaction_effect[i] <- main_effect[i] - sum(interaction_effect[lower])
  }

  # --- total effects: ragged-tree safe total effect of every subset ---
  total_effect <- vapply(subsets, function (target_dims) {
    other_dims <- setdiff(dims, target_dims)

    if (length(other_dims) == 0) {
      # target_dims covers every decision: one background context (the whole
      # multiverse), every combination of target_dims is real
      return(spread(mv[[colname_metric]]))
    }

    # average-case counterfactual for every combination of target_dims' choices
    # that occurs anywhere in the multiverse: Lambda over the rest of the
    # pipeline, unconditioned on anything else. This also defines the full
    # comparable-set space -- combinations that never occur anywhere are not
    # considered, since there is no data to ground them in.
    imputed <- summarize_groups(target_dims) |> rename(v_imputed = v)

    # one realised outcome per (background context, combination of target_dims);
    # on duplicates the last one wins, as when building a dict in Python
    realised <- mv |> select(all_of(c(other_dims, target_dims)), v = all_of(colname_metric))
    realised <- realised[!duplicated(realised[c(other_dims, target_dims)], fromLast = TRUE), ]

    contexts <- mv |> select(all_of(other_dims)) |> distinct()

    # each background context gets a full comparable set, imputing the
    # average-case outcome wherever that context never realised a combination
    phi <- expand_grid(contexts, imputed |> select(all_of(target_dims))) |>
      left_join(realised, by = c(other_dims, target_dims)) |>
      left_join(imputed, by = target_dims) |>
      mutate(v = coalesce(v, v_imputed)) |>
      group_by(across(all_of(other_dims))) |>
      summarise(phi = spread(v), .groups = "drop")

    # aggregate the per-context spreads with Lambda (equal weight per background
    # context by default)
    return(summary(phi$phi))
  }, numeric(1))

  var_total <- spread(mv[[colname_metric]])

  return(tibble(
    dimensions = subsets |> unlist(),
    total_effect = unname(total_effect),
    main_effect = unname(main_effect),
    ratio_total_var = total_effect / var_total,
    ratio_main = main_effect / total_effect,
    # var_total is the same scalar for every subset (total spread of outcomes)
    var_total = var_total
  ) |>
    arrange(desc(total_effect))
  )
}
