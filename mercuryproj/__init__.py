from flask import Flask
import logging
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app():
    app = Flask(__name__)

    app.debug = True
    logging.basicConfig(level=logging.INFO)

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
