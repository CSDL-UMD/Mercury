from flask import Flask
import logging


def create_app():
    app = Flask(__name__)

    app.debug = True
    logging.basicConfig(level=logging.INFO)

    from . import database
    database.init_app(app)

    from . import auth_qualtrics
    app.register_blueprint(auth_qualtrics.bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
