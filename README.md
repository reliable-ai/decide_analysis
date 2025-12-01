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

### Tests

Tests are located in the `tests/` directory. You can run all tests using `pytest`:

```bash
uv run pytest
```

Among other types, the project uses snapshot tests via `syrupy` 📸. To update snapshots, run:

```bash
uv run pytest --update-snapshots
```

## Loading Data

As the data files are highly sensitive and need to stay encrypted, we use different approaches to loading data for different platforms.

Data loading code is located in `read_data/read_data.py`, which is not tracked in version control. You can find a boilerplate version of this file in `read_data/_read_data.py`.
