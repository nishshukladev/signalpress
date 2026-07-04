# Scheduling recipes

signalpress has no built-in scheduler (see decisions.md D13). Pick one:

## cron (Linux) / launchd-friendly (macOS)

```cron
# daily digest at 07:00, weekly report Saturday 08:00
0 7 * * *  cd ~/newsletters/mine && ~/.local/bin/signalpress daily
0 8 * * 6  cd ~/newsletters/mine && ~/.local/bin/signalpress weekly
```

Export your provider key in the crontab or a sourced env file (`ANTHROPIC_API_KEY=...`).

## GitHub Actions

Keep `newsletter.yaml`, the SQLite DB, and rendered digests in a private repo; the workflow
commits state back after each run.

```yaml
name: signalpress
on:
  schedule:
    - cron: "0 7 * * *"   # daily
    - cron: "0 8 * * 6"   # weekly
  workflow_dispatch:
jobs:
  run:
    runs-on: ubuntu-latest
    permissions: { contents: write }
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - run: uv tool install signalpress
      - name: Run
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          if [ "$(date +%u)" = 6 ] && [ "${{ github.event.schedule }}" = "0 8 * * 6" ]; then
            signalpress weekly
          else
            signalpress daily
          fi
      - name: Commit state
        run: |
          git config user.name signalpress-bot
          git config user.email bot@users.noreply.github.com
          git add -f signalpress.db digests/
          git commit -m "run: $(date -u +%F)" || echo "nothing to commit"
          git push
```

Note: Actions runners use datacenter IPs — every v1 source works from them, but any future
`scrape-local` source (e.g. X) will not; run those locally via cron.
