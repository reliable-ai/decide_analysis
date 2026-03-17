suppressPackageStartupMessages({
  library(tidyverse)
  library(broom)
  library(here)
  library(tidygraph)
  library(ggraph)
  library(reticulate)
})

# Load all scripts in the R directory, which do *not* start with a `_`
lapply(
  list.files(path = "R/", pattern = "^[^_].*\\.R$", full.names = TRUE),
  source
)

# Set default theme
theme_set(theme_classic())
