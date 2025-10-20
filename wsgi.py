from app import create_app

app = create_app()

if __name__ == "__main__":
    # Single-process debug server with hot reload
    app.run(host="127.0.0.1", port=5001, debug=True, use_reloader=True)
