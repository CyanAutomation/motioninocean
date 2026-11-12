"""WSGI entry point for production servers such as Gunicorn."""

import atexit

from .main import create_app_from_env, shutdown_app


app = create_app_from_env()
atexit.register(shutdown_app, app)
