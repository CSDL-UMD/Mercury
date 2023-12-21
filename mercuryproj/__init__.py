from flask import Flask
import logging


def create_app():
    app_dev = Flask(__name__)

    app_dev.debug = True

    log_level = logging.INFO
    logging.basicConfig(filename='mercuryproj.log', level=log_level)

    from . import auth_qualtrics
    app_dev.register_blueprint(auth_qualtrics.bp)

    from . import database
    app_dev.register_blueprint(database.bp)

    return app_dev


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
