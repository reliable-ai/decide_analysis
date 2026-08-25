# Tests for check_full_design(), which flags multiverses that aren't a full
# factorial design (i.e. some combination of judgment-call options is missing).

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

test_that("check_full_design returns TRUE and emits no message for a full factorial design", {
  mv <- make_example_multiverse()

  expect_no_message(result <- check_full_design(mv))
  expect_true(result)
})

test_that("check_full_design returns FALSE and reports missing combinations for a ragged design", {
  mv <- make_example_multiverse()[-c(1, 3), ]

  expect_message(
    result <- check_full_design(mv),
    "not a full design: 6 of 8 possible combinations are realised \\(2 missing, 25\\.0%\\)"
  )
  expect_false(result)
})

test_that("check_full_design's message attributes missingness to the responsible decisions", {
  # Removing (a1, b1, c1) and (a1, b2, c1) leaves every context complete for
  # mv_dim_B, but mv_dim_A and mv_dim_C each miss one option in one context.
  mv <- make_example_multiverse()[-c(1, 3), ]

  expect_message(check_full_design(mv), "mv_dim_A\\s+2\\s+2\\s+25")
  expect_message(check_full_design(mv), "mv_dim_C\\s+2\\s+2\\s+25")
  expect_no_match(
    capture_messages(check_full_design(mv)),
    "mv_dim_B\\s+2\\s+0"
  )
})

test_that("summarize_missing_by_dim quantifies per-decision missingness", {
  mv <- make_example_multiverse()[-c(1, 3), ]

  by_dim <- summarize_missing_by_dim(mv, c("mv_dim_A", "mv_dim_B", "mv_dim_C"))

  expect_equal(
    by_dim |> filter(dimension == "mv_dim_A") |> pull(pct_missing),
    25
  )
  expect_equal(
    by_dim |> filter(dimension == "mv_dim_C") |> pull(pct_missing),
    25
  )
  expect_equal(
    by_dim |> filter(dimension == "mv_dim_B") |> pull(pct_missing),
    0
  )
})

test_that("check_full_design respects a custom dim_prefix", {
  mv <- make_example_multiverse() |>
    rename_with(~ sub("^mv_dim_", "dim_", .x), starts_with("mv_dim_"))

  expect_no_message(result <- check_full_design(mv, dim_prefix = "dim_"))
  expect_true(result)

  expect_message(
    result <- check_full_design(mv[-c(1, 3), ], dim_prefix = "dim_"),
    "not a full design"
  )
  expect_false(result)
})
