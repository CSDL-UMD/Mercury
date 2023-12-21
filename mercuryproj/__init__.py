from flask import Flask
import logging


def create_app():
    app_dev = Flask(__name__)

    app_dev.debug = True

    logging.basicConfig(level=logging.INFO)

    from . import auth_qualtrics
    app_dev.register_blueprint(auth_qualtrics.bp)

    return app_dev


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
