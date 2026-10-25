import logging
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import django
import webview
from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from platformdirs import user_data_dir
from waitress import create_server


def configure_runtime():
    data_dir = Path(
        os.environ.get("ROHGPT_DATA_DIR")
        or user_data_dir("RohGPT", "Rohan Bramhankar")
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["ROHGPT_DATA_DIR"] = str(data_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    os.environ.setdefault("DJANGO_DEBUG", "false")
    os.environ.setdefault("DJANGO_SECURE_SSL_REDIRECT", "false")
    os.environ.setdefault("DJANGO_SESSION_COOKIE_SECURE", "false")
    os.environ.setdefault("DJANGO_CSRF_COOKIE_SECURE", "false")
    os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
    os.environ.setdefault("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    secret_path = data_dir / "django-secret-key"
    try:
        secret_key = secret_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        secret_key = secrets.token_urlsafe(48)
        try:
            with secret_path.open("x", encoding="utf-8") as secret_file:
                secret_file.write(secret_key)
        except FileExistsError:
            secret_key = secret_path.read_text(encoding="utf-8").strip()
    if not secret_key:
        raise RuntimeError("RohGPT's local app key file is empty.")
    os.environ["DJANGO_SECRET_KEY"] = secret_key
    logging.basicConfig(
        filename=data_dir / "rohgpt-desktop.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def wait_for_server(url, server_thread):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and server_thread.is_alive():
        try:
            with urllib.request.urlopen(url, timeout=1):
                return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.1)
    raise RuntimeError("RohGPT's local web server did not start.")


def main():
    configure_runtime()
    django.setup()
    call_command("migrate", interactive=False, verbosity=0)

    application = get_wsgi_application()
    server = create_server(application, host="127.0.0.1", port=0)
    url = f"http://127.0.0.1:{server.effective_port}/"
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()

    try:
        wait_for_server(url, server_thread)
        webview.create_window("RohGPT", url, width=1280, height=850, min_size=(800, 600))
        webview.start(debug=False)
    except Exception:
        logging.exception("RohGPT desktop startup failed.")
        raise
    finally:
        server.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("RohGPT desktop app exited with an error.")
        try:
            import tkinter
            from tkinter import messagebox

            root = tkinter.Tk()
            root.withdraw()
            messagebox.showerror("RohGPT could not start", str(exc))
            root.destroy()
        except Exception:
            print(f"RohGPT could not start: {exc}", file=sys.stderr)
        raise
