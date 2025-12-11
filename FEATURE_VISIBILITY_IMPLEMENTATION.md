# Feature Visibility Implementation Summary

## Overview
Implemented a new admin feature that allows designated administrators (via OIDC) to control which features are visible to specific users. This enables parents to hide sensitive sections like Bills and Budget from children's accounts.

## Changes Made

### 1. Configuration (config.py)
- Added `ADMIN_EMAILS` environment variable support
- Modified `load_access_control()` to load admin emails from environment

### 2. Database (database.py)
- Created new `feature_visibility` table to track user-specific feature settings
- Added helper functions:
  - `get_all_users()` - Get all users in the system
  - `get_user_feature_visibility(user_id, feature_name)` - Check if feature is visible to user
  - `get_all_user_features(user_id)` - Get all feature settings for a user
  - `set_user_feature_visibility()` - Update feature visibility
  - `get_all_users_features()` - Get all users with their feature settings
- Modified `create_or_update_user()` to set `is_admin` flag based on ADMIN_EMAILS list

### 3. Admin Routes (routes/admin.py - NEW FILE)
Created new Blueprint with endpoints:
- `/admin/features` - Admin panel UI
- `/admin/api/users` - Get all users and their settings (JSON)
- `/admin/api/feature-visibility` - Update feature visibility (POST)

### 4. Templates
- **base.html**: 
  - Added Admin menu item in user dropdown (only visible to admins)
  - Updated navigation to conditionally show features based on user settings
  - Applied to both desktop and mobile navigation
  
- **admin_features.html** (NEW FILE):
  - Clean admin interface showing all users
  - Toggle switches for each feature per user
  - Real-time updates via AJAX
  - Toast notifications for feedback
  - Features: Shopping, Chores, Tracker, Bills, Budget

### 5. Application (app.py)
- Registered new `admin_bp` blueprint
- Added context processor `inject_user_features()` to load user's feature visibility into all templates

### 6. Environment Files
- Updated `.env` with ADMIN_EMAILS example
- Updated `.env.sample` with ADMIN_EMAILS documentation
- Updated `compose.yml` with ADMIN_EMAILS environment variable

### 7. Documentation (README.md)
- Added new "Admin Features" section
- Documented the Feature Visibility Control functionality
- Added setup instructions for ADMIN_EMAILS

## Features Controlled
The following features can be toggled per user:
1. **Shopping** - Shopping list management
2. **Chores** - Chore tracking
3. **Tracker** - Expiry date tracking
4. **Bills** - Bill management
5. **Budget** - Budget dashboard

## How It Works

### For Admins:
1. Set ADMIN_EMAILS in environment (e.g., `ADMIN_EMAILS=parent@example.com`)
2. Admin users see "Admin" option in user menu dropdown
3. Admin panel shows table of all users with toggle switches
4. Toggling features on/off takes effect immediately
5. Changes are stored in the database

### For Regular Users:
1. Navigation automatically hides features that are disabled
2. Works on both desktop and mobile views
3. If no specific settings exist, all features are visible by default
4. Only applies to OIDC users (local mode users see everything)

## Database Schema

```sql
CREATE TABLE feature_visibility (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    feature_name TEXT NOT NULL,
    is_visible BOOLEAN DEFAULT TRUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (updated_by) REFERENCES users (id),
    UNIQUE(user_id, feature_name)
);
```

## Security Considerations
- Admin routes protected with `@admin_required` decorator
- All POST requests protected with CSRF tokens
- Feature visibility changes logged with admin user ID
- Only works with OIDC authentication (more secure than local mode)

## Future Enhancements
Potential improvements:
- Granular permissions (read-only vs full access)
- Feature visibility schedules (time-based access)
- Audit log of admin changes
- Bulk actions (enable/disable feature for all users)
- Role-based templates (predefined feature sets)

## Testing Notes
To test the feature:
1. Set up OIDC authentication
2. Configure ADMIN_EMAILS with at least one admin user
3. Log in as admin and access Admin panel from user menu
4. Toggle features for different users
5. Log in as those users to verify features are hidden/shown correctly
