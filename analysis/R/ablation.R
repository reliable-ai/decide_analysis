calc_fanova_main_effects <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  calc_fanova(mv, colname_metric, dim_prefix = dim_prefix) |>
    filter(is.na(level_1)) |>
    fanova_to_vec()
}

tidy_importance_methods <- function (importance_by_method, dim_prefix = "mv_dim_") {
  purrr::imap_dfr(
    importance_by_method,
    function (importance, method_name) {
      tibble(
        method = method_name,
        target_decision = names(importance),
        target_decision_label = strip_dim_prefix(names(importance), dim_prefix = dim_prefix),
        importance = unname(importance)
      )
    }
  )
}

calc_importance_methods <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  list(
    regression = calc_regression_importance(mv, colname_metric, dim_prefix = dim_prefix),
    fanova = calc_fanova_main_effects(mv, colname_metric, dim_prefix = dim_prefix),
    within = calc_within_bucket_variation(mv, colname_metric, dim_prefix = dim_prefix),
    between = calc_between_bucket_variation(mv, colname_metric, dim_prefix = dim_prefix)
  )
}

safe_mean <- function (x) {
  if (length(x) == 0 || all(is.na(x))) {
    return(NA_real_)
  }

  mean(x, na.rm = TRUE)
}

safe_min <- function (x) {
  if (length(x) == 0 || all(is.na(x))) {
    return(NA_real_)
  }

  min(x, na.rm = TRUE)
}

safe_cor <- function (x, y, method = "spearman") {
  keep <- complete.cases(x, y)
  x <- x[keep]
  y <- y[keep]

  if (length(x) < 2 || dplyr::n_distinct(x) < 2 || dplyr::n_distinct(y) < 2) {
    return(NA_real_)
  }

  suppressWarnings(cor(x, y, method = method))
}

fix_decision <- function (mv, fixed_decision, fixed_option, dim_prefix = "mv_dim_") {
  mv |>
    filter(as.character(.data[[fixed_decision]]) == fixed_option) |>
    remove_fake_decisions(dim_prefix = dim_prefix)
}

build_ablation_grid <- function (mv, dim_prefix = "mv_dim_") {
  dim_cols <- mv |>
    select(starts_with(dim_prefix)) |>
    colnames()

  purrr::map_dfr(
    dim_cols,
    function (fixed_decision) {
      tibble(
        fixed_decision = fixed_decision,
        fixed_decision_label = strip_dim_prefix(fixed_decision, dim_prefix = dim_prefix),
        fixed_option = unique(as.character(mv[[fixed_decision]]))
      )
    }
  )
}

calc_ablation_importance <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  ablation_grid <- build_ablation_grid(mv, dim_prefix = dim_prefix)

  purrr::pmap_dfr(
    ablation_grid,
    function (fixed_decision, fixed_decision_label, fixed_option) {
      ablated_mv <- fix_decision(
        mv,
        fixed_decision = fixed_decision,
        fixed_option = fixed_option,
        dim_prefix = dim_prefix
      )

      tidy_importance_methods(
        calc_importance_methods(
          ablated_mv,
          colname_metric = colname_metric,
          dim_prefix = dim_prefix
        ),
        dim_prefix = dim_prefix
      ) |>
        mutate(
          fixed_decision = fixed_decision,
          fixed_decision_label = fixed_decision_label,
          fixed_option = fixed_option,
          n_universes = nrow(ablated_mv)
        ) |>
        select(
          fixed_decision,
          fixed_decision_label,
          fixed_option,
          method,
          target_decision,
          target_decision_label,
          importance,
          n_universes
        )
    }
  )
}

# Compares importance rankings between every pair of methods.
# For each (fixed_decision, fixed_option), it correlates method-specific
# importance vectors across target decisions after pivoting to wide format.
# The reported rank_correlation is Spearman by default.
calc_method_stability <- function (importance_tbl, cor_method = "spearman") {
  methods <- unique(importance_tbl$method)
  method_pairs <- combn(methods, 2, simplify = FALSE)

  purrr::map_dfr(
    method_pairs,
    function (method_pair) {
      wide <- importance_tbl |>
        filter(method %in% method_pair) |>
        select(fixed_decision, fixed_option, target_decision, method, importance) |>
        tidyr::pivot_wider(names_from = method, values_from = importance)

      wide |>
        group_by(fixed_decision, fixed_option) |>
        summarise(
          method_x = method_pair[[1]],
          method_y = method_pair[[2]],
          rank_correlation = safe_cor(
            .data[[method_pair[[1]]]],
            .data[[method_pair[[2]]]],
            method = cor_method
          ),
          mean_abs_difference = mean(
            abs(.data[[method_pair[[1]]]] - .data[[method_pair[[2]]]]),
            na.rm = TRUE
          ),
          n_target_decisions = sum(complete.cases(.data[[method_pair[[1]]]], .data[[method_pair[[2]]]])),
          .groups = "drop"
        )
    }
  )
}

summarise_method_stability <- function (method_stability_tbl, dim_prefix = "mv_dim_") {
  method_stability_tbl |>
    group_by(fixed_decision, method_x, method_y) |>
    summarise(
      fixed_decision_label = strip_dim_prefix(first(fixed_decision), dim_prefix = dim_prefix),
      mean_rank_correlation = safe_mean(rank_correlation),
      min_rank_correlation = safe_min(rank_correlation),
      mean_abs_difference = safe_mean(mean_abs_difference),
      n_options = n(),
      .groups = "drop"
    )
}

# Quantifies how much a method changes when switching between options of the
# same fixed decision. For each option pair, it correlates the two option-
# specific importance vectors across target decisions (Spearman by default).
calc_option_pair_changes <- function (ablation_tbl, cor_method = "spearman") {
  ablation_tbl |>
    group_by(fixed_decision, method) |>
    group_modify(
      ~ {
        # Compare every pair of options for this (fixed_decision, method) slice.
        options <- unique(.x$fixed_option)
        option_pairs <- combn(options, 2, simplify = FALSE)

        if (length(option_pairs) == 0) {
          return(tibble())
        }

        purrr::map_dfr(
          option_pairs,
          function (option_pair) {
            # Align both options by target_decision so pairwise deltas/correlations
            # are computed on matched importance entries.
            wide <- .x |>
              filter(fixed_option %in% option_pair) |>
              select(fixed_option, target_decision, importance) |>
              tidyr::pivot_wider(names_from = fixed_option, values_from = importance)

            tibble(
              option_x = option_pair[[1]],
              option_y = option_pair[[2]],
              mean_abs_change = mean(
                abs(wide[[option_pair[[1]]]] - wide[[option_pair[[2]]]]),
                na.rm = TRUE
              ),
              rank_correlation = safe_cor(
                wide[[option_pair[[1]]]],
                wide[[option_pair[[2]]]],
                method = cor_method
              ),
              n_target_decisions = sum(complete.cases(
                wide[[option_pair[[1]]]],
                wide[[option_pair[[2]]]]
              ))
            )
          }
        )
      }
    ) |>
    ungroup()
}

# Aggregates pairwise option-change statistics per decision and method, then
# joins baseline self-importance (importance of decision d on itself in the
# full multiverse) to support downstream association analyses.
summarise_option_sensitivity <- function (option_pair_changes, baseline_importance,
                                          dim_prefix = "mv_dim_") {
  # Keep only each method's self-importance for decision d (d -> d) in baseline.
  baseline_self <- baseline_importance |>
    select(method, target_decision, importance) |>
    rename(
      fixed_decision = target_decision,
      baseline_importance = importance
    )

  option_pair_changes |>
    # Average over all option pairs for each decision and method.
    group_by(fixed_decision, method) |>
    summarise(
      mean_pairwise_abs_change = safe_mean(mean_abs_change),
      mean_pairwise_rank_correlation = safe_mean(rank_correlation),
      n_option_pairs = n(),
      .groups = "drop"
    ) |>
    # Join baseline self-importance so we can compare "importance" vs "sensitivity".
    left_join(baseline_self, by = c("fixed_decision", "method")) |>
    mutate(
      fixed_decision_label = strip_dim_prefix(fixed_decision, dim_prefix = dim_prefix)
    ) |>
    select(
      fixed_decision,
      fixed_decision_label,
      method,
      baseline_importance,
      mean_pairwise_abs_change,
      mean_pairwise_rank_correlation,
      n_option_pairs
    )
}

# Tests whether decisions that look important in the full multiverse are also
# the ones that are more sensitive to option changes.
# Correlation is computed across decisions within each method.
summarise_predictive_relationship <- function (option_sensitivity_summary,
                                               cor_method = "spearman") {
  option_sensitivity_summary |>
    group_by(method) |>
    summarise(
      association = safe_cor(
        baseline_importance,
        mean_pairwise_abs_change,
        method = cor_method
      ),
      n_decisions = sum(complete.cases(baseline_importance, mean_pairwise_abs_change)),
      .groups = "drop"
    )
}

# End-to-end ablation pipeline:
# 1) compute baseline importance on the full multiverse,
# 2) recompute importance after fixing each decision to each option,
# 3) compare methods within each ablated setting,
# 4) summarize how option changes alter importance,
# 5) correlate baseline importance with option sensitivity.
run_ablation_analysis <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  # Baseline: importances computed on the full multiverse (no fixed decision).
  baseline_importance <- tidy_importance_methods(
    calc_importance_methods(mv, colname_metric = colname_metric, dim_prefix = dim_prefix),
    dim_prefix = dim_prefix
  )

  # Ablation: re-estimate importances after fixing each decision to each option.
  ablation_importance <- calc_ablation_importance(
    mv,
    colname_metric = colname_metric,
    dim_prefix = dim_prefix
  )

  # Add the full-multiverse baseline as a reference pseudo-setting so method
  # agreement is directly comparable to ablated settings.
  method_stability <- bind_rows(
    baseline_importance |>
      mutate(
        fixed_decision = "full_multiverse",
        fixed_decision_label = "full_multiverse",
        fixed_option = "all",
        n_universes = nrow(mv)
      ) |>
      select(
        fixed_decision,
        fixed_decision_label,
        fixed_option,
        method,
        target_decision,
        target_decision_label,
        importance,
        n_universes
      ),
    ablation_importance
  ) |>
    calc_method_stability()

  # Option-level perturbation diagnostics and summary statistics.
  option_pair_changes <- calc_option_pair_changes(ablation_importance)
  option_sensitivity <- summarise_option_sensitivity(
    option_pair_changes,
    baseline_importance = baseline_importance,
    dim_prefix = dim_prefix
  )

  list(
    baseline_importance = baseline_importance,
    ablation_importance = ablation_importance,
    method_stability = method_stability,
    method_stability_summary = summarise_method_stability(
      method_stability,
      dim_prefix = dim_prefix
    ),
    option_pair_changes = option_pair_changes,
    option_sensitivity = option_sensitivity,
    predictive_relationship = summarise_predictive_relationship(option_sensitivity)
  )
}
