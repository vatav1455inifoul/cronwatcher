# cronwatcher

Lightweight daemon that monitors cron job execution times and alerts on missed or delayed runs.

---

## Installation

```bash
pip install cronwatcher
```

Or install from source:

```bash
git clone https://github.com/youruser/cronwatcher.git && cd cronwatcher && pip install .
```

---

## Usage

Define your monitored jobs in a `cronwatcher.yml` config file:

```yaml
jobs:
  daily-backup:
    schedule: "0 2 * * *"
    tolerance: 5m
    alert: email

  hourly-sync:
    schedule: "0 * * * *"
    tolerance: 2m
    alert: webhook
    webhook_url: https://hooks.example.com/notify
```

Start the daemon:

```bash
cronwatcher start --config cronwatcher.yml
```

Check status of monitored jobs:

```bash
cronwatcher status
```

Wrap an existing cron command to report execution:

```bash
cronwatcher run --job daily-backup -- /usr/local/bin/backup.sh
```

---

## Configuration Options

| Key | Description | Default |
|-----------|--------------------------------------|---------|
| `schedule` | Cron expression for expected run time | required |
| `tolerance` | Allowed delay before alerting | `1m` |
| `alert` | Alert method (`email`, `webhook`, `log`) | `log` |

---

## License

MIT © 2024 cronwatcher contributors