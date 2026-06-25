from pathlib import Path
import click
from flask import Flask, render_template
from config import Config
from .extensions import db, login_manager, csrf
from .models import User


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录后再访问该页面。"
    login_manager.login_message_category = "warning"

    for key in ("UPLOAD_FOLDER", "PROCESSED_FOLDER", "REPORT_FOLDER"):
        Path(app.config[key]).mkdir(parents=True, exist_ok=True)

    from .blueprints.auth import bp as auth_bp
    from .blueprints.main import bp as main_bp
    from .blueprints.datasets import bp as datasets_bp
    from .blueprints.analysis import bp as analysis_bp
    from .blueprints.ai import bp as ai_bp
    from .blueprints.reports import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(datasets_bp, url_prefix="/datasets")
    app.register_blueprint(analysis_bp, url_prefix="/analysis")
    app.register_blueprint(ai_bp, url_prefix="/ai")
    app.register_blueprint(reports_bp, url_prefix="/reports")

    @app.cli.command("init-db")
    def init_db():
        """创建全部数据库表。"""
        db.create_all()
        click.echo("数据库表创建完成。")

    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_user(username, password):
        """通过命令行创建用户。"""
        if User.query.filter_by(username=username).first():
            click.echo("用户名已存在。")
            return
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo("用户创建成功。")

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(_error):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    return app
