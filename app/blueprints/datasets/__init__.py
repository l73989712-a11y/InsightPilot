from flask import Blueprint

bp = Blueprint("datasets", __name__)

from . import routes
