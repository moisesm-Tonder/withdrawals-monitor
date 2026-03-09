# Railway Deployment

## Runtime
- Service type: Worker
- Start command: `python main.py`
- `Procfile` already included.

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

## Build
- Railway will install from `requirements.txt`.

## Schedule
- Recommended: run every 5 minutes using Railway Cron.
