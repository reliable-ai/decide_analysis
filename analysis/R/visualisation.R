vis_multiverse_tree <- function(
  mv,
  dim_prefix = "mv_dim_",
  direction = c("down", "up", "left", "right"),
  show_labels = FALSE,
  label_depth = NULL,
  label_size = 3,
  show_dots = c("none", "coloured", "black"),
  show_decision_labels = c("text", "coloured", "none"),
  decision_label_pos = 0.6
) {
  direction <- match.arg(direction)
  show_dots <- match.arg(show_dots)
  show_decision_labels <- match.arg(show_decision_labels)

  dim_cols <- grep(paste0("^", dim_prefix), names(mv), value = TRUE)
  dim_names <- sub(paste0("^", dim_prefix), "", dim_cols)

  # Only keep combinations that actually exist in the data
  paths <- mv %>%
    select(all_of(dim_cols)) %>%
    distinct()

  # Build nodes and edges from existing paths
  nodes <- tibble(id = 1L, label = "root", depth = 0L, decision = "")
  edges <- tibble(from = integer(), to = integer())
  node_map <- new.env(hash = TRUE, parent = emptyenv())
  node_map[["root"]] <- 1L
  next_id <- 2L

  for (i in seq_along(dim_cols)) {
    sub_paths <- paths %>%
      select(all_of(dim_cols[1:i])) %>%
      distinct()

    for (r in seq_len(nrow(sub_paths))) {
      vals <- as.character(unlist(sub_paths[r, ]))
      parent_key <- if (i == 1) "root" else paste(vals[1:(i - 1)], collapse = "|")
      current_key <- paste(vals, collapse = "|")

      if (is.null(node_map[[current_key]])) {
        node_map[[current_key]] <- next_id
        nodes <- bind_rows(nodes, tibble(
          id = next_id,
          label = vals[i],
          depth = as.integer(i),
          decision = dim_names[i]
        ))
        edges <- bind_rows(edges, tibble(
          from = node_map[[parent_key]],
          to = next_id
        ))
        next_id <- next_id + 1L
      }
    }
  }

  graph <- tbl_graph(nodes = nodes, edges = edges)
  lay <- create_layout(graph, layout = "dendrogram")
  lay_df <- as_tibble(lay)
  is_horizontal <- direction %in% c("left", "right")

  p <- ggraph(lay) +
    geom_edge_diagonal(colour = "grey60")

  # Dots
  if (show_dots == "coloured") {
    p <- p +
      geom_node_point(aes(filter = depth > 0, colour = decision), size = 3) +
      labs(colour = "Decision")
  } else if (show_dots == "black") {
    p <- p +
      geom_node_point(aes(filter = depth > 0), size = 2, colour = "grey30")
  }

  # Decision labels
  if (show_decision_labels %in% c("coloured", "text")) {
    # Position labels between parent and child y-levels (midpoint of the split)
    depth_y <- lay_df %>%
      filter(depth > 0) %>%
      group_by(depth) %>%
      summarise(child_y = mean(y), .groups = "drop")
    parent_y <- lay_df %>%
      group_by(depth) %>%
      summarise(parent_y = mean(y), .groups = "drop") %>%
      mutate(depth = depth + 1L)
    decision_annot <- depth_y %>%
      left_join(parent_y, by = "depth") %>%
      mutate(
        parent_y = coalesce(parent_y, child_y + 1),
        y_pos = child_y + (parent_y - child_y) * decision_label_pos,
        decision = dim_names[depth]
      )

    x_range <- range(lay_df$x)
    x_offset <- diff(x_range) * 0.06 + 0.2
    decision_annot <- decision_annot %>%
      mutate(x_pos = x_range[1] - x_offset)

    if (show_decision_labels == "coloured") {
      p <- p +
        geom_text(
          data = decision_annot,
          aes(x = x_pos, y = y_pos, label = decision, colour = decision),
          hjust = 1, size = label_size, fontface = "bold",
          show.legend = FALSE, inherit.aes = FALSE
        ) +
        scale_x_continuous(expand = expansion(mult = c(0.15, 0.05)))
    } else {
      p <- p +
        geom_text(
          data = decision_annot,
          aes(x = x_pos, y = y_pos, label = decision),
          hjust = 1, size = label_size, fontface = "bold",
          inherit.aes = FALSE
        ) +
        scale_x_continuous(expand = expansion(mult = c(0.15, 0.05)))
    }
  }

  # Node option labels
  if (show_labels) {
    max_label_depth <- if (is.null(label_depth)) max(nodes$depth) else label_depth

    if (is_horizontal) {
      p <- p + geom_node_text(
        aes(filter = depth > 0 & depth <= !!max_label_depth, label = label),
        angle = 0, hjust = 0.5, nudge_x = -0.3, size = label_size
      )
    } else {
      p <- p + geom_node_text(
        aes(filter = depth > 0 & depth <= !!max_label_depth, label = label),
        angle = 90, hjust = 1, nudge_y = -0.1, size = label_size
      )
    }
  }

  # Direction: transform coordinates to orient the tree
  if (direction == "up") {
    p <- p + scale_y_reverse()
  } else if (direction == "right") {
    p <- p + scale_y_reverse() + coord_flip()
  } else if (direction == "left") {
    p <- p + coord_flip()
  }

  p + theme_void() +
    coord_cartesian(clip = "off")
}
