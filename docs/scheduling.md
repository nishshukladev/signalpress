# Scheduling recipes

signalpress has no built-in scheduler (see decisions.md D13). Pick one:

## cron (Linux) / launchd-friendly (macOS)

```cron
# daily digest at 07:00, weekly report Saturday 08:00
0 7 * * *  cd ~/newsletters/mine && ~/.local/bin/signalpress daily
0 8 * * 6  cd ~/newsletters/mine && ~/.local/bin/signalpress weekly
```

Export your provider key in the crontab or a sourced env file (`ANTHROPIC_API_KEY=...`).

## GitHub Actions (recommended — shipped with the repo)

The repo ships a ready workflow: [`.github/workflows/signalpress.yml`](../.github/workflows/signalpress.yml).
Fork-and-go:

1. Fork the repo and enable Actions (scheduled workflows are off by default in forks).
2. Locally: `uv run signalpress init`, edit `newsletter.yaml`, then commit it with
   `git add -f newsletter.yaml` (it's gitignored in the template so the source repo stays
   config-free).
3. Add `ANTHROPIC_API_KEY` (or `OPENAI_API_KEY` + change models in the config) as a repo secret.

The workflow runs the daily digest at 07:00 UTC and the weekly report Saturday 08:00 UTC,
then commits `signalpress.db` and `digests/` back — git is the persistence layer, and every
day's state is a commit. A `concurrency` group queues overlapping runs (Saturday fires both
crons; daily lands first, then weekly reads the week's rows). Trigger ad-hoc runs from the
Actions tab via `workflow_dispatch`.

Note: Actions runners use datacenter IPs — every v1 source works from them, but any future
`scrape-local` source (e.g. X) will not; run those locally via cron.
