# Discord Setup — Signal Routing Layer for Pawl

**Purpose:** Separate signal channels so Aaron's Telegram stays clean (only things requiring action) while Discord shows the ops dashboard (briefings, alerts, sub-agent work, system health).

**Time estimate:** 30 minutes end-to-end.

---

## Step 1: Create the Discord server

1. Go to [discord.com](https://discord.com)
2. Log in or sign up
3. Click the **+** icon on the left sidebar
4. Select **Create a server**
5. Name it: "Pawl Ops" (or whatever you prefer)
6. Accept the defaults, complete setup
7. You now have a private server for Pawl

---

## Step 2: Create the channels

In your new server, create these channels (right-click in the left sidebar, **Create Channel**):

| Channel | Purpose | Visibility |
|---------|---------|-----------|
| `#conversation` | Aaron ↔ Pawl dialogue | Private (for you only initially) |
| `#autonomous` | Sub-agent completions, background work output | Private |
| `#alerts` | Cadence alerts, incident reports, service warnings | Private |
| `#briefings` | Morning briefing, weekly review | Private |
| `#system` | Heartbeat status, service health, cron logs | Private |
| `#memory` | Memory management (promotion/purge reports) | Private |

**Leave `#general` for now** — you can use it later or delete it.

---

## Step 3: Create a Discord bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application**
3. Name it: "Pawl" (or similar)
4. Go to the **Bot** tab on the left
5. Click **Add Bot**
6. Under TOKEN, click **Copy** — this is your bot token (keep it secret)
7. Store the token securely (you'll give this to OpenClaw)

---

## Step 4: Give the bot permissions

1. Still in the Developer Portal, go to **OAuth2** → **URL Generator**
2. Under "Scopes," select:
   - `bot`
3. Under "Permissions," select:
   - `Send Messages`
   - `Read Message History`
   - `Manage Messages` (optional, for cleanup)
   - `Embed Links`
4. Copy the generated URL at the bottom
5. Paste it into your browser and authorize the bot to your "Pawl Ops" server
6. The bot should now appear in your server's member list as "Pawl#XXXX"

---

## Step 5: Get your server ID and channel IDs

1. In Discord, enable **Developer Mode**: User Settings → App Settings → Advanced → Developer Mode (toggle on)
2. Right-click your server name → **Copy Server ID** — save this as `DISCORD_GUILD_ID`
3. Right-click each channel name → **Copy Channel ID** — save these:
   - `#conversation` → `CONVERSATION_CHANNEL_ID`
   - `#autonomous` → `AUTONOMOUS_CHANNEL_ID`
   - `#alerts` → `ALERTS_CHANNEL_ID`
   - `#briefings` → `BRIEFINGS_CHANNEL_ID`
   - `#system` → `SYSTEM_CHANNEL_ID`
   - `#memory` → `MEMORY_CHANNEL_ID`

---

## Step 6: Configure OpenClaw for Discord

On your droplet, edit the OpenClaw gateway config (usually `~/.openclaw/gateway.config.yaml` or similar):

```yaml
channels:
  discord:
    enabled: true
    token: "<YOUR_BOT_TOKEN>"
    guildId: "<DISCORD_GUILD_ID>"
    routing:
      conversation: "<CONVERSATION_CHANNEL_ID>"
      autonomous: "<AUTONOMOUS_CHANNEL_ID>"
      alerts: "<ALERTS_CHANNEL_ID>"
      briefings: "<BRIEFINGS_CHANNEL_ID>"
      system: "<SYSTEM_CHANNEL_ID>"
      memory: "<MEMORY_CHANNEL_ID>"
```

Replace all `<...>` values with the IDs you collected in Step 5.

---

## Step 7: Update routing rules

In your OpenClaw session/cron config, set the target channel based on message type:

```
# In session config or cron job definition:
output_channel: "discord:conversation"    # For Aaron-facing dialogue
output_channel: "discord:autonomous"      # For sub-agent completions
output_channel: "discord:alerts"          # For incident/cadence alerts
output_channel: "discord:briefings"       # For morning briefing, weekly review
output_channel: "discord:system"          # For heartbeat, cron status
output_channel: "discord:memory"          # For memory-manage reports
```

Exact syntax depends on your OpenClaw version — check the OpenClaw docs or ask Pawl for the current pattern.

---

## Step 8: Test

1. Restart OpenClaw gateway: `openclaw gateway restart`
2. Send a test message to the bot in Discord (direct message or mention in a channel)
3. Verify it routes correctly to `#conversation`
4. Trigger a heartbeat cron manually to test `#system` routing
5. If all checks pass, you're done

---

## What happens next

- **Aaron's Telegram:** Now receives only messages that need action (live conversation with Pawl)
- **Discord #conversation:** Same as Telegram (live dialogue)
- **Discord #autonomous:** Sub-agent completions, research results, builds in progress
- **Discord #alerts:** Overdue maintenance, incidents, service warnings (if any)
- **Discord #briefings:** Morning summary, weekly review (no longer noise in Telegram)
- **Discord #system:** Heartbeat OK, service restarts, cron logs (ambient visibility)
- **Discord #memory:** "Promoted X facts to MEMORY.md," "Purged Y facts" (weekly)

This lets Aaron check Discord when he wants detailed context, while keeping Telegram clean for urgent items.

---

## Troubleshooting

**Bot doesn't appear in server after OAuth:** Re-check the bot's permissions in OAuth2. Make sure `bot` scope is selected.

**Messages don't route to Discord:** Check that the channel IDs are correct (copy them again directly from Discord). Verify the config syntax matches your OpenClaw version.

**Bot can't send messages:** Check that the bot has `Send Messages` permission in the server. Right-click the bot in the member list → **Manage User** → verify permissions.

**Missing a channel:** If you realize you need another channel later (e.g., `#experiments`), just create it, get the ID, add it to the config, and restart OpenClaw.

---

## Next steps

Once Discord is running, consider:
1. Pin a summary of CURRENT.md to `#conversation` for quick context
2. Set up message reactions (👍 for acknowledgment, etc.)
3. Archive old channels periodically to keep the workspace clean
4. Later: add other people with read-only access to `#alerts` and `#briefings` (if you want to share Pawl's work with a team)
