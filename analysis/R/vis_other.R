vis_regression_coefficients <- function(reg_result, dim_prefix = "mv_dim_") {
  df <- tidy_regression_coefficients(reg_result, dim_prefix = dim_prefix) |>
    mutate(decision_label = fct_reorder(decision_label, abs(estimate), .fun = max))

  df |>
    ggplot(aes(x = estimate, y = option)) +
    geom_vline(xintercept = 0, linetype = "dashed", colour = "grey50") +
    geom_pointrange(aes(
      xmin = estimate - 1.96 * std.error,
      xmax = estimate + 1.96 * std.error
    )) +
    facet_grid(decision_label ~ ., scales = "free_y", space = "free_y", switch = "y") +
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
    mutate(decision = fct_reorder(decision, mean_variance |> replace_na(0))) |>
    ggplot(aes(x = mean_variance, y = decision)) +
    geom_col() +
    labs(x = "Importance", y = NULL) +
    theme_classic()
}

vis_importance_2dim <- function(importance_x, importance_y,
                               dim_prefix = "mv_dim_") {
  label_x <- deparse(substitute(importance_x))
  label_y <- deparse(substitute(importance_y))

  df <- tibble(
    decision = sub(paste0("^", dim_prefix), "", names(importance_x)),
    x = unname(importance_x),
    y = unname(importance_y[names(importance_x)])
  )

  df |>
    ggplot(aes(x = x, y = y, label = decision)) +
    geom_point() +
    ggrepel::geom_text_repel() +
    labs(x = label_x, y = label_y) +
    theme_classic()
}
