# Roadmap identity repair

AgentDesk uses ticket UUIDs as durable internal identities and `ticket_key` as the single human-facing identity.

The original bootstrap created milestone epics before roadmap stories, which caused the seeded roadmap code embedded in a story title (for example `AD-10 Repository registration`) to disagree with the generated `ticket_key` (for example `AD-21`).

`just bootstrap` now runs an idempotent repair after normal roadmap enrichment:

- roadmap stories receive `AD-1` through `AD-27`
- milestone epics receive `AD-28` through `AD-37`
- UUIDs, parent/child links, dependencies, events, and workspace records are unchanged
- non-roadmap tickets are never renumbered
- repair fails rather than overwrite a non-roadmap ticket occupying a canonical key
- existing Git branch names are not renamed

Future tickets continue from the highest sequence as normal.
