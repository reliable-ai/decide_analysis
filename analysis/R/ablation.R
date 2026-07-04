calc_fanova_main_effects <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  calc_fanova(mv, colname_metric, dim_prefix = dim_prefix, use_individual = TRUE) |>
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

# Default to using individual for better comparability
calc_importance_methods <- function (mv, colname_metric, dim_prefix = "mv_dim_", post_process_importances = NULL) {
  if (is.null(post_process_importances)) {
    post_process_importances = function (x) { return(x) }
  }

  list(
    regression = calc_regression_importance(mv, colname_metric, dim_prefix = dim_prefix) |>
      post_process_importances(),
    fanova = calc_fanova_main_effects(mv, colname_metric, dim_prefix = dim_prefix) |>
      post_process_importances(),
    within = calc_within_bucket_variation(mv, colname_metric, dim_prefix = dim_prefix) |>
      post_process_importances(),
    between = calc_between_bucket_variation(mv, colname_metric, dim_prefix = dim_prefix) |>
      post_process_importances()
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

calc_ablation_importance <- function (
  mv,
  colname_metric,
  dim_prefix = "mv_dim_",
  post_process_importances = NULL
) {
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
          dim_prefix = dim_prefix,
          post_process_importances = post_process_importances
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
calc_inter_method_stability <- function (importance_tbl, cor_method = "spearman") {
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

summarise_inter_method_stability <- function (inter_method_stability_tbl, dim_prefix = "mv_dim_") {
  inter_method_stability_tbl |>
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

# Compares each method's baseline full-multiverse importance vector to the
# corresponding ablated importance vectors obtained after fixing a decision to
# one option. This isolates within-method stability across multiverse sizes.
calc_intra_method_stability <- function (baseline_importance, ablation_importance,
                                         cor_method = "spearman") {
  ablation_importance |>
    select(fixed_decision, fixed_option, method, target_decision, importance) |>
    rename(ablated_importance = importance) |>
    left_join(
      baseline_importance |>
        select(method, target_decision, importance) |>
        rename(baseline_importance = importance),
      by = c("method", "target_decision")
    ) |>
    group_by(fixed_decision, fixed_option, method) |>
    summarise(
      rank_correlation = safe_cor(
        baseline_importance,
        ablated_importance,
        method = cor_method
      ),
      mean_abs_difference = mean(abs(baseline_importance - ablated_importance), na.rm = TRUE),
      n_target_decisions = sum(complete.cases(baseline_importance, ablated_importance)),
      .groups = "drop"
    )
}

summarise_intra_method_stability <- function (intra_method_stability_tbl,
                                              dim_prefix = "mv_dim_") {
  intra_method_stability_tbl |>
    group_by(fixed_decision, method) |>
    summarise(
      fixed_decision_label = strip_dim_prefix(first(fixed_decision), dim_prefix = dim_prefix),
      mean_rank_correlation = safe_mean(rank_correlation),
      min_rank_correlation = safe_min(rank_correlation),
      mean_abs_difference = safe_mean(mean_abs_difference),
      n_options = n(),
      .groups = "drop"
    )
}

calc_method_stability <- calc_inter_method_stability
summarise_method_stability <- summarise_inter_method_stability

# End-to-end ablation pipeline:
# 1) compute baseline importance on the full multiverse,
# 2) recompute importance after fixing each decision to each option,
# 3) compare methods within each ablated setting,
# 4) compare each method's full-multiverse importances to its ablated variants.
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
  inter_method_stability <- bind_rows(
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
    calc_inter_method_stability()

  intra_method_stability <- calc_intra_method_stability(
    baseline_importance = baseline_importance,
    ablation_importance = ablation_importance
  )

  list(
    baseline_importance = baseline_importance,
    ablation_importance = ablation_importance,
    inter_method_stability = inter_method_stability,
    inter_method_stability_summary = summarise_inter_method_stability(
      inter_method_stability,
      dim_prefix = dim_prefix
    ),
    intra_method_stability = intra_method_stability,
    intra_method_stability_summary = summarise_intra_method_stability(
      intra_method_stability,
      dim_prefix = dim_prefix
    )
  )
}
