# Admin Utilities

This folder contains command-line utilities for managing the Django backend.

## 📂 Core Utilities (Root)
Safe, reusable tools for day-to-day management and auditing.
- `user_management.py`: Interactive tool to create super admins and reset passwords.
- `check_database_health.py`: Audit script to check DB integrity.
- `search_users.py`: Find users by various criteria.
- `verify_permissions.py`: Check permission assignments.
- `full_audit.py`: Comprehensive system state audit.

## ⚠️ Danger Zone (`/danger_zone`)
**BECAREFUL:** These scripts modify or delete data.
- They are intended for repair, initialization, or deep cleaning.
- They contain warnings at the top of the file.
- **Do not run these automatedly.**
- Includes: `force_clean.py`, `remove_old_invoices.py`, `enable_support.py` (permission fix), etc.

## Usage
Run these scripts via the Django shell or directly if they configure Django setup:
```bash
python manage.py shell < admin_utilities/script_name.py
# OR if they have __main__:
python admin_utilities/script_name.py
```
