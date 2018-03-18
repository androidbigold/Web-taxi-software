from flask import Blueprint


blockchain = Blueprint('blockchain', __name__)


from . import views, forms
