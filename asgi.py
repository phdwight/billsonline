from asgiref.wsgi import WsgiToAsgi

from app import create_app


# Create the Flask WSGI app and wrap it for ASGI servers (e.g., Uvicorn/Hypercorn)
flask_app = create_app()
app = WsgiToAsgi(flask_app)
