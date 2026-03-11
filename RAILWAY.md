# Railway Deployment

## Runtime
- Service type: Web Service
- Start command from `Procfile`:
  `gunicorn monitor.web:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 180`

## Required Environment Variables
- `AWS_REGION`
- `LOG_GROUP_NAME`
- `CLOUDWATCH_FILTER_PATTERN`
- `SLACK_WEBHOOK_URL`
- `WINDOW_MINUTES`
- `ANTHROPIC_API_KEY` (optional)
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` (optional for temporary creds)
- `ENABLE_SCHEDULER` (`true` or `false`)
- `SCHEDULE_EVERY_MINUTES` (recommended `5`)
- `RUN_TRIGGER_TOKEN` (recommended in production)

## Build
- Railway will install from `requirements.txt`.

## Endpoints
- `GET /health`: healthcheck
- `POST /run`: manual run trigger (use `X-Run-Token` header if `RUN_TRIGGER_TOKEN` is set)

## Scheduling Options
- Default: in-process scheduler (`ENABLE_SCHEDULER=true`).
- Alternative: disable scheduler and trigger `/run` from an external cron.

## Scheduling Options
- Default: in-process scheduler (`ENABLE_SCHEDULER=true`).
- Alternative: disable scheduler and trigger `/run` from an external cron.
