from flask import Blueprint


main = Blueprint('main', __name__)


from . import views, errors  # 放在后面避免循环导入
