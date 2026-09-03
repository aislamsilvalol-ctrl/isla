# Contributing to ISLA

Thanks for looking. ISLA is small on purpose: one process, one file of state.
Contributions that keep it that way are the easiest to merge.

## Ground rules

Read the honesty rules in the README first. A PR that makes ISLA invent a
number, hide a source's real freshness or mix simulated with real data will
not be merged, no matter how nice the UI looks.

## Setup

```bash
git clone https://github.com/aislamsilvalol-ctrl/isla
cd isla
python -m venv .venv && source .venv/bin/activate
pip install -e ".[serve,llm]" pytest
python -m pytest -q
```

## Adding a source

Sources are plain functions returning normalised signals. The contract and a
worked example are in [docs/SOURCE_SDK.md](docs/SOURCE_SDK.md). Every new
source must declare its true freshness and use an official or public API.

## Pull requests

- One change per PR, with a test when behaviour changes.
- Commit messages in the form `feat:`, `fix:`, `docs:`, `refactor:`,
  `security:`, `chore:`.
- CI must pass. It runs the test suite on Python 3.11 and 3.12 and a
  non-blocking dependency audit.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Do not open public issues for
vulnerabilities.
