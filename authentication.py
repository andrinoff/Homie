"""
Authentication utilities for Homie Flask application
"""

import logging
from functools import wraps

from flask import flash, jsonify, redirect, session, url_for

from security import csrf_protect

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Custom exception for authentication errors"""

    pass


def login_required(f):
    """Decorator to require authentication for routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges for routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))

        user = session["user"]
        if not user.get("is_admin", False):
            return redirect(url_for("unauthorized"))

        return f(*args, **kwargs)

    return decorated_function


def api_auth_required(f):
    """Decorator for API endpoints that require authentication"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)

    return decorated_function


def feature_required(feature_name):
    """Decorator to require a specific feature to be enabled for the user"""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))

            # Import here to avoid circular imports
            from database import get_user_feature_visibility

            user_id = session["user"]["id"]

            # Check if user has access to this feature
            if not get_user_feature_visibility(user_id, feature_name):
                logger.warning(
                    f"User {user_id} attempted to access disabled feature: {feature_name}"
                )
                return redirect(url_for("unauthorized"))

            return f(*args, **kwargs)

        return decorated_function

    return decorator


@csrf_protect
def clear_session():
    """Safely clear the user session"""
    session.clear()
