"""Application package and Flask application factory."""

import os
from datetime import datetime

from flask import Flask, render_template, request, send_from_directory, session
from werkzeug.exceptions import HTTPException

from app.cli import register_cli
from app.config import Config
from app.database import initialize_database
from app.extensions import csrf, db
from app.routes import register_blueprints
from app.utils.auth import current_admin, current_user


def create_app(config_object=None):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object or Config)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "profiles"), exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "reports"), exist_ok=True)

    db.init_app(app)
    csrf.init_app(app)

    if not app.debug and app.config.get("SECRET_KEY") in {None, "", "dev-change-this-secret-key"}:
        app.logger.warning("SECRET_KEY is not set to a unique value. Set it in the environment before deploying.")

    register_blueprints(app)

    @app.context_processor
    def inject_globals():
        return {
            "SITE_NAME": app.config.get("SITE_NAME"),
            "current_user": current_user(),
            "current_admin": current_admin(),
            "is_administrator": bool(session.get("admin_id")),
            "current_year": datetime.now().year,
        }

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        user = current_user()
        admin = current_admin()
        if not user and not admin:
            return render_template("errors/403.html"), 403
        if filename.startswith("profiles/"):
            return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
        if admin:
            return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
        if user and filename.startswith(f"reports/{user.user_id}/"):
            return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
        return render_template("errors/403.html"), 403

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning("Bad request on %s: %s", request.path, getattr(error, "description", "invalid request"))
        return render_template("errors/400.html"), 400

    @app.errorhandler(401)
    def unauthorized(_error):
        app.logger.warning("Unauthorized request on %s", request.path)
        return render_template("errors/401.html"), 401

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        app.logger.warning("Method %s not allowed on %s", request.method, request.path)
        return render_template("errors/405.html"), 405

    @app.errorhandler(413)
    def request_too_large(_error):
        app.logger.warning("Request too large on %s", request.path)
        return render_template("errors/413.html"), 413

    @app.errorhandler(429)
    def too_many_requests(_error):
        app.logger.warning("Rate limit reached on %s", request.path)
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        app.logger.exception("Internal server error on %s: %s", request.path, error)
        return render_template("errors/500.html"), 500

    @app.errorhandler(Exception)
    def unhandled_error(error):
        if isinstance(error, HTTPException):
            status = error.code if error.code in {400, 401, 403, 404, 405, 413, 429} else 500
            app.logger.warning("Unhandled HTTP %s on %s", error.code, request.path)
            return render_template(f"errors/{status}.html"), status
        db.session.rollback()
        app.logger.exception(error)
        return render_template("errors/500.html"), 500

    initialize_database(app)
    register_cli(app)
    return app


__all__ = ["create_app"]