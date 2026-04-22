vis_method_stability <- function (method_stability_summary, baseline_label = "full multiverse") {
  method_stability_summary |>
    mutate(
      comparison = paste(method_x, "vs", method_y),
      fixed_decision_label = if_else(
        fixed_decision == "full_multiverse",
        baseline_label,
        fixed_decision_label
      )
    ) |>
    ggplot(aes(x = comparison, y = fct_reorder(fixed_decision_label, mean_rank_correlation), fill = mean_rank_correlation)) +
    geom_tile() +
    scale_fill_viridis_c(limits = c(-1, 1)) +
    labs(x = NULL, y = NULL, fill = "Mean rank\ncorrelation") +
    theme_classic() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))
}

vis_option_sensitivity <- function (option_sensitivity_summary,
                                    show_regression_line = FALSE,
                                    show_correlation = TRUE) {
  plot <- option_sensitivity_summary |>
    ggplot(aes(
      x = baseline_importance,
      y = mean_pairwise_abs_change,
      label = fixed_decision_label
    )) +
    geom_point() +
    ggrepel::geom_text_repel() +
    facet_wrap(vars(method), scales = "free") +
    labs(
      x = "Baseline importance of fixed decision",
      y = "Mean pairwise change across fixed options"
    ) +
    theme_classic()

  if (show_regression_line) {
    plot <- plot +
      geom_smooth(method = "lm", se = FALSE, colour = "grey50")
  }

  if (show_correlation) {
    correlation_labels <- summarise_predictive_relationship(option_sensitivity_summary) |>
      mutate(
        label = if_else(
          is.na(association),
          "rho = NA",
          paste0("rho = ", formatC(association, digits = 2, format = "f"))
        ),
        x = Inf,
        y = -Inf
      )

    plot <- plot +
      geom_text(
        data = correlation_labels,
        aes(x = x, y = y, label = label),
        hjust = 1.1,
        vjust = -0.5,
        inherit.aes = FALSE
      )
  }

  plot
}
