# Composite importance table for a single analysis: one row per decision, with
# grouped columns per method
compose_importance_table <- function (decide,
                                      fanova_main,
                                      fanova_total = NULL,
                                      regression,
                                      dim_prefix = "mv_dim_",
                                      digits = 3,
                                      ratio_digits = 1,
                                      sort_by = "decide_total",
                                      caption = NULL,
                                      label = NULL,
                                      print_latex = TRUE,
                                      write_tex = TRUE,
                                      tables_dir = here::here("tables")) {
  vec_tbl <- function (vec, value) {
    tibble(
      decision = strip_dim_prefix(names(vec), dim_prefix = dim_prefix),
      !!value := unname(vec)
    )
  }

  decide_tbl <- decide |>
    transmute(
      decision = strip_dim_prefix(dimension, dim_prefix = dim_prefix),
      decide_total = decide_total,
      decide_main = decide_main,
      decide_ratio = ratio_main
    )

  # fANOVA total is optional; drop the column entirely when not supplied.
  fanova_cols <- if (is.null(fanova_total)) "fanova_main" else c("fanova_main", "fanova_total")

  wide <- decide_tbl |>
    full_join(vec_tbl(fanova_main, "fanova_main"), by = "decision")
  if (!is.null(fanova_total)) {
    wide <- wide |> full_join(vec_tbl(fanova_total, "fanova_total"), by = "decision")
  }
  wide <- wide |>
    full_join(vec_tbl(regression, "regression"), by = "decision") |>
    arrange(desc(.data[[sort_by]])) |>
    mutate(decision = nn(decision)) |>
    select(
      decision,
      decide_total, decide_main, decide_ratio,
      all_of(fanova_cols),
      regression
    ) |>
    # ratio as a percentage string, e.g. 88.3%
    mutate(decide_ratio = if_else(
      is.na(decide_ratio),
      NA_character_,
      paste0(formatC(100 * decide_ratio, format = "f", digits = ratio_digits), "%")
    ))

  n_fanova <- length(fanova_cols)
  fanova_names <- if (n_fanova == 2) c("Main", "Total") else "Main"

  kbl <- knitr::kable(
    wide,
    format = "latex",
    booktabs = TRUE,
    digits = digits,
    # keep small values in fixed notation (e.g. 0.00005, not 5e-05)
    format.args = list(scientific = FALSE, nsmall = digits),
    escape = TRUE,
    linesep = "",
    align = c("l", rep("r", 4 + n_fanova)),
    caption = caption,
    label = label,
    col.names = c(
      "Decision",
      "Total", "Main", "Ratio",
      fanova_names,
      "Reg."
    )
  ) |>
    kableExtra::add_header_above(
      c(" " = 1, "\\textsc{Decide}" = 3, "fANOVA" = n_fanova, " " = 1),
      escape = FALSE
    )

  latex <- as.character(kbl)
  if (isTRUE(print_latex)) {
    cat(latex, "\n", sep = "")
  }

  if (isTRUE(write_tex) && !is.null(label)) {
    if (!dir.exists(tables_dir)) {
      dir.create(tables_dir, recursive = TRUE)
    }
    tex_path <- file.path(tables_dir, paste0(label, ".tex"))
    writeLines(latex, tex_path)
    message("Wrote ", tex_path)
  }

  kbl
}
