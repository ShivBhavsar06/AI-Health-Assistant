from routes.admin import admin_bp
from routes.ai import ai_bp
from routes.appointments import appointments_bp
from routes.auth import auth_bp
from routes.feedback import feedback_bp
from routes.health_records import health_records_bp
from routes.main import main_bp
from routes.medical_reports import medical_reports_bp
from routes.medicines import medicines_bp
from routes.reminders import reminders_bp
from routes.user import user_bp


def register_blueprints(app):
	for blueprint in (
		main_bp,
		auth_bp,
		user_bp,
		medicines_bp,
		reminders_bp,
		appointments_bp,
		health_records_bp,
		medical_reports_bp,
		feedback_bp,
		admin_bp,
		ai_bp,
	):
		app.register_blueprint(blueprint)
