# fANOVA main / individual importance per decision (main effects only, no
# interactions). This is the cheaper of the two fANOVA quantities.
calc_fanova_main_importance <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  calc_fanova(mv, colname_metric, dim_prefix = dim_prefix, use_individual = TRUE) |>
    fanova_to_vec()
}

# fANOVA total importance per decision (main effect plus every interaction the
# decision is involved in). Requires the full interaction decomposition, which
# is markedly slower, hence gated behind a flag in the ablation pipeline.
calc_fanova_total_importance <- function (mv, colname_metric, dim_prefix = "mv_dim_") {
  calc_fanova(mv, colname_metric, dim_prefix = dim_prefix, use_individual = FALSE) |>
    fanova_total_to_vec()
}

# DECIDE main effect and total effect per decision, as two named numeric vectors
# keyed by dimension name.
calc_decide_importances <- function (mv, colname_metric, dim_prefix = "mv_dim_",
                                     spread = pop_var, summary = mean) {
  decomposition <- decide(
    mv, colname_metric,
    max_order = 1, spread = spread, summary = summary, dim_prefix = dim_prefix
  )

  list(
    decide_total = setNames(decomposition$decide_total, decomposition$dimension),
    decide_main  = setNames(decomposition$decide_main, decomposition$dimension)
  )
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

# Computes named importance vectors per method.
calc_importance_methods <- function (mv, colname_metric, dim_prefix = "mv_dim_",
                                      post_process_importances = NULL,
                                      regression_mv_pre_process = identity,
                                      regression_post_process = identity,
                                      fanova_mv_pre_process = identity,
                                      fanova_post_process = identity,
                                      include_fanova_total = TRUE) {
  if (is.null(post_process_importances)) {
    post_process_importances = function (x) { return(x) }
  }

  decide_importances <- calc_decide_importances(mv, colname_metric, dim_prefix = dim_prefix)

  fanova_mv <- fanova_mv_pre_process(mv)

  methods <- list(
    regression = calc_regression_importance(regression_mv_pre_process(mv), colname_metric, dim_prefix = dim_prefix) |>
      regression_post_process() |>
      post_process_importances(),
    fanova_main = calc_fanova_main_importance(fanova_mv, colname_metric, dim_prefix = dim_prefix) |>
      fanova_post_process() |>
      post_process_importances(),
    decide_main = decide_importances$decide_main |>
      post_process_importances(),
    decide_total = decide_importances$decide_total |>
      post_process_importances()
  )

  if (include_fanova_total) {
    methods$fanova_total <- calc_fanova_total_importance(fanova_mv, colname_metric, dim_prefix = dim_prefix) |>
      fanova_post_process() |>
      post_process_importances()
  }

  methods
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

# Restrict a multiverse to the specified decision-option pairs, then discard
# dimensions that no longer vary in the ablated data.
fix_decision <- function (mv, fixed_decision, fixed_option, dim_prefix = "mv_dim_") {
  for (i in seq_along(fixed_decision)) {
    mv <- mv |>
      filter(as.character(.data[[fixed_decision[[i]]]]) == fixed_option[[i]])
  }
  mv |> remove_fake_decisions(dim_prefix = dim_prefix)
}

# Build the ablation grid.
#
# `prefixes` is an optional character vector of column-name prefixes.  All
# dimension columns whose name starts with a given prefix are treated as a
# single logical decision: they are ablated jointly (every unique combination
# of their values counts as one "option") and are excluded from individual
# single-column ablation.  Prefixes are matched before individual columns, so
# the same column cannot appear in both.
#
# The returned tibble has two extra list-columns used internally by
# calc_ablation_importance:
#   fixed_decision_cols – character vector of actual column names to filter on.
#   fixed_option_vals   – character vector of values (parallel to the above).
build_ablation_grid <- function (mv, prefixes = character(0), dim_prefix = "mv_dim_") {
  dim_cols <- mv |>
    select(starts_with(dim_prefix)) |>
    colnames()

  # Absorb columns claimed by a prefix so they are not individually ablated.
  grouped_cols <- character(0)

  prefix_rows <- purrr::map_dfr(
    prefixes,
    function (pfx) {
      matching <- dim_cols[startsWith(dim_cols, pfx)]
      if (length(matching) == 0) return(tibble())
      grouped_cols <<- c(grouped_cols, matching)

      combos <- mv |>
        select(all_of(matching)) |>
        distinct() |>
        mutate(across(everything(), as.character))

      purrr::map_dfr(seq_len(nrow(combos)), function (i) {
        vals <- unname(unlist(combos[i, ]))
        tibble(
          fixed_decision       = pfx,
          fixed_decision_label = strip_dim_prefix(pfx, dim_prefix = dim_prefix),
          fixed_option         = paste(vals, collapse = "/"),
          fixed_decision_cols  = list(matching),
          fixed_option_vals    = list(vals)
        )
      })
    }
  )

  individual_cols <- setdiff(dim_cols, grouped_cols)

  individual_rows <- purrr::map_dfr(
    individual_cols,
    function (col) {
      options <- unique(as.character(mv[[col]]))
      tibble(
        fixed_decision       = col,
        fixed_decision_label = strip_dim_prefix(col, dim_prefix = dim_prefix),
        fixed_option         = options,
        fixed_decision_cols  = rep(list(col), length(options)),
        fixed_option_vals    = as.list(options)
      )
    }
  )

  bind_rows(prefix_rows, individual_rows)
}

# An ablated multiverse is only usable if at least two decisions still vary in
# it: with a single remaining decision every importance vector has length one,
# so no rank correlation can be computed, and the model-based estimators break
# down. This functions checks for these scenarios.
is_usable_ablation <- function (ablated_mv, dim_prefix = "mv_dim_",
                                min_decisions = 2, min_universes = 2) {
  n_decisions <- ablated_mv |> select(starts_with(dim_prefix)) |> ncol()

  n_decisions >= min_decisions && nrow(ablated_mv) >= min_universes
}

calc_ablation_importance <- function (
  mv,
  colname_metric,
  dim_prefix = "mv_dim_",
  prefixes = character(0),
  post_process_importances = NULL,
  regression_mv_pre_process = identity,
  regression_post_process = identity,
  fanova_mv_pre_process = identity,
  fanova_post_process = identity,
  include_fanova_total = TRUE
) {
  ablation_grid <- build_ablation_grid(mv, prefixes = prefixes, dim_prefix = dim_prefix)

  purrr::pmap_dfr(
    ablation_grid,
    function (fixed_decision, fixed_decision_label, fixed_option,
              fixed_decision_cols, fixed_option_vals) {
      ablated_mv <- fix_decision(
        mv,
        fixed_decision = fixed_decision_cols,
        fixed_option = fixed_option_vals,
        dim_prefix = dim_prefix
      )

      # Skip ablations that wouldn't work
      if (!is_usable_ablation(ablated_mv, dim_prefix = dim_prefix)) {
        message(
          "Skipping broken ablation: ", fixed_decision_label, " = ", fixed_option,
          " (", nrow(ablated_mv), " universes, ",
          ablated_mv |> select(starts_with(dim_prefix)) |> ncol(),
          " remaining decisions)"
        )
        return(tibble())
      }

      tidy_importance_methods(
        calc_importance_methods(
          ablated_mv,
          colname_metric = colname_metric,
          dim_prefix = dim_prefix,
          post_process_importances = post_process_importances,
          regression_mv_pre_process = regression_mv_pre_process,
          regression_post_process = regression_post_process,
          fanova_mv_pre_process = fanova_mv_pre_process,
          fanova_post_process = fanova_post_process,
          include_fanova_total = include_fanova_total
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

# The base method a (possibly variant-suffixed) method name belongs to, e.g.
# both `decide_main` and `decide_total` map to `decide`.
method_family <- function (method) {
  sub("_(main|total)$", "", method)
}

# Compares importance rankings between every pair of methods.
# For each (fixed_decision, fixed_option), it correlates method-specific
# importance vectors across target decisions after pivoting to wide format.
# The reported rank_correlation is Spearman by default.
calc_inter_method_stability <- function (importance_tbl, cor_method = "spearman") {
  methods <- unique(importance_tbl$method)
  # Create compairson pairings, but skip comparisons between equal methods
  method_pairs <- combn(methods, 2, simplify = FALSE) |>
    purrr::keep(function (pair) method_family(pair[[1]]) != method_family(pair[[2]]))

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
run_ablation_analysis <- function (mv, colname_metric, dim_prefix = "mv_dim_", prefixes = character(0),
                                    post_process_importances = NULL,
                                    regression_mv_pre_process = identity,
                                    regression_post_process = identity,
                                    fanova_mv_pre_process = identity,
                                    fanova_post_process = identity,
                                    include_fanova_total = TRUE) {
  # Baseline: importances computed on the full multiverse (no fixed decision).
  baseline_importance <- tidy_importance_methods(
    calc_importance_methods(
      mv,
      colname_metric = colname_metric,
      dim_prefix = dim_prefix,
      post_process_importances = post_process_importances,
      regression_mv_pre_process = regression_mv_pre_process,
      regression_post_process = regression_post_process,
      fanova_mv_pre_process = fanova_mv_pre_process,
      fanova_post_process = fanova_post_process,
      include_fanova_total = include_fanova_total
    ),
    dim_prefix = dim_prefix
  )

  # Ablation: re-estimate importances after fixing each decision to each option.
  ablation_importance <- calc_ablation_importance(
    mv,
    colname_metric = colname_metric,
    dim_prefix = dim_prefix,
    prefixes = prefixes,
    post_process_importances = post_process_importances,
    regression_mv_pre_process = regression_mv_pre_process,
    regression_post_process = regression_post_process,
    fanova_mv_pre_process = fanova_mv_pre_process,
    fanova_post_process = fanova_post_process,
    include_fanova_total = include_fanova_total
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
