# PostgreSQL Setup Instructions

## 1. Install PostgreSQL

### Option A: Using Homebrew (Recommended for macOS)
```bash
brew install postgresql@14
```

### Option B: Download from Official Website
- Go to https://www.postgresql.org/download/macos/
- Download and install PostgreSQL

### Option C: Using Postgres.app
- Go to https://postgresapp.com/
- Download and install Postgres.app

## 2. Start PostgreSQL Service

### If installed via Homebrew:
```bash
# Start PostgreSQL service
brew services start postgresql@14

# Add to PATH (add this to your ~/.zshrc or ~/.bash_profile)
export PATH="/usr/local/opt/postgresql@14/bin:$PATH"
```

### If installed via official installer or Postgres.app:
- The service should start automatically
- For Postgres.app, just open the app

## 3. Create Database and User

```bash
# Connect to PostgreSQL as superuser
psql postgres

# Create database
CREATE DATABASE events_db;

# Create user (optional - you can use the default postgres user)
CREATE USER events_user WITH ENCRYPTED PASSWORD 'your_password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE events_db TO events_user;

# Exit psql
\q
```

## 4. Update Django Settings

The settings.py has already been updated with:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'events_db',
        'USER': 'postgres',  # or 'events_user' if you created a specific user
        'PASSWORD': 'password',  # update with your actual password
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

## 5. Run Django Migrations

```bash
# Make migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser
```

## 6. Test Connection

```bash
# Test database connection
python manage.py dbshell
```

## Environment Variables (Recommended for Production)

Create a `.env` file in your project root:
```
DB_NAME=events_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
```

Then update settings.py to use environment variables:
```python
import os
from dotenv import load_dotenv

load_dotenv()

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'events_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'password'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}
```

## Troubleshooting

### Connection Issues:
- Make sure PostgreSQL service is running
- Check if the database exists
- Verify username and password
- Ensure PostgreSQL is listening on port 5432

### Permission Issues:
- Make sure the user has proper privileges
- Try connecting with the postgres superuser first

### Commands to Check Status:
```bash
# Check if PostgreSQL is running
brew services list | grep postgresql

# Connect to database
psql -d events_db -U postgres -h localhost

# List databases
\l

# List tables in current database
\dt
```