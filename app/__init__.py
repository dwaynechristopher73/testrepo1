import os
import base64
import tempfile

from flask import Flask

from config import config_map
from app.database import init_db


def create_app(config_name='development'):
    app = Flask(__name__, instance_relative_config=False)

    cfg = config_map.get(config_name, config_map['development'])
    app.config.from_object(cfg)

    _setup_google_credentials(app)
    _ensure_directories(app)

    with app.app_context():
        init_db(app.config['DATABASE_PATH'])

    from app.routes.inventory import inventory_bp
    from app.routes.checkout import checkout_bp
    from app.routes.dashboard import dashboard_bp

    app.register_blueprint(inventory_bp)
    app.register_blueprint(checkout_bp)
    app.register_blueprint(dashboard_bp)

    return app


def _setup_google_credentials(app):
    b64 = app.config.get('GOOGLE_CREDENTIALS_B64')
    if not b64:
        return
    try:
        json_bytes = base64.b64decode(b64)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        tmp.write(json_bytes)
        tmp.flush()
        tmp.close()
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = tmp.name
    except Exception as e:
        app.logger.warning(f'Failed to set up Google credentials: {e}')


def _ensure_directories(app):
    for path in [app.config['UPLOAD_FOLDER'],
                 os.path.dirname(app.config['DATABASE_PATH'])]:
        os.makedirs(path, exist_ok=True)
