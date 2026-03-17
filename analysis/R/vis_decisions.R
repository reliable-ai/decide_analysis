vis_decision <- function(mv, decision, colname_metric, facet = FALSE,
                         type = c("hist", "kde"), dim_prefix = "mv_dim_") {
  type <- match.arg(type)
  decision <- enquo(decision)
  decision_label <- sub(paste0("^", dim_prefix), "", as_label(decision))

  p <- ggplot(mv, aes(
    x = .data[[colname_metric]],
    fill = factor(!!decision),
    colour = factor(!!decision)
  ))

  if (type == "hist") {
    p <- p + geom_histogram(alpha = 0.6, position = "identity")
  } else {
    p <- p + geom_density(alpha = 0.4)
  }

  if (facet) {
    p <- p + facet_wrap(vars(!!decision), scales = "free_y")
  }

  p +
    labs(fill = decision_label, colour = decision_label, x = colname_metric) +
    theme_classic()
}

vis_two_decisions <- function(mv, decision1, decision2, colname_metric,
                              facet = FALSE, type = c("hist", "kde"),
                              dim_prefix = "mv_dim_") {
  type <- match.arg(type)
  decision1 <- enquo(decision1)
  decision2 <- enquo(decision2)
  label1 <- sub(paste0("^", dim_prefix), "", as_label(decision1))
  label2 <- sub(paste0("^", dim_prefix), "", as_label(decision2))

  if (facet) {
    p <- ggplot(mv, aes(
      x = .data[[colname_metric]],
      fill = factor(!!decision1),
      colour = factor(!!decision1)
    ))
    aes_label <- label1
  } else {
    mv <- mv |>
      mutate(.combined = interaction(!!decision1, !!decision2, sep = " / "))
    p <- ggplot(mv, aes(
      x = .data[[colname_metric]],
      fill = .combined,
      colour = .combined
    ))
    aes_label <- paste(label1, label2, sep = " / ")
  }

  if (type == "hist") {
    p <- p + geom_histogram(alpha = 0.6, position = "identity")
  } else {
    p <- p + geom_density(alpha = 0.4)
  }

  if (facet) {
    p <- p + facet_grid(rows = vars(!!decision1), cols = vars(!!decision2))
  }

  p <- p + labs(fill = aes_label, colour = aes_label, x = colname_metric)

  p + theme_classic()
}
