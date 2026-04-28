vis_residuals_vs_fitted <- function(reg_result) {
  df <- tibble(
    fitted = fitted(reg_result),
    residuals = residuals(reg_result)
  )

  df |>
    ggplot(aes(x = fitted, y = residuals)) +
    geom_hline(yintercept = 0, linetype = "dashed", colour = "grey50") +
    geom_point(alpha = 0.6) +
    geom_smooth(method = "loess", se = FALSE, colour = "steelblue") +
    labs(x = "Fitted values", y = "Residuals") +
    theme_classic()
}

vis_observed_vs_predicted <- function(reg_result, type = c("scatter", "hist", "kde"), facet = FALSE) {
  type <- match.arg(type)

  col_name <- names(reg_result$model)[[1]]

  df <- tibble(
    observed = reg_result$model[[1]],
    predicted = fitted(reg_result)
  )

  if (type == "scatter") {
    df |>
      ggplot(aes(x = predicted, y = observed)) +
      geom_abline(slope = 1, intercept = 0, linetype = "dashed", colour = "grey50") +
      geom_point(alpha = 0.6) +
      labs(x = "Predicted", y = "Observed") +
      theme_classic()
  } else {
    df_long <- df |>
      pivot_longer(cols = c(observed, predicted), names_to = "source", values_to = "value")

    if (type == "hist") {
      p <- df_long |>
        ggplot(aes(x = value, fill = source, colour = source)) +
        geom_histogram(alpha = 0.5, position = "identity") +
        labs(x = col_name, y = "Count", fill = NULL, colour = NULL) +
        theme_classic()
    } else {
      p <- df_long |>
        ggplot(aes(x = value, fill = source, colour = source)) +
        geom_density(alpha = 0.3) +
        labs(x = col_name, y = "Density", fill = NULL, colour = NULL) +
        theme_classic()
    }

    if (facet) p <- p + facet_wrap(~source) + theme(legend.position = "none")
    p
  }
}
