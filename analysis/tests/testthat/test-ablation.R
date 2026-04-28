# Tests for ablation-study helpers used in the hurricane analysis.

source(here::here("R", "_load.R"))
testthat::local_edition(3)

make_example_multiverse <- function() {
  tibble(
    mv_dim_A = rep(c("a1", "a2"), each = 4),
    mv_dim_B = rep(rep(c("b1", "b2"), each = 2), 2),
    mv_dim_C = rep(c("c1", "c2"), 4),
    accuracy = c(0.80, 0.82, 0.70, 0.73, 0.60, 0.63, 0.50, 0.55)
  )
}

test_that("build_ablation_grid enumerates every decision-option combination", {
  grid <- build_ablation_grid(make_example_multiverse())

  expect_equal(nrow(grid), 6)
  expect_equal(unique(grid$fixed_decision), c("mv_dim_A", "mv_dim_B", "mv_dim_C"))
  expect_equal(grid |> count(fixed_decision) |> pull(n), c(2, 2, 2))
})

test_that("fix_decision filters rows and removes the fixed dimension", {
  ablated <- fix_decision(make_example_multiverse(), "mv_dim_A", "a1")

  expect_equal(nrow(ablated), 4)
  expect_false("mv_dim_A" %in% names(ablated))
  expect_equal(names(ablated), c("mv_dim_B", "mv_dim_C", "accuracy"))
})

test_that("calc_inter_method_stability compares ablated importance rankings pairwise", {
  importance_tbl <- tibble(
    fixed_decision = "mv_dim_A",
    fixed_option = "a1",
    target_decision = rep(c("mv_dim_B", "mv_dim_C", "mv_dim_D"), 3),
    method = rep(c("fanova", "within", "between"), each = 3),
    importance = c(1, 2, 3, 2, 4, 6, 3, 2, 1)
  )

  stability <- calc_inter_method_stability(importance_tbl)

  expect_equal(
    stability |>
      filter(method_x == "fanova", method_y == "within") |>
      pull(rank_correlation),
    1
  )
  expect_equal(
    stability |>
      filter(method_x == "fanova", method_y == "between") |>
      pull(rank_correlation),
    -1
  )
  expect_equal(
    stability |>
      filter(method_x == "within", method_y == "between") |>
      pull(rank_correlation),
    -1
  )
})

test_that("calc_intra_method_stability compares baseline and ablated importances within method", {
  baseline_importance <- tibble(
    method = c(rep("within", 3), rep("between", 3)),
    target_decision = rep(c("mv_dim_A", "mv_dim_B", "mv_dim_C"), 2),
    target_decision_label = rep(c("A", "B", "C"), 2),
    importance = c(1, 2, 3, 3, 2, 1)
  )

  ablation_importance <- tibble(
    fixed_decision = c(rep("mv_dim_A", 6), rep("mv_dim_B", 6)),
    fixed_decision_label = c(rep("A", 6), rep("B", 6)),
    fixed_option = c(rep("a1", 3), rep("a2", 3), rep("b1", 3), rep("b2", 3)),
    method = c(rep("within", 6), rep("between", 6)),
    target_decision = rep(c("mv_dim_A", "mv_dim_B", "mv_dim_C"), 4),
    target_decision_label = rep(c("A", "B", "C"), 4),
    importance = c(1, 2, 3, 3, 2, 1, 3, 2, 1, 1, 2, 3),
    n_universes = 4
  )

  stability <- calc_intra_method_stability(baseline_importance, ablation_importance)

  expect_equal(
    stability |>
      filter(fixed_decision == "mv_dim_A", fixed_option == "a1", method == "within") |>
      pull(rank_correlation),
    1
  )
  expect_equal(
    stability |>
      filter(fixed_decision == "mv_dim_A", fixed_option == "a2", method == "within") |>
      pull(rank_correlation),
    -1
  )
  expect_equal(
    stability |>
      filter(fixed_decision == "mv_dim_B", fixed_option == "b1", method == "between") |>
      pull(rank_correlation),
    1
  )
  expect_equal(
    stability |>
      filter(fixed_decision == "mv_dim_B", fixed_option == "b2", method == "between") |>
      pull(rank_correlation),
    -1
  )
})

test_that("add_stability_average_row appends grouped averages", {
  stability_summary <- tibble(
    comparison = c("within vs between", "within vs between", "fanova vs between", "fanova vs between"),
    fixed_decision = c("mv_dim_A", "mv_dim_B", "mv_dim_A", "mv_dim_B"),
    fixed_decision_label = c("A", "B", "A", "B"),
    mean_rank_correlation = c(0.5, 0.7, 0.4, 0.6)
  )

  averaged <- add_stability_average_row(stability_summary, group_cols = "comparison")

  expect_equal(nrow(averaged), 6)
  expect_equal(
    averaged |>
      filter(fixed_decision == "overall_average", comparison == "within vs between") |>
      pull(mean_rank_correlation),
    0.6
  )
  expect_equal(
    averaged |>
      filter(fixed_decision == "overall_average") |>
      pull(fixed_decision_label),
    c("Average", "Average")
  )
})

test_that("vis_inter_method_stability rotates x-axis labels", {
  inter_method_stability_summary <- tibble(
    method_x = "within",
    method_y = "between",
    fixed_decision = "mv_dim_A",
    fixed_decision_label = "A",
    mean_rank_correlation = 0.5
  )

  plot <- vis_inter_method_stability(inter_method_stability_summary)

  expect_s3_class(plot, "ggplot")
  expect_equal(plot$theme$axis.text.x$angle, 45)
  expect_equal(plot$theme$axis.text.x$hjust, 1)
})

test_that("vis_inter_method_stability can show values and add averages", {
  inter_method_stability_summary <- tibble(
    method_x = c("within", "within", "fanova", "fanova"),
    method_y = c("between", "between", "between", "between"),
    fixed_decision = c("mv_dim_A", "mv_dim_B", "mv_dim_A", "mv_dim_B"),
    fixed_decision_label = c("A", "B", "A", "B"),
    mean_rank_correlation = c(0.5, 0.7, 0.4, 0.6)
  )

  plot <- vis_inter_method_stability(
    inter_method_stability_summary,
    show_values = TRUE,
    add_average = TRUE
  )
  geom_classes <- vapply(plot$layers, function(layer) class(layer$geom)[1], character(1))

  expect_true("GeomText" %in% geom_classes)
  expect_true("Average" %in% as.character(plot$data$fixed_decision_label))
  expect_equal(
    plot$data |>
      filter(fixed_decision_label == "Average", comparison == "within vs between") |>
      pull(mean_rank_correlation),
    0.6
  )
})

test_that("vis_intra_method_stability rotates x-axis labels", {
  intra_method_stability_summary <- tibble(
    method = "within",
    fixed_decision = "mv_dim_A",
    fixed_decision_label = "A",
    mean_rank_correlation = 0.5
  )

  plot <- vis_intra_method_stability(intra_method_stability_summary)

  expect_s3_class(plot, "ggplot")
  expect_equal(plot$theme$axis.text.x$angle, 45)
  expect_equal(plot$theme$axis.text.x$hjust, 1)
})

test_that("vis_intra_method_stability can show values and add averages", {
  intra_method_stability_summary <- tibble(
    method = c("within", "within", "between", "between"),
    fixed_decision = c("mv_dim_A", "mv_dim_B", "mv_dim_A", "mv_dim_B"),
    fixed_decision_label = c("A", "B", "A", "B"),
    mean_rank_correlation = c(0.5, 0.7, 0.4, 0.6)
  )

  plot <- vis_intra_method_stability(
    intra_method_stability_summary,
    show_values = TRUE,
    add_average = TRUE
  )
  geom_classes <- vapply(plot$layers, function(layer) class(layer$geom)[1], character(1))

  expect_true("GeomText" %in% geom_classes)
  expect_true("Average" %in% as.character(plot$data$fixed_decision_label))
  expect_equal(
    plot$data |>
      filter(fixed_decision_label == "Average", method == "within") |>
      pull(mean_rank_correlation),
    0.6
  )
})

test_that("regression importance aggregates absolute coefficients by decision", {
  mv <- tidyr::expand_grid(
    mv_dim_A = c("a1", "a2"),
    mv_dim_B = c("b1", "b2", "b3")
  ) |>
    mutate(
      outcome = 1 +
        2 * (mv_dim_A == "a2") -
        1 * (mv_dim_B == "b2") +
        3 * (mv_dim_B == "b3") +
        c(0.0, 0.1, -0.1, 0.05, -0.05, 0.02)
    )

  reg_importance <- calc_regression_importance(mv, "outcome")

  expect_equal(unname(reg_importance["mv_dim_A"]), 2, tolerance = 0.05)
  expect_equal(unname(reg_importance["mv_dim_B"]), 4, tolerance = 0.1)
})

test_that("tidy_importance_methods keeps regression alongside other methods", {
  importance_tbl <- tidy_importance_methods(
    list(
      regression = c(mv_dim_A = 1, mv_dim_B = 2),
      fanova = c(mv_dim_A = 3, mv_dim_B = 4),
      within = c(mv_dim_A = 5, mv_dim_B = 6),
      between = c(mv_dim_A = 7, mv_dim_B = 8)
    )
  )

  expect_setequal(
    unique(importance_tbl$method),
    c("regression", "fanova", "within", "between")
  )
})
