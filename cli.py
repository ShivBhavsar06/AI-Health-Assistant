from extensions import db
from models import Admin
from utils.id_generator import PREFIXES, assign_new_id


def register_cli(app):
    @app.cli.command("allow-duplicate-user-emails")
    def allow_duplicate_user_emails():
        """Remove the legacy unique index on users.email, if present."""
        from sqlalchemy import inspect, text

        if db.engine.dialect.name != "mysql":
            print("This migration is only needed for MySQL installations.")
            return
        inspector = inspect(db.engine)
        for index in inspector.get_indexes("users"):
            columns = index.get("column_names") or []
            if index.get("unique") and [column.lower() for column in columns] == ["email"]:
                db.session.execute(text(f"ALTER TABLE users DROP INDEX `{index['name']}`"))
                db.session.commit()
                print(f"Removed unique users.email index {index['name']}")
                return
        print("No unique users.email index found.")

    @app.cli.command("create-admin")
    def create_admin():
        import getpass

        email = input("Admin email: ").strip().lower()
        name = input("Full name: ").strip() or "System Administrator"
        password = getpass.getpass("Password: ")
        if Admin.query.filter_by(email=email).first():
            print("An administrator with this email already exists.")
            return
        admin = Admin(full_name=name, email=email)
        assign_new_id(admin, PREFIXES["admin"], "admin_id")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        print(f"Created administrator {admin.admin_id}")

    @app.cli.command("reset-admin-password")
    def reset_admin_password():
        import getpass

        email = input("Admin email: ").strip().lower()
        admin = Admin.query.filter_by(email=email).first()
        if not admin:
            print("No administrator found with that email.")
            return
        password = getpass.getpass("New password: ")
        confirmation = getpass.getpass("Confirm new password: ")
        if not password:
            print("Password cannot be empty.")
            return
        if password != confirmation:
            print("Passwords do not match.")
            return
        admin.set_password(password)
        admin.session_version += 1
        db.session.commit()
        print(f"Updated password for administrator {admin.admin_id}")