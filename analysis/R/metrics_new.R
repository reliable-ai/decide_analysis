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
#                       everything else. (Var(E[Y|X_S]) by default.) Universes in
#                       background contexts that are left out of total_effect
#                       (see exclude_inert and conditional_decisions) are left out
#                       here too, so that both are computed over the same
#                       universes.
#   total_effect        DECIDE(S) = Lambda_{p_{-S}}(Phi(comparable set)): the
#                       total effect of S -- the spread across S's choices within
#                       each fixed background context, aggregated over contexts.
#                       A choice of S that a context never realised is imputed
#                       with its matched average-case counterfactual: Lambda over
#                       the universes taking that choice which agree with the
#                       context on as many other judgment calls as possible.
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
# `exclude_inert`: some decisions do not apply in certain backgrounds but are
# still listed there, so all of their options give identical results (e.g. in
# YRBS, combination when y_variable is a singleton). Identical results can also
# happen by coincidence when the decision does apply (e.g. with discrete
# outcomes), so by default (FALSE) these backgrounds are kept as zeros and only
# reported through `inert_share`. Set to TRUE to calculate the importances
# (total and main) only over the backgrounds where the decision applies.
#
# `conditional_decisions`: judgment calls that only apply when other judgment
# calls take certain options, as a named list mapping each such judgment call to
# a named list of {other judgment call = options where it applies}. E.g. in MTF,
# y_variable only varies for 5 of the 13 x_variables, so
# list(mv_dim_y_variable = list(mv_dim_x_variable = c(<those 5 options>)))
# declares that y_variable does not apply for the other 8. Background contexts
# where a declared judgment call does not apply are left out of its importances
# (total and main) instead of being compared against imputed counterfactuals.
# Several conditions for one judgment call must all hold. For a subset S of
# several judgment calls, a background is left out only if none of S's judgment
# calls apply there; a declaration whose condition involves a judgment call in S
# is ignored for S, since S's options are then compared jointly.
#
# Besides the scores, the result reports `applicability_share`, the proportion
# of background contexts included in decide_total (left out are inert
# backgrounds if exclude_inert = TRUE, and backgrounds where a declared
# conditional decision does not apply; decide_total is NaN when it is 0), and
# `inert_share`, the proportion of background contexts where all options give
# identical results. With Lambda = mean, decide_total * applicability_share
# equals decide_total with the left-out backgrounds counted as zero.
#
# Returns a tibble with one row per subset and columns `dimension` (the judgment
# call's name, or the names of a subset's judgment calls joined with " + "),
# `decide_total`, `decide_main`, `ratio_main`, `applicability_share` and
# `inert_share`, plus `share_var_total` when Phi = variance and Lambda = mean.
# With `report_all = TRUE` it also includes `decide_interactions`,
# `ratio_interactions` and `total_spread`.
decide <- function (
  mv,
  colname_metric,
  max_order = 1,
  spread = pop_var,
  summary = mean,
  report_all = FALSE,
  dim_prefix = "mv_dim_",
  exclude_inert = FALSE,
  conditional_decisions = NULL
) {

  # fix sparsity from functional dependence by merging decisions, if applicable
  mv <- check_and_merge_decisions(mv, colname_metric, dim_prefix = dim_prefix)
  dims <- mv |> select(starts_with(dim_prefix)) |> colnames()

  if (is.null(max_order)) max_order <- length(dims)

  # judgment calls that only apply when other judgment calls take certain
  # options (declared by the user, see conditional_decisions above). for each,
  # record whether it applies in every universe
  if (is.null(conditional_decisions)) conditional_decisions <- list()
  applies_in_universe <- list()
  for (decision in names(conditional_decisions)) {
    conditions <- conditional_decisions[[decision]]
    for (name in c(decision, names(conditions))) {
      if (!name %in% dims) {
        stop(
          "conditional_decisions refers to judgment call '", name, "', which ",
          "is not in the multiverse (it may have been merged into another ",
          "judgment call by check_and_merge_decisions()).",
          call. = FALSE
        )
      }
    }
    for (condition_dim in names(conditions)) {
      never_occur <- setdiff(
        as.character(conditions[[condition_dim]]),
        as.character(unique(mv[[condition_dim]]))
      )
      if (length(never_occur) > 0) {
        stop(
          "conditional_decisions: option(s) ", paste(never_occur, collapse = ", "),
          " never occur for judgment call '", condition_dim, "'.",
          call. = FALSE
        )
      }
    }
    applies_in_universe[[decision]] <- Reduce(`&`, lapply(
      names(conditions),
      \(c) as.character(mv[[c]]) %in% as.character(conditions[[c]])
    ))
  }

  # every non-empty subset of the judgment calls, smallest first
  subsets <- unlist(
    lapply(seq_len(max_order), \(size) combn(dims, size, simplify = FALSE)),
    recursive = FALSE
  )
  subset_key <- \(target_dims) paste(target_dims, collapse = "\r")
  keys <- vapply(subsets, subset_key, character(1))

  # Lambda applied within each group formed by `cols`, over the universes marked
  # in the logical vector `used` (all universes by default), returning one
  # summary value per group
  summarize_groups <- function (cols, used = NULL) {
    data <- if (is.null(used)) mv else mv[used, ]
    return(
      data |>
        group_by(across(all_of(cols))) |>
        summarise(v = summary(.data[[colname_metric]]), .groups = "drop")
    )
  }

  # --- total effects: sparse-multiverse-safe total effect of every subset ---
  # each subset gets its total effect and the proportions of background contexts
  # that were included in it (applicability_share) and that are inert
  # (inert_share; see exclude_inert)
  total_results <- lapply(subsets, function (target_dims) {
    other_dims <- setdiff(dims, target_dims)

    if (length(other_dims) == 0) {
      # target_dims covers every decision: one background context (the whole
      # multiverse), every combination of target_dims is real
      return(list(
        total = spread(mv[[colname_metric]]),
        applicability_share = 1,
        inert_share = as.numeric(n_distinct(mv[[colname_metric]]) == 1),
        used = rep(TRUE, nrow(mv))
      ))
    }

    # every combination of target_dims' choices that occurs anywhere in the
    # multiverse defines the full comparable-set space -- combinations that
    # never occur anywhere are not considered, since there is no data to ground
    # them in. global_means (Lambda over every universe taking a combination) is
    # the fallback counterfactual when nothing else about the background can be
    # matched.
    global_means <- summarize_groups(target_dims) |> rename(v_global = v)
    combos <- global_means |> select(all_of(target_dims))

    # one realised outcome per (background context, combination of target_dims);
    # on duplicates the last one wins, as when building a dict in Python
    realised <- mv |> select(all_of(c(other_dims, target_dims)), v = all_of(colname_metric))
    realised <- realised[!duplicated(realised[c(other_dims, target_dims)], fromLast = TRUE), ]

    contexts <- mv |> select(all_of(other_dims)) |> distinct()

    # sparsity handling in case different options exist depending on the
    # background: a combination of target_dims that a background never
    # realised is filled in with its matched average-case counterfactual --
    # Lambda over the universes taking that combination which agree with the
    # background on as many of the other judgment calls as possible, averaging
    # only over the ones that block the comparison. E.g. with the universe
    # (c1=1, c2=1, c3=0) and no c3=0 anywhere else, its counterpart for c2=2 is
    # the average of (c1=1, c2=2, c3=x). If several equally large sets of
    # judgment calls can be matched, their universes are pooled. This does not
    # depend on the order of the judgment calls.
    #
    # All missing (background, combination) cells are matched at once, level by
    # level: first on all but one of the other judgment calls, then on one
    # fewer, and so on. A cell is resolved at the first level where any
    # universes match it, and the matches of every way of choosing that many
    # judgment calls are pooled before applying Lambda.
    missing <- expand_grid(contexts, combos) |>
      anti_join(realised, by = c(other_dims, target_dims)) |>
      mutate(.cell = row_number())
    matched <- tibble(.cell = integer(), v_matched = numeric())
    unresolved <- missing
    for (num_matched in rev(seq_len(length(other_dims) - 1))) {
      # loop thru to find closest matching universes
      if (nrow(unresolved) == 0) break
      hits <- bind_rows(lapply(
        combn(other_dims, num_matched, simplify = FALSE),
        function (matched_dims) {
          unresolved |>
            select(.cell, all_of(c(target_dims, matched_dims))) |>
            inner_join(
              mv |> select(all_of(c(target_dims, matched_dims)), v = all_of(colname_metric)),
              by = c(target_dims, matched_dims),
              relationship = "many-to-many"
            ) |>
            select(.cell, v)
        }
      ))
      if (nrow(hits) == 0) next
      resolved <- hits |>
        group_by(.cell) |>
        summarise(v_matched = summary(v), .groups = "drop")
      matched <- bind_rows(matched, resolved)
      unresolved <- unresolved |> filter(!.cell %in% resolved$.cell)
    }
    # nothing about the background can be matched: fall back to the global value
    filled <- missing |>
      left_join(matched, by = ".cell") |>
      left_join(global_means, by = target_dims) |>
      mutate(v_filled = coalesce(v_matched, v_global)) |>
      select(all_of(c(other_dims, target_dims)), v_filled)

    # each background context gets a full comparable set: its realised outcomes,
    # plus the matched counterfactuals for the combinations it never realised
    phi <- expand_grid(contexts, combos) |>
      left_join(realised, by = c(other_dims, target_dims)) |>
      left_join(filled, by = c(other_dims, target_dims)) |>
      mutate(v = coalesce(v, v_filled)) |>
      group_by(across(all_of(other_dims))) |>
      summarise(phi = spread(v), .groups = "drop")

    # This addresses the case where the decision doesn't apply in some
    # backgrounds, but is still listed there (thus, there is no difference in
    # the downstream results across its options): a background where
    # target_dims has at least two options listed, but they all give the same
    # result. This can also happen by coincidence if a decision just doesn't
    # matter, so we only report this proportion by default, and leave these
    # backgrounds out if the user asks to exclude them (recommended if they
    # know a priori that the decision doesn't apply in some backgrounds).
    inert <- realised |>
      group_by(across(all_of(other_dims))) |>
      summarise(inert = n() >= 2 & n_distinct(v) == 1, .groups = "drop")
    phi <- phi |> left_join(inert, by = other_dims)
    included <- if (exclude_inert) !phi$inert else rep(TRUE, nrow(phi))

    # This addresses the case where a judgment call was declared to only apply
    # when other judgment calls take certain options (see conditional_decisions):
    # backgrounds where it does not apply are left out rather than compared
    # against imputed counterfactuals. S applies wherever at least one of its
    # judgment calls does; undeclared judgment calls always apply, and a
    # declaration whose condition involves a judgment call in S is ignored, since
    # S's options are then compared jointly. The result is constant within a
    # background context, since every condition left refers only to judgment
    # calls that the background fixes.
    s_applies <- rep(FALSE, nrow(mv))
    for (d in target_dims) {
      conditions <- conditional_decisions[[d]]
      if (is.null(conditions) || any(names(conditions) %in% target_dims)) {
        s_applies[] <- TRUE
        break
      }
      s_applies <- s_applies | applies_in_universe[[d]]
    }
    declared <- mv |>
      select(all_of(other_dims)) |>
      mutate(.applies = s_applies) |>
      distinct(across(all_of(other_dims)), .keep_all = TRUE)
    phi <- phi |> left_join(declared, by = other_dims)
    included <- included & phi$.applies

    # the universes of the included backgrounds, which the main effect is also
    # computed over
    used <- (
      mv |>
        select(all_of(other_dims)) |>
        left_join(
          phi |> mutate(.used = included) |> select(all_of(other_dims), .used),
          by = other_dims
        )
    )$.used

    shares <- list(
      applicability_share = mean(included),
      inert_share = mean(phi$inert),
      used = used
    )

    if (!any(included)) {
      # target_dims does not apply in any background, so there is nothing to
      # estimate; refuse rather than guess
      warning(
        "total_effect for ", paste(target_dims, collapse = ", "), " is not ",
        "estimable: it does not apply in any background context (all are ",
        "inert with exclude_inert = TRUE, or declared not to apply in ",
        "conditional_decisions), so it is reported as NaN.",
        call. = FALSE
      )
      return(c(list(total = NaN), shares))
    }

    # among the included backgrounds, count the combinations of target_dims that
    # were filled in rather than realised
    num_imputed <- missing |>
      semi_join(phi[included, other_dims], by = other_dims) |>
      nrow()
    if (num_imputed > 0) {
      # the multiverse is sparse for this specific subset: at least one
      # background context was missing a real outcome for one of target_dims'
      # choices, so total_effect partly relies on matched average-case
      # counterfactuals rather than purely observed adjacent universes. This
      # also means total_effect ~= main_effect + interaction_effect only holds
      # approximately for this subset.
      warning(
        "total_effect for ", paste(target_dims, collapse = ", "), " used ",
        num_imputed, " imputed average-case counterfactual value(s) across ",
        sum(included), " background contexts (multiverse is ragged for this ",
        "subset). total_effect ~= main_effect + interaction_effect will only ",
        "hold approximately here.",
        call. = FALSE
      )
    }

    # aggregate the per-context spreads of the included backgrounds with Lambda
    # (each included background context contributes one value)
    return(c(list(total = summary(phi$phi[included])), shares))
  })
  total_effect <- vapply(total_results, \(r) r$total, numeric(1))
  applicability_share <- vapply(total_results, \(r) r$applicability_share, numeric(1))
  inert_share <- vapply(total_results, \(r) r$inert_share, numeric(1))

  # --- main effects: Phi_{s_S}( Lambda_{p_{-S}}( f ) ) for every subset ---
  # computed over the same universes as the total effect, i.e. leaving out the
  # background contexts where S does not apply (see the total effects above)
  main_effect <- setNames(
    vapply(seq_along(subsets), function (k) {
      used <- total_results[[k]]$used
      if (!any(used)) return(NaN)
      spread(summarize_groups(subsets[[k]], used)$v)
    }, numeric(1)),
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

  total_spread <- spread(mv[[colname_metric]])

  results <- tibble(
    # one label per subset; for subsets of several judgment calls, their names
    # joined with " + " (single judgment calls keep their plain name)
    dimension = vapply(subsets, \(target_dims) paste(target_dims, collapse = " + "), character(1)),
    decide_total = unname(total_effect),
    decide_main = unname(main_effect),
    decide_interactions = unname(interaction_effect),

    ratio_main = decide_main / decide_total,
    ratio_interactions = interaction_effect / decide_total,
    total_spread = total_spread,

    applicability_share = applicability_share,
    inert_share = inert_share
  )

  # Default scores to report
  main_scores <- c(
    "dimension",
    "decide_total",
    "decide_main",
    "ratio_main",
    "applicability_share",
    "inert_share"
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
                        spread = pop_var, summary = mean, exclude_inert = FALSE,
                        conditional_decisions = NULL) {
  decide(
    mv, colname_metric,
    max_order = 1, spread = spread, summary = summary, dim_prefix = dim_prefix,
    exclude_inert = exclude_inert, conditional_decisions = conditional_decisions
  ) |>
    (\(tbl) setNames(tbl$decide_total, tbl$dimension))()
}
