"""
Configuration utilities for Homie Flask application
"""

import logging
import os

logger = logging.getLogger(__name__)


def get_supabase_config():
    """Get Supabase configuration"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
        return None

    return {"url": url, "key": key}


def load_access_control():
    """Load access control configuration"""
    config = {"allowed_emails": [], "admin_emails": []}

    # Load admin emails
    admin_emails_str = os.getenv("ADMIN_EMAILS", "")
    if admin_emails_str:
        config["admin_emails"] = [
            email.strip().lower() for email in admin_emails_str.split(",")
        ]
        logger.info(
            f"Access control: Using ADMIN_EMAILS with {len(config['admin_emails'])} admin emails"
        )

    # Load allowed emails
    allowed_emails_str = os.getenv("ALLOWED_EMAILS", "")
    if allowed_emails_str:
        config["allowed_emails"] = [
            email.strip().lower() for email in allowed_emails_str.split(",")
        ]
        logger.info(
            f"Access control: Using ALLOWED_EMAILS with {len(config['allowed_emails'])} emails"
        )

    return config


def get_currency_symbol():
    """Get the currency symbol to use in the application"""
    return os.getenv("CURRENCY", "£")


def get_app_config():
    """Get Flask application configuration"""
    return {
        "SECRET_KEY": os.getenv("SECRET_KEY", "dev-key-change-in-production"),
        "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
        "SUPABASE_KEY": os.getenv("SUPABASE_KEY", ""),
        "BASE_URL": os.getenv("BASE_URL", "http://localhost:5000"),
        "RATELIMIT_STORAGE_URI": "memory://",
        "SESSION_COOKIE_SECURE": os.getenv("SESSION_COOKIE_SECURE", "False").lower()
        == "true",
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "PERMANENT_SESSION_LIFETIME": 86400 * 7,  # 7 days
        "MAX_CONTENT_LENGTH": 16 * 1024 * 1024,  # 16MB max upload
        "DEBUG": os.getenv("FLASK_DEBUG", "False").lower() == "true",
    }


def setup_logging():
    """Setup application logging"""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(level=getattr(logging, log_level), format=log_format)

    # Set specific logger levels
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("supabase").setLevel(logging.WARNING)
