from flask import Blueprint


main = Blueprint('main', __name__)


from . import errors  # 放在后面避免循环导入
