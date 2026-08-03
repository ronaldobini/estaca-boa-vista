from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "ebv.login"
login_manager.login_message = "Inicie sessão para continuar."
login_manager.session_protection = None
