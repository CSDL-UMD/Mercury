from flask import Flask
import logging
from werkzeug.middleware.proxy_fix import ProxyFix

import json
import logging.config
import logging.handlers
import pathlib


def setup_logger():
    logger = logging.getLogger("mercury")
    config_file = pathlib.Path("logging_configs/configs.json")
    with open(config_file) as f_in:
        config = json.load(f_in)

    logging.config.dictConfig(config)

    return logger


def create_app():
    app = Flask(__name__)

    app.debug = True
    # setup_logger()
    from . import database
    database.init_app(app)

    from . import auth_qualtrics
    app.register_blueprint(auth_qualtrics.bp)

    from . import health
    app.register_blueprint(health.bp)

    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
