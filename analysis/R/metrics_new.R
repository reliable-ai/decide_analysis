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

# In the Python implementation, functional dependence is handled within the
# `organize_multiverse_results` function, which is called on each multiverse.
# Since the results in the paper are from the R code, and the R code base does
# not utilize the `organize_multiverse_results` function (at least not now), we
# fix this case using this helper function which will be called by both
# `load_multiverse` (so that every importance method, e.g., regression, fANOVA)
# sees the same judgment calls (and comparisons are fair), and `decide`, so that
# DECIDE behaves the same regardless of how it is called.
#
# If the input is incorrectly formatted, we throw an error instead of returning
# bad importances. `colname_metric` is optional, since a loaded multiverse holds
# several metrics, some of which may legitimately be missing.
#
# If the choice for judgment call i fully determines the choice for judgment
# call j, then j never varies on its own, so its importance can't be separated
# from i's. Since i's column already encodes j's choice, we merge the two by
# dropping j, and warn the user in case they were not aware of this.
check_and_merge_decisions <- function (mv, colname_metric = NULL,
                                       dim_prefix = "mv_dim_") {
  
  # get the decisions by getting cols starting with prefix
  dims <- mv |> select(starts_with(dim_prefix)) |> colnames()

  # if the input is incorrectly formatted or has some sort of sparsity that
  # makes it impossible to accurately estimate, then we want to throw an error
  # instead of returning bad importances.
  missing_choices <- dims[vapply(mv[dims], anyNA, logical(1))]
  if (length(missing_choices) > 0) {
    stop(
      "Judgment call(s) ", paste(missing_choices, collapse = ", "),
      " contain NA values; encode them as an explicit option instead.",
      call. = FALSE
    )
  }
  if (!is.null(colname_metric) && !all(is.finite(mv[[colname_metric]]))) {
    stop(
      "Performance metric '", colname_metric, "' contains NA or infinite ",
      "values (e.g. failed runs); drop those universes first.",
      call. = FALSE
    )
  }
  num_duplicates <- sum(duplicated(mv[dims]))
  if (num_duplicates > 0) {
    stop(
      num_duplicates, " universe(s) appear more than once (same choices for ",
      "every judgment call); aggregate them first (e.g. over seeds).",
      call. = FALSE
    )
  }

  # if the multiverse is such that the option (singular) available at the jth
  # decision is a deterministic function of the choice made at the ith
  # decision, this means that the ith decision never varies on its own, so its
  # importance is not identifiable since it can't be separated from i. Since
  # the choice for the ith decision is encoded in the choice at i, we can drop
  # the column corresponding to the choice made for decision j. We will give
  # the user a warning in case they were not familiar that this was happening
  # in their multiverse.
  for (j in dims) {
    # if there is only one option across all universes, it is not a decision
    if (n_distinct(mv[[j]]) < 2) {
      stop(
        "Judgment call '", j, "' has only one option, so it is not a valid ",
        "decision; remove it from the multiverse.",
        call. = FALSE
      )
    }
    for (i in setdiff(dims, j)) {
      # j is a function of i exactly when each option of i co-occurs with only
      # one option of j, i.e. there are as many (i, j) pairs as options of i
      if (nrow(distinct(mv[c(i, j)])) == n_distinct(mv[[i]])) {
        warning(
          "Judgment call '", j, "' is fully determined by '", i, "', so it ",
          "will be merged into '", i, "' and dropped as a separate decision.",
          call. = FALSE
        )
        mv <- mv |> select(-all_of(j))
        dims <- setdiff(dims, j)
        break # since j is removed, stop searching over it
      }
    }
  }

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
decide <- function (
  mv,
  colname_metric,
  max_order = 1,
  spread = pop_var,
  summary = mean,
  report_all = FALSE,
  dim_prefix = "mv_dim_"
) {

  # fix sparsity from functional dependence by merging decisions, if applicable
  mv <- check_and_merge_decisions(mv, colname_metric, dim_prefix = dim_prefix)
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

  total_spread <- spread(mv[[colname_metric]])

  results <- tibble(
    dimension = subsets |> unlist(),
    decide_total = unname(total_effect),
    decide_main = unname(main_effect),
    decide_interactions = unname(interaction_effect),

    ratio_main = decide_main / decide_total,
    ratio_interactions = interaction_effect / decide_total,
    total_spread = total_spread
  )

  # Default scores to report
  main_scores <- c(
    "dimension",
    "decide_total",
    "decide_main",
    "ratio_main"
  )
  if (!report_all) {
    # If report_all isn't set, report only the most important scores
    results <- results |>
      select(all_of(main_scores))
  }

  # Only report share_var_total if its assumptions are met
  # i.e. summary function is mean, spread function is var()
  if (identical(summary, mean) && (identical(spread, pop_var) || identical(spread, var))) {
    results$share_var_total <- results$decide_total / total_spread
  }

  return(
    results |>
      arrange(desc(decide_total))
  )
}

# Order-1 decide_total from decide(), as a named numeric vector keyed by
# dimension name. A drop-in replacement for the old (sample-variance-based)
# calc_between_bucket_variation() wherever a single importance-per-decision
# vector is expected, e.g. vis_importance(), vis_importance_2dim(),
# aggregate_onehot_importances(), or the ablation pipeline in R/ablation.R.
decide_vec <- function (mv, colname_metric, dim_prefix = "mv_dim_",
                        spread = pop_var, summary = mean) {
  decide(
    mv, colname_metric,
    max_order = 1, spread = spread, summary = summary, dim_prefix = dim_prefix
  ) |>
    (\(tbl) setNames(tbl$decide_total, tbl$dimension))()
}
