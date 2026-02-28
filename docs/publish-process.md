# Publish Process — Ratcheting Up

Every time a meaningful capability is built, follow this process before considering it done.

## Steps

1. **Update getratchet.dev**
   - Add or update the feature card on `index.html`
   - Add `cadence.json`, new `bin/` tools, or other artifacts to the file structure display if relevant
   - Keep copy high-level and general — describe *what it does* and *why it matters*, not implementation details

2. **Update or create the concept doc**
   - `docs/<capability-name>.md` — explain the problem, the solution, and the data model
   - Reference real examples but sanitize any personal data

3. **Take screenshots from the demo environment**
   - Use `?demo=true` URLs only — never real data
   - Mobile + desktop if it's a UI capability
   - CLI output screenshots if it's a tool (use sanitized/example data)
   - Run `bin/screenshot-commit` to capture, commit, and update `docs/GALLERY.md`

4. **Commit and push**
   - `git add` all changed files in `ratchet/`
   - Commit message: `feat: <capability name> — <one line description>`
   - Push to `github.com/ratchet-framework/Ratchet`

5. **Close the GitHub Issue** (if one exists for this capability)

## What counts as "ratcheting up"

- New `bin/` tool that solves a class of problem
- New Ratchet primitive (cadence, notification routing, cost routing, etc.)
- New Mission Control page or major feature
- Significant improvement to an existing capability

## What doesn't need this process

- Bug fixes and minor patches
- Internal config changes with no user-facing impact
- Dependency updates

## Notes

- Screenshots require Aaron's machine (browser tool). If not available, commit the site/doc changes and note "screenshots pending" — take them next session.
- Never commit screenshots of real data. Demo environment only.
- The publish step is part of the capability, not an afterthought. Done = shipped + documented + published.
