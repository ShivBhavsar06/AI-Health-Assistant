from extensions import db


def initialize_database(app) -> None:
    """Create tables and apply the legacy MySQL ID/timestamp compatibility fixes."""
    with app.app_context():
        db.create_all()
        from sqlalchemy import inspect, text

        _add_missing_health_record_columns(inspect, text)
        if db.engine.dialect.name != "mysql":
            return

        from sqlalchemy import Integer

        _drop_retired_feature_tables(text)
        _migrate_legacy_integer_ids(inspect, Integer, text)
        _migrate_feedback_rating(inspect, Integer, text)

        timestamp_columns = {
            "admins": "created_at",
            "users": "created_at",
            "medicines": "created_at",
            "health_records": "updated_at",
        }
        for table_name, column_name in timestamp_columns.items():
            table_columns = {column["name"] for column in inspect(db.engine).get_columns(table_name)}
            if column_name not in table_columns:
                db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} DATETIME NULL"))
        db.session.commit()

        inspector = inspect(db.engine)
        user_id_column = next(
            column for column in inspector.get_columns("users") if column["name"] == "user_id"
        )
        if isinstance(user_id_column["type"], Integer):
            user_foreign_keys = []
            for table_name in inspector.get_table_names():
                for foreign_key in inspector.get_foreign_keys(table_name):
                    if foreign_key.get("referred_table") == "users" and "user_id" in foreign_key.get(
                        "constrained_columns", []
                    ):
                        user_foreign_keys.append((table_name, foreign_key))
                        db.session.execute(
                            text(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{foreign_key['name']}`")
                        )

            db.session.execute(text("ALTER TABLE users MODIFY COLUMN user_id VARCHAR(20) NOT NULL"))
            for table_name, foreign_key in user_foreign_keys:
                constrained_column = foreign_key["constrained_columns"][0]
                child_column = next(
                    column for column in inspector.get_columns(table_name) if column["name"] == constrained_column
                )
                nullable = "NULL" if child_column["nullable"] else "NOT NULL"
                db.session.execute(
                    text(
                        f"ALTER TABLE `{table_name}` MODIFY COLUMN `{constrained_column}` "
                        f"VARCHAR(20) {nullable}"
                    )
                )
                on_delete = foreign_key.get("options", {}).get("ondelete")
                delete_clause = f" ON DELETE {on_delete}" if on_delete else ""
                db.session.execute(
                    text(
                        f"ALTER TABLE `{table_name}` ADD CONSTRAINT `{foreign_key['name']}` "
                        f"FOREIGN KEY (`{constrained_column}`) REFERENCES users (`user_id`){delete_clause}"
                    )
                )
            db.session.commit()
        admin_id_column = next(
            column for column in inspect(db.engine).get_columns("admins") if column["name"] == "admin_id"
        )
        if isinstance(admin_id_column["type"], Integer):
            db.session.execute(text("ALTER TABLE admins MODIFY COLUMN admin_id VARCHAR(20) NOT NULL"))
            db.session.commit()

        admin_columns = inspect(db.engine).get_columns("admins")
        admin_username = next((column for column in admin_columns if column["name"] == "username"), None)
        if admin_username and not admin_username["nullable"]:
            db.session.execute(text("ALTER TABLE admins MODIFY COLUMN username VARCHAR(50) NULL"))
            db.session.commit()

        health_indexes = inspect(db.engine).get_indexes("health_records")
        health_unique_constraints = inspect(db.engine).get_unique_constraints("health_records")
        has_unique_health_user = any(
            index.get("unique") and index.get("column_names") == ["user_id"] for index in health_indexes
        ) or any(
            constraint.get("column_names") == ["user_id"] for constraint in health_unique_constraints
        )
        if not has_unique_health_user:
            db.session.execute(
                text("ALTER TABLE `health_records` ADD UNIQUE INDEX `uq_health_records_user_id` (`user_id`)")
            )
            db.session.commit()


def _add_missing_health_record_columns(inspect, text) -> None:
    """Add new nullable lifestyle fields to existing health-record tables."""
    columns = {
        "smoking_status": "VARCHAR(30) NULL",
        "alcohol_use": "VARCHAR(30) NULL",
        "exercise_habits": "TEXT NULL",
        "diet": "TEXT NULL",
        "other_lifestyle": "TEXT NULL",
    }
    existing_columns = {column["name"] for column in inspect(db.engine).get_columns("health_records")}
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            db.session.execute(text(f"ALTER TABLE `health_records` ADD COLUMN `{column_name}` {column_type}"))
    db.session.commit()


def _drop_retired_feature_tables(text) -> None:
    """Remove tables from features intentionally excluded from the ERD."""
    for table_name in ("pending_registrations", "support_requests", "otp_challenges", "auth_throttles"):
        db.session.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
    db.session.commit()


def _migrate_legacy_integer_ids(inspect, integer_type, text) -> None:
    """Convert legacy numeric business keys without renaming tables or columns."""
    id_columns = {
        "medical_reports": "report_id",
        "medicines": "medicine_id",
        "appointments": "appointment_id",
        "health_records": "record_id",
        "reminders": "reminder_id",
        "feedback": "feedback_id",
    }
    foreign_keys = []
    inspector = inspect(db.engine)
    for table_name in inspector.get_table_names():
        for foreign_key in inspector.get_foreign_keys(table_name):
            constrained = set(foreign_key.get("constrained_columns") or [])
            referred_table = foreign_key.get("referred_table")
            if table_name == "reminders" and constrained.intersection({"medicine_id", "appointment_id"}):
                foreign_keys.append((table_name, foreign_key))
            elif referred_table in id_columns:
                foreign_keys.append((table_name, foreign_key))

    needs_migration = any(
        isinstance(column["type"], integer_type)
        for table_name, column_name in id_columns.items()
        for column in inspector.get_columns(table_name)
        if column["name"] == column_name
    )
    needs_migration = needs_migration or any(
        isinstance(column["type"], integer_type)
        for column_name in ("medicine_id", "appointment_id")
        for column in inspector.get_columns("reminders")
        if column["name"] == column_name
    )
    if not needs_migration:
        return

    for table_name, foreign_key in foreign_keys:
        name = foreign_key.get("name")
        if name:
            db.session.execute(text(f"ALTER TABLE `{table_name}` DROP FOREIGN KEY `{name}`"))

    for table_name, column_name in id_columns.items():
        column = next(column for column in inspector.get_columns(table_name) if column["name"] == column_name)
        if isinstance(column["type"], integer_type):
            nullable = "NULL" if column["nullable"] else "NOT NULL"
            db.session.execute(
                text(f"ALTER TABLE `{table_name}` MODIFY COLUMN `{column_name}` VARCHAR(20) {nullable}")
            )

    for column_name in ("medicine_id", "appointment_id"):
        column = next(column for column in inspector.get_columns("reminders") if column["name"] == column_name)
        if isinstance(column["type"], integer_type):
            nullable = "NULL" if column["nullable"] else "NOT NULL"
            db.session.execute(
                text(f"ALTER TABLE `reminders` MODIFY COLUMN `{column_name}` VARCHAR(20) {nullable}")
            )

    for table_name, foreign_key in foreign_keys:
        name = foreign_key.get("name")
        if not name:
            continue
        constrained = foreign_key["constrained_columns"][0]
        referred_table = foreign_key["referred_table"]
        referred_column = foreign_key["referred_columns"][0]
        options = foreign_key.get("options") or {}
        on_update = f" ON UPDATE {options['onupdate']}" if options.get("onupdate") else ""
        on_delete = f" ON DELETE {options['ondelete']}" if options.get("ondelete") else ""
        db.session.execute(
            text(
                f"ALTER TABLE `{table_name}` ADD CONSTRAINT `{name}` FOREIGN KEY "
                f"(`{constrained}`) REFERENCES `{referred_table}` (`{referred_column}`)"
                f"{on_update}{on_delete}"
            )
        )
    db.session.commit()


def _migrate_feedback_rating(inspect, integer_type, text) -> None:
    """Allow legacy feedback tables to store half-star ratings."""
    rating_column = next(
        column for column in inspect(db.engine).get_columns("feedback") if column["name"] == "rating"
    )
    if isinstance(rating_column["type"], integer_type):
        db.session.execute(text("ALTER TABLE `feedback` MODIFY COLUMN `rating` DECIMAL(2, 1) NOT NULL"))
        db.session.commit()