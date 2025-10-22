#!/bin/bash

# Events Manager Deployment Script
# This script deploys the Events Manager application to /var/www

set -e  # Exit on any error

echo "Starting Events Manager deployment..."

# Change to web directory
echo "Changing to /var/www directory..."
cd /var/www

# Backup .env file if it exists before removing directory
ENV_BACKUP_FILE=""
if [ -d "events-manager" ] && [ -f "events-manager/.env" ]; then
    echo "Backing up existing .env file..."
    ENV_BACKUP_FILE="/tmp/events_manager_env_backup_$(date +%Y%m%d_%H%M%S).env"
    cp "events-manager/.env" "$ENV_BACKUP_FILE"
    echo "✓ .env backed up to $ENV_BACKUP_FILE"
fi

# Remove existing events_manager folder if it exists
if [ -d "events-manager" ]; then
    echo "Removing existing events_manager directory..."
    sudo rm -IR 'events-manager'
fi

# Clone the repository
echo "Cloning Events Manager repository..."
git clone https://github.com/stanx89/events-manager.git

# Change to the project directory
echo "Entering events_manager directory..."
cd 'events-manager'

# Create Python virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install Python packages
echo "Installing Python packages..."
pip install --upgrade pip
pip install django gunicorn psycopg2-binary requests python-decouple

# Restore backed up .env file or create new one from example
if [ -n "$ENV_BACKUP_FILE" ] && [ -f "$ENV_BACKUP_FILE" ]; then
    echo "Restoring backed up .env file..."
    cp "$ENV_BACKUP_FILE" ".env"
    echo "✓ .env file restored from backup"
    # Clean up backup file
    rm "$ENV_BACKUP_FILE"
elif [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your actual database credentials!"
else
    echo "✓ .env file already exists"
fi

# Run Django migrations
echo "Running Django migrations..."
python manage.py makemigrations
python manage.py migrate

# Collect static files (if needed)
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Change ownership to nginx:nginx
echo "Changing ownership to nginx:nginx..."
sudo chown -R nginx:nginx '/var/www/events-manager'

# Restart gunicorn service
echo "Restarting gunicorn service..."
sudo systemctl restart gunicorn

echo "Deployment completed successfully!"
echo "Events Manager has been deployed to /var/www/events-manager"

# Display final status
echo ""
echo "=== Deployment Summary ==="
echo "✓ Existing .env file backed up and restored (if present)"
echo "✓ Repository cloned from GitHub"
echo "✓ Virtual environment created"
echo "✓ Dependencies installed"
echo "✓ Environment file (.env) configured"
echo "✓ Django migrations applied"
echo "✓ Static files collected"
echo "✓ Ownership changed to nginx:nginx"
echo "✓ Gunicorn service restarted"
echo ""
echo "Application is ready at: /var/www/events-manager"