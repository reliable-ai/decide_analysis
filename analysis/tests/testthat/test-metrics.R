# Snapshot tests for decide(), the general main/total-effect decomposition.
#
# See tests/metrics/test_metrics.py for the Python reference implementation.

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

test_that("decide produces expected results", {
  mv <- make_example_multiverse()

  decide(mv, "accuracy") |>
    expect_snapshot()
})

test_that("decide produces expected results (when reporting all scores)", {
  mv <- make_example_multiverse()

  decide(mv, "accuracy", report_all = TRUE) |>
    expect_snapshot()
})

test_that("decide's order-1 total_effect matches calc_between_bucket_variation", {
  # calc_between_bucket_variation is a special case of decide()'s total_effect:
  # single-dimension subsets on a full-factorial multiverse (no imputation
  # needed), with matching spread/summary functions (decide defaults to
  # pop_var/mean, calc_between_bucket_variation to var/mean).
  mv <- make_example_multiverse()

  between_bucket <- calc_between_bucket_variation(
    mv, "accuracy",
    fun_spread = pop_var, fun_summary = mean
  )

  decide_total_effect <- decide(
    mv, "accuracy",
    max_order = 1, spread = pop_var, summary = mean
  ) |>
    (\(tbl) setNames(tbl$decide_total, unlist(tbl$dimension)))()

  expect_equal(
    decide_total_effect[names(between_bucket)],
    between_bucket,
    ignore_attr = "names"
  )
})
