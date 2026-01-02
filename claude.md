# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Living Documentation

This project uses `docs.md` as living documentation that should be kept current with the codebase.

### When to update docs.md

After completing any task that involves:
- Adding new features or components
- Changing architecture or project structure
- Introducing new patterns, conventions, or dependencies
- Modifying key entry points or APIs
- Making design decisions worth preserving

### How to update docs.md

- Keep it terse and high-signal — no filler
- Focus on architecture, patterns, entry points, and non-obvious gotchas
- Do NOT duplicate what's obvious from reading the code
- Update information in-place to reflect current state — this is not a changelog
- Remove outdated sections rather than adding "previously" notes

### What belongs in docs.md

- High-level architecture and system design
- Key entry points and where to start reading code
- Non-obvious patterns, conventions, or gotchas
- Important design decisions and rationale
- Critical dependencies or integration points

### What does NOT belong in docs.md

- Exhaustive file lists or function signatures
- Step-by-step implementation details
- Anything obvious from reading the source
- Generic development practices