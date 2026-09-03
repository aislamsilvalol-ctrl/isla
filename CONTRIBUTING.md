# Contributing

ISLA is one process and one file of state, on purpose. Changes that keep it
that way are the easiest to merge.

Read the honesty rules in the README first. A change that makes ISLA invent
a number, hide a source's real freshness or mix simulated with real data
won't be merged.

## Setup

```bash
git clone https://github.com/aislamsilvalol-ctrl/isla
cd isla
python -m venv .venv && source .venv/bin/activate
pip install -e ".[serve,llm]" pytest
python -m pytest -q
```

## Adding a source

Sources are plain functions that return normalised signals. The contract
and an example are in [docs/SOURCE_SDK.md](docs/SOURCE_SDK.md). Declare the
source's real freshness and use an official or public API.

## Pull requests

- One change per PR, with a test when behaviour changes.
- Commit prefixes: `feat`, `fix`, `docs`, `refactor`, `security`, `chore`.
- CI runs the tests on Python 3.11 and 3.12.

Security issues go through [SECURITY.md](SECURITY.md), not the issue tracker.
