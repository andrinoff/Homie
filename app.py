"""
Homie - Family Utility App
Main application module using Supabase Authentication
"""

import logging
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from supabase import Client, create_client

from authentication import admin_required, clear_session, login_required

# Import custom modules
from config import (
    get_app_config,
    get_currency_symbol,
    get_supabase_config,
    load_access_control,
    setup_logging,
)

# ADDED UserModel to this import
from database import UserModel, get_dashboard_stats, get_recent_activities, init_db

# Import route blueprints
from routes.shopping import shopping_bp
from security import csrf_protect, generate_csrf_token

logger = logging.getLogger(__name__)


def create_app():
    """Application factory"""
    # Initialize Flask app
    app = Flask(__name__)

    # Setup logging
    setup_logging()

    # Load configuration
    app_config = get_app_config()
    app.config.update(app_config)

    # Initialize rate limiting
    limiter = Limiter(
        app=app, key_func=get_remote_address, default_limits=["1000 per hour"]
    )

    # Initialize database
    # Note: db_instance will be None because your init_db() returns nothing.
    # We pass it anyway to maintain your structure.
    db_instance = init_db()

    # Initialize Supabase
    supabase_config = get_supabase_config()
    supabase: Client = None
    if supabase_config:
        try:
            # Explicitly passing only url and key to avoid "unexpected keyword argument" errors
            supabase = create_client(
                supabase_url=supabase_config["url"], supabase_key=supabase_config["key"]
            )
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
    else:
        logger.warning("Supabase configuration missing. Authentication will fail.")

    # Load access control
    access_control = load_access_control()

    # Template context processors
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf_token)

    @app.context_processor
    def inject_currency():
        return dict(currency=get_currency_symbol())

    @app.context_processor
    def inject_user_features():
        if "user" in session:
            from database import get_all_user_features

            try:
                user_features = get_all_user_features(session["user"]["id"])
                return dict(user_features=user_features)
            except Exception as e:
                logger.error(f"Error loading user features: {e}")
                return dict(
                    user_features={
                        "shopping": True,
                        "chores": True,
                        "tracker": True,
                        "bills": True,
                        "budget": True,
                    }
                )
        return dict(user_features={})

    # Filters
    @app.template_filter("title_case")
    def title_case_filter(text):
        if not text:
            return text
        return " ".join(word.capitalize() for word in str(text).split())

    @app.template_filter("format_date")
    def format_date_filter(date_string, format_str="%B %d, %Y"):
        if not date_string:
            return ""
        try:
            from datetime import datetime

            if isinstance(date_string, str):
                for fmt in [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                ]:
                    try:
                        dt = datetime.strptime(date_string, fmt)
                        return dt.strftime(format_str)
                    except ValueError:
                        continue
            return str(date_string)
        except Exception:
            return str(date_string)

    # ===== ROUTES =====

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """Handle login with Supabase"""
        if "user" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            if not supabase:
                flash("Authentication service unavailable", "error")
                return render_template("login.html")

            email = request.form.get("email")
            password = request.form.get("password")

            try:
                # 1. Authenticate with Supabase
                res = supabase.auth.sign_in_with_password(
                    {"email": email, "password": password}
                )

                if res.user:
                    # 2. Check strict allowlist (if configured)
                    allowed_emails = access_control.get("allowed_emails", [])
                    admin_emails = access_control.get("admin_emails", [])

                    if allowed_emails and email.lower() not in [
                        e.lower() for e in allowed_emails
                    ]:
                        # Allow admins through even if not in allowed_emails explicitly
                        if email.lower() not in [e.lower() for e in admin_emails]:
                            logger.warning(
                                f"Login denied for {email}: Not in allowed list"
                            )
                            supabase.auth.sign_out()
                            flash("Access denied. You are not authorized.", "error")
                            return render_template("login.html")

                    # 3. Sync user to local DB for foreign keys
                    # We pass None or db_instance based on your database.py requirements
                    user_model = UserModel()
                    local_user = user_model.get_or_create_supabase_user(
                        res.user, access_control
                    )

                    # 4. Set session
                    session["user"] = {
                        "id": local_user["id"],
                        "supabase_id": local_user.get(
                            "supabase_id", local_user.get("oidc_sub")
                        ),
                        "username": local_user["username"],
                        "email": local_user["email"],
                        "full_name": local_user["full_name"],
                        "is_admin": local_user["is_admin"],
                        "access_token": res.session.access_token,
                    }

                    flash(f"Welcome back, {local_user['full_name']}!", "success")
                    return redirect(url_for("dashboard"))

            except Exception as e:
                logger.error(f"Login failed: {e}")
                flash("Invalid email or password", "error")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        """Logout user"""
        if supabase and "user" in session:
            try:
                supabase.auth.sign_out()
            except Exception as e:
                logger.warning(f"Supabase signout warning: {e}")

        clear_session()
        flash("You have been logged out", "info")
        return redirect(url_for("login"))

    @app.route("/")
    def index():
        if "user" in session:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        try:
            stats = get_dashboard_stats()
            recent_activities = get_recent_activities(limit=5)
            return render_template(
                "dashboard.html", recent_activities=recent_activities, **stats
            )
        except Exception as e:
            logger.error(f"Dashboard error: {e}")
            flash("Error loading dashboard", "error")
            return render_template(
                "dashboard.html",
                shopping_count=0,
                chores_count=0,
                expiring_count=0,
                monthly_total=0,
                recent_activities=[],
            )

    @app.route("/unauthorized")
    def unauthorized():
        return render_template("unauthorized.html")

    @app.route("/manifest.json")
    def manifest():
        return send_from_directory("static", "manifest.json")

    # Register Blueprints
    app.register_blueprint(shopping_bp)

    from routes.admin import admin_bp
    from routes.bills import bills_bp
    from routes.chores import chores_bp
    from routes.expiry import expiry_bp

    app.register_blueprint(chores_bp)
    app.register_blueprint(bills_bp)
    app.register_blueprint(expiry_bp)
    app.register_blueprint(admin_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(
        debug=os.getenv("FLASK_DEBUG", "False").lower() == "true",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
    )
