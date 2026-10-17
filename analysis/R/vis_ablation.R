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

# Order of the decision rows in the stability heatmaps: by mean correlation
# across methods (or method pairs), lowest first, so that the most stable
# decisions sit at the top. Returns the decisions' fixed_decision_label values.
# Pass the result as `decision_order` to both heatmaps so their rows line up.
stability_decision_order <- function (stability_summary) {
  stability_summary |>
    filter(fixed_decision != "full_multiverse") |>
    group_by(fixed_decision_label) |>
    summarise(order_value = safe_mean(mean_rank_correlation), .groups = "drop") |>
    arrange(order_value) |>
    pull(fixed_decision_label)
}

vis_inter_method_stability <- function (inter_method_stability_summary,
                                        baseline_label = "Full Multiverse",
                                        show_values = TRUE,
                                        add_average = TRUE,
                                        fill_label = "Mean rank\ncorrelation",
                                        fill_option = "viridis",
                                        decision_order = NULL,
                                        value_size = 3) {
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

  # rows follow `decision_order` if given (e.g. to match the intra-method
  # heatmap), otherwise this heatmap's own mean correlations
  if (is.null(decision_order)) {
    decision_order <- stability_decision_order(inter_method_stability_summary)
  }

  # full multiverse row always sits at the top of the heatmap (last level = top of y-axis)
  decision_order <- c(decision_order, baseline_label)

  if (add_average) {
    decision_order <- c("Average", decision_order)
  }

  plot_data <- plot_data |>
    mutate(
      comparison = factor(comparison, levels = unique(comparison_order)),
      fixed_decision_label = factor(fixed_decision_label, levels = unique(decision_order)) |>
        # display names from R/nicknames.R, keeping the row order
        fct_relabel(nn),
      correlation_label = if_else(
        is.na(mean_rank_correlation),
        "NA",
        # round first and add 0, so that values rounding to zero from below
        # show as 0.00 rather than -0.00
        formatC(round(mean_rank_correlation, 2) + 0, digits = 2, format = "f")
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
    plot <- plot + geom_text(aes(label = correlation_label, color = label_color), size = value_size) +
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
                                        fill_option = "mako",
                                        decision_order = NULL,
                                        value_size = 3) {
  plot_data <- intra_method_stability_summary

  if (add_average) {
    plot_data <- add_stability_average_row(plot_data, group_cols = "method")
  }

  # rows follow `decision_order` if given (e.g. to match the inter-method
  # heatmap), otherwise this heatmap's own mean correlations
  if (is.null(decision_order)) {
    decision_order <- stability_decision_order(intra_method_stability_summary)
  }

  if (add_average) {
    decision_order <- c("Average", decision_order)
  }

  plot_data <- plot_data |>
    mutate(
      # methods on the x-axis follow the canonical method order
      method_label = factor_method_labels(method),
      fixed_decision_label = factor(fixed_decision_label, levels = unique(decision_order)) |>
        # display names from R/nicknames.R, keeping the row order
        fct_relabel(nn),
      correlation_label = if_else(
        is.na(mean_rank_correlation),
        "NA",
        # round first and add 0, so that values rounding to zero from below
        # show as 0.00 rather than -0.00
        formatC(round(mean_rank_correlation, 2) + 0, digits = 2, format = "f")
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
    plot <- plot + geom_text(aes(label = correlation_label, color = label_color), size = value_size) +
      scale_color_identity()
  }

  if (add_average) {
    plot <- plot + geom_hline(yintercept = 1.5, color = "black", linewidth = 0.5)
  }

  plot
}

# Compact styling for the stability heatmaps as small paper figures (e.g. two
# side by side at 3.2in wide): smaller text, multi-word decision names wrapped
# onto separate lines, and a slim colour legend at the side. Use together with
# `value_size = 1.6` in the heatmap functions. `left_margin` (in points) leaves
# room for the first rotated x-axis label when it is wider than the decision
# names, e.g. the long method pairs of the inter-method heatmap (use 22 there).
theme_stability_compact <- function (left_margin = 2) {
  list(
    theme(
      text = element_text(size = 7),
      axis.text = element_text(size = 6.5),
      legend.position = "right",
      legend.title = element_text(size = 6),
      legend.text = element_text(size = 5.5),
      legend.key.width = unit(0.08, "in"),
      legend.key.height = unit(0.22, "in"),
      legend.margin = margin(0, 0, 0, 0),
      legend.box.spacing = unit(0.05, "in"),
      plot.margin = margin(2, 2, 2, left_margin)
    ),
    # 11, not 10: label_wrap() keeps lines shorter than the width, so 10 would
    # split 10-character labels like "X Variable"
    scale_y_discrete(labels = scales::label_wrap(11))
  )
}

# Give stability heatmaps that are saved as separate figures the same space
# for axis labels, legend and margins, so that when saved at the same width
# and height their heatmap panels come out exactly the same size and in the
# same place (e.g. the inter- and intra-method heatmaps placed side by side).
# Returns the plots as a list, in the order given.
align_stability_plots <- function (...) {
  plots <- list(...)
  # patchwork fixes the label space using the font metrics of the currently
  # open device; measure on a PDF device, as the plots are saved as PDFs
  # (screen and PNG devices measure the text smaller, clipping the labels)
  grDevices::pdf(NULL)
  on.exit(grDevices::dev.off())
  dims <- patchwork::get_max_dim(plots)
  lapply(plots, patchwork::set_dim, dim = dims)
}

vis_method_stability <- vis_inter_method_stability
