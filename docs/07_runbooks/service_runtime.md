# Runbook: launchd runtime service

## Install services

```bash
/Users/chappie/Projects/Agent.Chappie/scripts/install_services.sh
```

## Start or restart services

```bash
launchctl kickstart -k gui/$(id -u)/com.agentchappie.runtime
launchctl kickstart -k gui/$(id -u)/com.agentchappie.watchdog
```

## Check status

```bash
/Users/chappie/Projects/Agent.Chappie/scripts/status_services.sh
launchctl print gui/$(id -u)/com.agentchappie.runtime
launchctl print gui/$(id -u)/com.agentchappie.watchdog
cat /Users/chappie/Projects/Agent.Chappie/runtime_status/heartbeat.json
```

## Stop and remove services

```bash
/Users/chappie/Projects/Agent.Chappie/scripts/uninstall_services.sh
```

## Supervision model

- runtime service uses `KeepAlive=true`
- watchdog service uses `RunAtLoad=true` and `StartInterval=30`
- launchd handles crash restart
- watchdog handles stale recovery

## Bounded restart policy

- watchdog restart limit: 3 restarts per 300 seconds
- if the restart budget is exhausted, watchdog returns `restart_blocked`
- this avoids infinite restart storms

## Log locations

```bash
tail -n 50 /Users/chappie/Projects/Agent.Chappie/runtime_status/runtime_stdout.log
tail -n 50 /Users/chappie/Projects/Agent.Chappie/runtime_status/runtime_stderr.log
tail -n 50 /Users/chappie/Projects/Agent.Chappie/runtime_status/watchdog_stdout.log
tail -n 50 /Users/chappie/Projects/Agent.Chappie/runtime_status/watchdog_stderr.log
tail -n 50 /Users/chappie/Projects/Agent.Chappie/runtime_status/watchdog_log.jsonl
```
