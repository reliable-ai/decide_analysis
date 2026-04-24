add_stability_average_row <- function (stability_summary,
                                       group_cols,
                                       average_label = "Average") {
  bind_rows(
    stability_summary,
    stability_summary |>
      group_by(across(all_of(group_cols))) |>
      summarise(
        fixed_decision = "overall_average",
        fixed_decision_label = average_label,
        mean_rank_correlation = safe_mean(mean_rank_correlation),
        .groups = "drop"
      )
  )
}

vis_inter_method_stability <- function (inter_method_stability_summary,
                                        baseline_label = "full multiverse",
                                        show_values = TRUE,
                                        add_average = TRUE) {
  plot_data <- inter_method_stability_summary |>
    mutate(
      comparison = paste(method_x, "vs", method_y),
      fixed_decision_label = if_else(
        fixed_decision == "full_multiverse",
        baseline_label,
        fixed_decision_label
      )
    )

  if (add_average) {
    plot_data <- add_stability_average_row(plot_data, group_cols = "comparison")
  }

  decision_order <- plot_data |>
    filter(fixed_decision_label != "Average") |>
    group_by(fixed_decision_label) |>
    summarise(order_value = safe_mean(mean_rank_correlation), .groups = "drop") |>
    arrange(order_value) |>
    pull(fixed_decision_label)

  if (add_average) {
    decision_order <- c("Average", decision_order)
  }

  plot_data <- plot_data |>
    mutate(
      fixed_decision_label = factor(fixed_decision_label, levels = unique(decision_order)),
      correlation_label = if_else(
        is.na(mean_rank_correlation),
        "NA",
        formatC(mean_rank_correlation, digits = 2, format = "f")
      )
    )

  plot <- ggplot(
    plot_data,
    aes(x = comparison, y = fixed_decision_label, fill = mean_rank_correlation)
  ) +
    geom_tile() +
    scale_fill_viridis_c(limits = c(-1, 1)) +
    labs(x = NULL, y = NULL, fill = "Mean rank\ncorrelation") +
    theme_classic() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))

  if (show_values) {
    plot <- plot + geom_text(aes(label = correlation_label), size = 3)
  }

  plot
}

vis_intra_method_stability <- function (intra_method_stability_summary,
                                        show_values = TRUE,
                                        add_average = TRUE) {
  plot_data <- intra_method_stability_summary

  if (add_average) {
    plot_data <- add_stability_average_row(plot_data, group_cols = "method")
  }

  decision_order <- plot_data |>
    filter(fixed_decision_label != "Average") |>
    group_by(fixed_decision_label) |>
    summarise(order_value = safe_mean(mean_rank_correlation), .groups = "drop") |>
    arrange(order_value) |>
    pull(fixed_decision_label)

  if (add_average) {
    decision_order <- c("Average", decision_order)
  }

  plot_data <- plot_data |>
    mutate(
      fixed_decision_label = factor(fixed_decision_label, levels = unique(decision_order)),
      correlation_label = if_else(
        is.na(mean_rank_correlation),
        "NA",
        formatC(mean_rank_correlation, digits = 2, format = "f")
      )
    )

  plot <- ggplot(
    plot_data,
    aes(
      x = method,
      y = fixed_decision_label,
      fill = mean_rank_correlation
    )
  ) +
    geom_tile() +
    scale_fill_viridis_c(limits = c(-1, 1)) +
    labs(x = NULL, y = NULL, fill = "Mean rank\ncorrelation") +
    theme_classic() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))

  if (show_values) {
    plot <- plot + geom_text(aes(label = correlation_label), size = 3)
  }

  plot
}

vis_method_stability <- vis_inter_method_stability

vis_option_sensitivity <- function (option_sensitivity_summary,
                                    show_regression_line = FALSE,
                                    show_correlation = TRUE) {
  plot_data <- option_sensitivity_summary

  if (show_correlation) {
    plot_data <- plot_data |>
      left_join(
        summarise_predictive_relationship(
          option_sensitivity_summary,
          method = "pearson"
        ) |>
          mutate(
            method_label = paste0(
              method,
              "\n",
              if_else(
                is.na(association),
                "r = NA",
                paste0("r = ", formatC(association, digits = 2, format = "f"))
              )
            )
          ) |>
          select(method, method_label),
        by = "method"
      )
  } else {
    plot_data <- plot_data |>
      mutate(method_label = method)
  }

  plot <- plot_data |>
    ggplot(aes(
      x = baseline_importance,
      y = mean_pairwise_abs_change,
      label = fixed_decision_label
    )) +
    geom_point() +
    ggrepel::geom_text_repel() +
    facet_wrap(vars(method_label), scales = "free") +
    labs(
      x = "Baseline importance of fixed decision",
      y = "Mean pairwise change across fixed options"
    ) +
    theme_classic()

  if (show_regression_line) {
    plot <- plot +
      geom_smooth(method = "lm", se = FALSE, colour = "grey50")
  }

  plot
}
