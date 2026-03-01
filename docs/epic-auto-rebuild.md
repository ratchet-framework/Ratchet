# Epic 5: Auto-rebuild Pipeline for Mission Control

## Problem

**INC-008:** Sub-agents modify Next.js source in `second-brain/src/` but forget to run `npm run build` and restart the service. PROCESS.md says "you must rebuild" — but that's advisory. Agents skip it. Users see stale or crashing builds.

## Solution: Systemd Path Watcher + Debounced Build Script

### Architecture

```
File change in src/ → systemd PathChanged trigger → second-brain-watcher.service
  → bin/rebuild-console (flock + debounce) → npm run build
    → success: systemctl restart second-brain
    → failure: alert Aaron via Telegram, keep old build running
```

### Components

| File | Purpose |
|------|---------|
| `/etc/systemd/system/second-brain-watcher.service` | Long-running inotifywait watcher service |
| `/root/.openclaw/workspace/bin/watch-and-rebuild-console` | inotifywait loop with debounce, build, restart, alerting |
| `/root/.openclaw/workspace/bin/rebuild-console` | Manual rebuild script (flock-guarded, same alerting) |

**Note:** Initially designed with systemd `PathChanged` units, but those don't watch recursively. Switched to `inotifywait -r` for proper recursive monitoring of the entire `src/` tree.

### Design Decisions

#### Why systemd path watcher over git hooks?

| | Systemd Path Watcher | Git Post-Commit Hook |
|-|----------------------|---------------------|
| Triggers on file save | ✅ Yes | ❌ Only on commit |
| Works if agent forgets to commit | ✅ Yes | ❌ No |
| Debouncing | Via flock + sleep in script | Same |
| Complexity | Low (3 files) | Lower (1 file) but less reliable |

**Decision: Systemd path watcher.** The whole problem is agents forgetting steps. A git hook adds another step to forget. The path watcher is fully mechanical — no agent cooperation needed.

#### Debouncing

Systemd `PathChanged` fires once per directory modification batch (not per-file), but rapid sequential writes can still trigger multiple activations. The build script uses:

1. **`flock -n`** — If a build is already running, exit immediately
2. **5-second sleep** — After trigger, wait for writes to settle before building

This means: first file change starts a 5s timer, build runs, and any changes during the build are caught by flock (skipped) but will re-trigger the path unit after the build completes.

#### During Build (~60s)

The old build keeps serving. This is acceptable:
- Old build is functional (just missing new features)
- Zero-downtime is maintained
- A "building" UI indicator is nice-to-have but not worth the complexity for an internal tool

#### Failure Handling

If `npm run build` fails:
- Service is **not** restarted (old build keeps running)
- Build errors logged to `/var/log/second-brain-build.log`
- Telegram alert sent to Aaron with last 20 lines of error output
- Agent can fix the code and the watcher will auto-trigger again

### Testing

```bash
# Trigger a rebuild:
touch /root/.openclaw/workspace/second-brain/src/app/layout.tsx

# Watch the log:
tail -f /var/log/second-brain-build.log

# Check watcher status:
systemctl status second-brain-watcher.path
systemctl status second-brain-watcher.service
```

### Manual Override

```bash
# Force rebuild anytime:
/root/.openclaw/workspace/bin/rebuild-console
```

## Impact

- **Before:** Advisory PROCESS.md line. Agents forget. Users see crashes.
- **After:** Mechanical. Any file change in `src/` triggers build automatically. No agent cooperation required. Failures alert Aaron. Old build stays up on failure.

This is a ratchet click: the class of problem "agent forgets to rebuild" is mechanically eliminated.
