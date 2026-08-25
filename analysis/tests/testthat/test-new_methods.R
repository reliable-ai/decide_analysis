# Snapshot tests for within- and between-bucket variation metrics.
#
# Reproduction of the Python implementation to double check that results are
# the same across implementations. See tests/metrics/test_metrics.py

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

test_that("calc_within_bucket_variation produces expected results", {
  mv <- make_example_multiverse()
  calc_within_bucket_variation(mv, "accuracy") |>
    round(10) |>
    expect_snapshot()
})

test_that("calc_between_bucket_variation produces expected results", {
  mv <- make_example_multiverse()

  calc_between_bucket_variation(mv, "accuracy") |>
    round(10) |>
    expect_snapshot()
})
