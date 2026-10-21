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

# Fill scale of the stability heatmaps. With `include_negative`, the scale
# spans the full correlation range from -1 to 1; otherwise it only spans 0 to 1
# (for multiverses without negative correlations), with any negative values
# squished onto 0.
stability_fill_scale <- function (include_negative, fill_option) {
  scale_fill_viridis_c(
    limits = if (include_negative) c(-1, 1) else c(0, 1),
    oob = scales::squish,
    option = fill_option
  )
}

# Value labels are white on the dark lowest quarter of the fill scale
stability_label_color <- function (correlation, include_negative) {
  dark_below <- if (include_negative) -0.5 else 0.25
  if_else(!is.na(correlation) & correlation < dark_below, "white", "black")
}

vis_inter_method_stability <- function (inter_method_stability_summary,
                                        baseline_label = "Full Multiverse",
                                        show_values = TRUE,
                                        add_average = TRUE,
                                        fill_label = "Mean rank\ncorrelation",
                                        fill_option = "viridis",
                                        include_negative = TRUE,
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
      label_color = stability_label_color(mean_rank_correlation, include_negative)
    )

  plot <- ggplot(
    plot_data,
    aes(x = comparison, y = fixed_decision_label, fill = mean_rank_correlation)
  ) +
    geom_tile() +
    stability_fill_scale(include_negative, fill_option) +
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

# Correlation-matrix view of inter-method stability: one tile per method pair,
# showing the pair's mean rank correlation averaged over all rows of the
# inter-method heatmap (the full multiverse and every fixed decision), i.e. the
# values of that heatmap's "Average" row. Only the lower triangle is drawn.
# Use the same `fill_option` and `include_negative` as the matching
# vis_inter_method_stability() plot.
vis_inter_method_matrix <- function (inter_method_stability_summary,
                                     include_baseline = TRUE,
                                     show_values = TRUE,
                                     fill_label = "Mean rank\ncorrelation",
                                     fill_option = "viridis",
                                     include_negative = TRUE,
                                     value_size = 3) {
  if (!include_baseline) {
    inter_method_stability_summary <- inter_method_stability_summary |>
      filter(fixed_decision != "full_multiverse")
  }

  plot_data <- inter_method_stability_summary |>
    mutate(
      # order the two methods within each pair canonically, so that each pair
      # falls into the lower triangle
      swap_methods = method_rank(method_x) > method_rank(method_y),
      method_first = if_else(swap_methods, method_y, method_x),
      method_second = if_else(swap_methods, method_x, method_y)
    ) |>
    group_by(method_first, method_second) |>
    summarise(mean_rank_correlation = safe_mean(mean_rank_correlation), .groups = "drop")

  # every method but the last on the x-axis, every method but the first on the
  # y-axis (top to bottom), so the tiles form a lower triangle
  methods <- order_methods(c(plot_data$method_first, plot_data$method_second))
  x_levels <- head(methods, -1)
  y_levels <- rev(methods[-1])

  plot_data <- plot_data |>
    mutate(
      method_first = factor(nn(method_first), levels = nn(x_levels)),
      method_second = factor(nn(method_second), levels = nn(y_levels)),
      correlation_label = if_else(
        is.na(mean_rank_correlation),
        "NA",
        # round first and add 0, so that values rounding to zero from below
        # show as 0.00 rather than -0.00
        formatC(round(mean_rank_correlation, 2) + 0, digits = 2, format = "f")
      ),
      label_color = stability_label_color(mean_rank_correlation, include_negative)
    )

  plot <- ggplot(
    plot_data,
    aes(x = method_first, y = method_second, fill = mean_rank_correlation)
  ) +
    geom_tile() +
    stability_fill_scale(include_negative, fill_option) +
    coord_equal() +
    labs(x = NULL, y = NULL, fill = fill_label) +
    theme_classic() +
    theme(axis.text.x = element_text(angle = 45, hjust = 1))

  if (show_values) {
    plot <- plot + geom_text(aes(label = correlation_label, color = label_color), size = value_size) +
      scale_color_identity()
  }

  plot
}

vis_intra_method_stability <- function (intra_method_stability_summary,
                                        show_values = TRUE,
                                        add_average = TRUE,
                                        fill_label = "Mean rank\ncorrelation",
                                        fill_option = "mako",
                                        include_negative = TRUE,
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
      label_color = stability_label_color(mean_rank_correlation, include_negative)
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
    stability_fill_scale(include_negative, fill_option) +
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
