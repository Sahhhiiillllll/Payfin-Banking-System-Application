"""Register all API blueprints."""

from routes.auth import auth_bp
from routes.accounts import accounts_bp
from routes.transactions import transactions_bp
from routes.upi import upi_bp
from routes.gateway import gateway_bp
from routes.security import security_bp
from routes.webhooks import webhooks_bp
from routes.statements import statements_bp


def register_routes(app):
  app.register_blueprint(auth_bp)
  app.register_blueprint(accounts_bp)
  app.register_blueprint(transactions_bp)
  app.register_blueprint(upi_bp)
  app.register_blueprint(gateway_bp)
  app.register_blueprint(security_bp)
  app.register_blueprint(webhooks_bp)
  app.register_blueprint(statements_bp)
