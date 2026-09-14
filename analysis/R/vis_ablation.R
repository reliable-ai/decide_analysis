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
                                        add_average = TRUE,
                                        fill_label = "Mean rank\ncorrelation",
                                        fill_option = "viridis") {
  plot_data <- inter_method_stability_summary |>
    mutate(
      # order the two methods within each pair canonically, so that e.g.
      # DECIDE always precedes fANOVA in the comparison label
      swap_methods = method_rank(method_x) > method_rank(method_y),
      method_first = if_else(swap_methods, method_y, method_x),
      method_second = if_else(swap_methods, method_x, method_y),
      comparison = paste(method_first |> nn(), "vs", method_second |> nn()),
      fixed_decision_label = if_else(
        fixed_decision == "full_multiverse",
        baseline_label,
        fixed_decision_label
      )
    )

  # comparisons on the x-axis follow the canonical method order
  comparison_order <- plot_data |>
    distinct(method_first, method_second, comparison) |>
    arrange(method_rank(method_first), method_rank(method_second)) |>
    pull(comparison)

  if (add_average) {
    plot_data <- add_stability_average_row(plot_data, group_cols = "comparison")
  }

  decision_order <- plot_data |>
    filter(
      fixed_decision_label != "Average",
      fixed_decision_label != baseline_label
    ) |>
    group_by(fixed_decision_label) |>
    summarise(order_value = safe_mean(mean_rank_correlation), .groups = "drop") |>
    arrange(order_value) |>
    pull(fixed_decision_label)

  # full multiverse row always sits at the top of the heatmap (last level = top of y-axis)
  decision_order <- c(decision_order, baseline_label)

  if (add_average) {
    decision_order <- c("Average", decision_order)
  }

  plot_data <- plot_data |>
    mutate(
      comparison = factor(comparison, levels = unique(comparison_order)),
      fixed_decision_label = factor(fixed_decision_label, levels = unique(decision_order)),
      correlation_label = if_else(
        is.na(mean_rank_correlation),
        "NA",
        formatC(mean_rank_correlation, digits = 2, format = "f")
      ),
      label_color = if_else(
        !is.na(mean_rank_correlation) & mean_rank_correlation < -0.5,
        "white",
        "black"
      )
    )

  plot <- ggplot(
    plot_data,
    aes(x = comparison, y = fixed_decision_label, fill = mean_rank_correlation)
  ) +
    geom_tile() +
    scale_fill_viridis_c(limits = c(-1, 1), option = fill_option) +
    labs(x = NULL, y = NULL, fill = fill_label) +
    theme_classic() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))

  if (show_values) {
    plot <- plot + geom_text(aes(label = correlation_label, color = label_color), size = 3) +
      scale_color_identity()
  }

  if (add_average) {
    plot <- plot + geom_hline(yintercept = 1.5, color = "black", linewidth = 0.5)
  }

  plot
}

vis_intra_method_stability <- function (intra_method_stability_summary,
                                        show_values = TRUE,
                                        add_average = TRUE,
                                        fill_label = "Mean rank\ncorrelation",
                                        fill_option = "mako") {
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
      # methods on the x-axis follow the canonical method order
      method_label = factor_method_labels(method),
      fixed_decision_label = factor(fixed_decision_label, levels = unique(decision_order)),
      correlation_label = if_else(
        is.na(mean_rank_correlation),
        "NA",
        formatC(mean_rank_correlation, digits = 2, format = "f")
      ),
      label_color = if_else(
        !is.na(mean_rank_correlation) & mean_rank_correlation < -0.5,
        "white",
        "black"
      )
    )

  plot <- ggplot(
    plot_data,
    aes(
      x = method_label,
      y = fixed_decision_label,
      fill = mean_rank_correlation
    )
  ) +
    geom_tile() +
    scale_fill_viridis_c(limits = c(-1, 1), option = fill_option) +
    labs(x = NULL, y = NULL, fill = fill_label) +
    theme_classic() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))

  if (show_values) {
    plot <- plot + geom_text(aes(label = correlation_label, color = label_color), size = 3) +
      scale_color_identity()
  }

  if (add_average) {
    plot <- plot + geom_hline(yintercept = 1.5, color = "black", linewidth = 0.5)
  }

  plot
}

vis_method_stability <- vis_inter_method_stability
