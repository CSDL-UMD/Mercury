from flask import Blueprint
from . import database

bp = Blueprint("health", __name__, url_prefix="/health")


@bp.route('/check')
def check():
    db = database.getdb()
    cursor = db.cursor()
    cursor.execute("SELECT 1;")
    res = cursor.fetchone()
    return "healthy"
