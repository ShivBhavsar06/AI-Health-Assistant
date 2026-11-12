from functools import wraps

from flask import abort, flash, redirect, session, url_for

from models.admin import Admin
from models.user import User


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return User.query.filter_by(user_id=user_id).first()


def current_admin():
    admin_id = session.get("admin_id")
    if not admin_id:
        return None
    return Admin.query.filter_by(admin_id=admin_id).first()


def login_required(view):
    """Protect user workspace pages. Administrators cannot use these routes."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("admin_id") and not session.get("user_id"):
            abort(403)
        if not session.get("user_id") or current_user() is None:
            session.pop("user_id", None)
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    """Protect administrator pages. Signed-in patients cannot use these routes."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") and not session.get("admin_id"):
            abort(403)
        if not session.get("admin_id") or current_admin() is None:
            session.pop("admin_id", None)
            flash("Please log in as an administrator.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def forbid_admin_as_user():
    if session.get("admin_id") and not session.get("user_id"):
        abort(403)
