"""
ASGI entrypoint alias so platforms that run `uvicorn main:app` can import the app.
This forwards to the ASGI app defined in `asgi.py`.
"""
from asgi import app  # noqa: F401  # re-export for Uvicorn