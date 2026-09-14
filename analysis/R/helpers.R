get_multiverse_decisions <- function (mv, dim_prefix = "mv_dim_") {
  opts <- mv |>
    select(starts_with(dim_prefix)) |>
    lapply(unique)
  names(opts) <- sub(paste0("^", dim_prefix), "", names(opts))
  opts
}

strip_dim_prefix <- function (x, dim_prefix = "mv_dim_") {
  sub(paste0("^", dim_prefix), "", x)
}

# Canonical display order of the importance methods, used across all plots so
# that methods always appear in the same sequence.
METHOD_ORDER <- c(
  "decide_total",
  "decide_main",
  "decide",
  "fanova_total",
  "fanova_main",
  "fanova",
  "regression"
)

# Position of a method in the canonical order; unknown methods sort last.
method_rank <- function (method) {
  rank <- match(as.character(method), METHOD_ORDER)
  replace_na(rank, length(METHOD_ORDER) + 1L)
}

# Method names present in `methods`, in canonical order. Unknown methods keep
# their original relative order and are appended at the end.
order_methods <- function (methods) {
  methods <- unique(as.character(methods))
  c(intersect(METHOD_ORDER, methods), setdiff(methods, METHOD_ORDER))
}

# Factor of method names in canonical order.
factor_methods <- function (methods) {
  factor(as.character(methods), levels = order_methods(methods))
}

# Factor of nicknamed method labels, in canonical order.
factor_method_labels <- function (methods) {
  levels <- order_methods(methods)
  factor(nn(as.character(methods)), levels = nn(levels))
}
