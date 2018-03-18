from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import config

bootstrap = Bootstrap()
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.session_protection = 'strong'  # 安全等级,设为"strong"时，Flask-Login 会记录客户端 IP
# 地址和浏览器的用户代理信息，如果发现异动就登出用户。
login_manager.login_view = 'user.login'  # 设置登陆页面的端点


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    bootstrap.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)

    # 附加路由和自定义的错误页面

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .user import user as user_blueprint
    app.register_blueprint(user_blueprint, url_prefix='/user')  # 使用url_prefix注册的路由都会加上该前缀

    from .blockchain import blockchain as blockchain_blueprint
    app.register_blueprint(blockchain_blueprint, url_prefix='/blockchain')

    return app
