from flask import Blueprint

bp = Blueprint("ai", __name__)

from . import routes
