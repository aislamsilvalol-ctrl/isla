# Security Policy

ISLA only talks to public, official APIs and stores everything in a local
SQLite file. The main things worth protecting are your BYOK credentials
(YouTube, Twitch, Reddit, Anthropic) and the machine you self-host it on.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.2.x   | yes       |
| < 0.2   | no        |

## Reporting a vulnerability

Use GitHub's private vulnerability reporting:
https://github.com/aislamsilvalol-ctrl/isla/security/advisories/new

Please do not open a public issue for anything that could leak credentials
or let a remote party run code on a host.

Include what you can: version, source connector involved, reproduction steps,
and impact as you understand it. You will get an acknowledgement within
72 hours and a fix or a mitigation plan within 14 days for confirmed issues.

<!-- A dedicated security mailbox will be listed here once it is live. -->

## Scope notes

- Secrets are read from environment variables only and never written to the
  database or to logs.
- Demo (simulated) data lives in a separate database and is labelled in the UI.
- The web UI and API bind to localhost by default; expose them deliberately.
