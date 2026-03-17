vis_regression_coefficients <- function(reg_result, dim_prefix = "mv_dim_") {
  df <- reg_result |>
    filter(term != "(Intercept)") |>
    mutate(term_clean = sub(paste0("^", dim_prefix), "", term))

  # Find shared prefixes among terms to identify decisions.
  # For each term, the decision is the longest prefix (up to and including a

  # trailing underscore-delimited segment) shared with at least one other term.
  # Terms that share no prefix with others are their own decision.
  terms <- df$term_clean
  find_decision <- function(t) {
    others <- setdiff(terms, t)
    # Split into underscore-separated parts; try progressively longer prefixes
    parts <- strsplit(t, "_")[[1]]
    best <- t
    for (k in seq_along(parts)) {
      prefix <- paste(parts[1:k], collapse = "_")
      if (any(startsWith(others, prefix))) best <- prefix
    }
    best
  }

  df <- df |>
    mutate(
      decision = vapply(term_clean, find_decision, character(1)),
      option = mapply(function(t, d) {
        rest <- substring(t, nchar(d) + 1)
        if (rest == "") d else rest
      }, term_clean, decision)
    ) |>
    mutate(decision = fct_reorder(decision, abs(estimate), .fun = max))

  df |>
    ggplot(aes(x = estimate, y = option)) +
    geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50") +
    geom_pointrange(aes(
      xmin = estimate - 1.96 * std.error,
      xmax = estimate + 1.96 * std.error
    )) +
    facet_grid(decision ~ ., scales = "free_y", space = "free_y", switch = "y") +
    labs(x = "Coefficient estimate (95% CI)", y = NULL) +
    theme_classic() +
    theme(
      strip.placement = "outside",
      strip.background = element_blank(),
      strip.text.y.left = element_text(angle = 0, face = "bold")
    )
}

vis_importance <- function(between_var, dim_prefix = "mv_dim_") {
  tibble(
    decision = sub(paste0("^", dim_prefix), "", names(between_var)),
    mean_variance = unname(between_var)
  ) |>
    mutate(decision = fct_reorder(decision, mean_variance)) |>
    ggplot(aes(x = mean_variance, y = decision)) +
    geom_col() +
    labs(x = "Importance", y = NULL) +
    theme_classic()
}
