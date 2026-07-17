from asgiref.wsgi import WsgiToAsgi, WsgiToAsgiInstance

from app import create_app


class _ContentLengthWsgiToAsgiInstance(WsgiToAsgiInstance):
    def build_environ(self, scope, body):
        environ = super().build_environ(scope, body)
        # asgiref buffers the entire request body before invoking the WSGI
        # app, but only sets CONTENT_LENGTH when the request carried a
        # Content-Length header. Proxies (e.g. Cloudflare tunnel) may forward
        # POST bodies chunked without one; Werkzeug then treats the body as
        # empty, so forms arrive blank and CSRF validation fails. The body is
        # fully buffered here, so declare the stream terminated (which makes
        # Werkzeug read it to EOF even for chunked requests) and report its
        # real size.
        environ["wsgi.input_terminated"] = True
        if "CONTENT_LENGTH" not in environ:
            position = body.tell()
            body.seek(0, 2)
            environ["CONTENT_LENGTH"] = str(body.tell())
            body.seek(position)
        return environ


class ContentLengthWsgiToAsgi(WsgiToAsgi):
    async def __call__(self, scope, receive, send):
        await _ContentLengthWsgiToAsgiInstance(self.wsgi_application)(
            scope, receive, send
        )


# Create the Flask WSGI app and wrap it for ASGI servers (e.g., Uvicorn/Hypercorn)
flask_app = create_app()
app = ContentLengthWsgiToAsgi(flask_app)
