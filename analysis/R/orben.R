# Takes importances_vec and aggregates any values whose name starts with
# `prefix` into a single entry named `col` (the original, non-expanded column
# name). This reverses expand_y_variable() for importance vectors, so it is a
# no-op when `importances_vec` already has a single mv_dim_y_variable entry.
aggregate_onehot_importances <- function(importances_vec, prefix = "mv_dim_y_",
                                          col = "mv_dim_y_variable") {
  matching_prefix <- names(importances_vec) |> str_starts(prefix)
  vec_new <- importances_vec[!matching_prefix]
  vec_new[col] <- sum(importances_vec[matching_prefix])
  vec_new
}

# mv_dim_y_variable is a comma-separated list of individual wellbeing variable
# names used in a given universe.  Having thousands of unique combinations makes
# every downstream method intractable.  We one-hot encode the individual
# variables instead: each unique item gets its own mv_dim_y_<name> binary
# column (1 = included, 0 = excluded), and the original string column is
# dropped.
expand_y_variable <- function(mv, dim_prefix = "mv_dim_",
                               col = "mv_dim_y_variable") {
  if (!col %in% names(mv)) return(mv)

  all_vars <- sort(unique(trimws(unlist(strsplit(as.character(mv[[col]]), ",")))))

  for (v in all_vars) {
    new_col <- paste0(dim_prefix, "y_", v)
    mv[[new_col]] <- as.integer(
      sapply(strsplit(as.character(mv[[col]]), ",\\s*"), function(x) v %in% trimws(x))
    )
  }

  mv |> select(-all_of(col))
}
