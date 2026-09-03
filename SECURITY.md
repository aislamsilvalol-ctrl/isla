# Security

ISLA talks only to public APIs and keeps its state in a local SQLite file.
What matters most: your BYOK credentials (YouTube, Twitch, Reddit,
Anthropic) and the host you run it on.

## Supported versions

0.2.x is supported. Older versions are not.

## Reporting

Use GitHub private vulnerability reporting:
https://github.com/aislamsilvalol-ctrl/isla/security/advisories/new

Or email contact@aislam.dev.

Don't open a public issue for anything involving credentials or remote code
execution. Include the version, the connector involved and steps to
reproduce. I answer within 72 hours.

## Notes

- Keys come from environment variables and are never written to the
  database or to logs.
- Demo data lives in a separate database and is labelled in the UI.
- The API and the UI bind to localhost by default.
