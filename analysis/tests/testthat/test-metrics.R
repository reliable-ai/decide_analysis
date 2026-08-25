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
