import os

from monitor.runner import run_monitor


if __name__ == "__main__":
    app_mode = os.getenv("APP_MODE", "worker").strip().lower()
    if app_mode == "web":
        from monitor.web import app

        app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
    else:
        run_monitor()
