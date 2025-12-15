# Database and Authentication Setup - Updated

## Overview
The backend has been updated to properly initialize the database and create a default admin user automatically on first startup.

## Key Changes Made

### 1. **Fixed `create_admin.py`** 
   - Updated import paths to use proper `src.` module imports
   - Added better error handling and user feedback
   - Script now returns a boolean indicating success/failure
   - Properly uses the `users` table (not `user` table)
   - Can be run manually with: `python create_admin.py`

### 2. **Updated `src/app.py`**
   - Added automatic admin user creation on first startup
   - Admin user is created only if it doesn't already exist
   - Prevents duplicate admin entries
   - Logs all initialization steps
   - Handles errors gracefully without crashing the server

### 3. **Enhanced `start_server.sh`**
   - Cleans up old database files from incorrect locations
   - Ensures the correct database directory (`src/instance/`) is created
   - Displays default credentials after successful startup
   - Removes confusion from multiple database instances

### 4. **New `initialize_db.sh`** Script
   - Dedicated script for manual database initialization
   - Cleans up old database files
   - Creates the database and admin user
   - Useful for fresh setup or troubleshooting
   - Usage: `./initialize_db.sh`

## Database Location

⚠️ **Important:** The database is now stored at:
```
/Users/mohammadiqbal/Documents/Workspace/cron-job-backend/src/instance/cron_jobs.db
```

This aligns with the SQLAlchemy model's default instance folder. Old databases in other locations will be automatically cleaned up.

## Default Credentials

After the first startup, the default admin credentials are:
- **Username:** `admin`
- **Password:** `admin123`

⚠️ **IMPORTANT:** Change the admin password immediately after first login!

## How It Works

### First Time Setup
1. Run `./start_server.sh`
2. Server starts and automatically:
   - Creates all database tables
   - Creates the default admin user (if it doesn't exist)
   - Logs all initialization steps
3. Admin user is ready to use

### Subsequent Startups
1. Run `./start_server.sh`
2. Server starts and:
   - Checks if admin user exists
   - Skips creation if already present
   - Resumes normal operations

### Manual Initialization
If you need to reinitialize everything:
```bash
./initialize_db.sh
```

## Testing the Setup

### Using Postman
```
POST http://localhost:5001/api/auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

### Using curl
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

## Files Modified

1. ✅ `/create_admin.py` - Fixed imports and error handling
2. ✅ `/src/app.py` - Added automatic admin creation on startup
3. ✅ `/start_server.sh` - Added database cleanup and enhanced output
4. ✅ `/initialize_db.sh` - New manual initialization script

## Future Startup Procedures

Simply run:
```bash
./start_server.sh
```

The server will automatically:
- Initialize the database
- Create the admin user if needed
- Display the default credentials
- Start listening on port 5001

## Troubleshooting

### Admin user not created?
- Check the server logs for error messages
- Run `./initialize_db.sh` manually
- Verify the database directory exists: `src/instance/`

### Still getting 401 Unauthorized?
- Verify the admin user exists in the database
- Check that you're using the correct username (not email)
- Ensure the database file is at: `src/instance/cron_jobs.db`

### Multiple database files?
- Run `./start_server.sh` to clean up old files automatically
- Or manually run: `./initialize_db.sh`
