# pcs_multiverse

## Development

Dependencies are managed via `uv`. For information on how to install `uv`, please refer to [official installation instructions](https://docs.astral.sh/uv/getting-started/installation/).

To install all dependencies, run:

```bash
uv sync --dev
```

### Formatting

We're using `ruff` for formatting of code. You can autoformat and lint code by running: 

```bash
ruff check . --fix && ruff format .
```
