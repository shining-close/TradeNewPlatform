When creating a database locally, you must first create a super administrator. 
Then log in to the login page using the super administrator account. 
Add "/admin" at the end of the URL. After that, you can enter the backend management. 
You need to create a new user, set it as an administrator on the super administrator page, 
and then log in with the newly created administrator account. 
You will be able to normally access the management backend link.
Cross-Border Trade Service Platform Project README

Project Introduction
This project is a cross-border trade service platform developed based on the Django framework. It supports multi-role (visitor, enterprise user, administrator) permission management and implements core business functions such as order publishing/management/favoriting, enterprise information management, logistics management, and administrator backend.
Runtime Environment Requirements
Python 3.10+
Django 6.0.3
MySQL 8.0+ (or a compatible database)

Runtime Environment Requirements
Python 3.10+
Django 6.0.3
MySQL 8.0+ (or a compatible database)

Quick Start Steps
# 1. Clone / Download the Project
Extract the project code to a local directory and enter the project root directory:
cd TradePlatformProject

# 2. Create & Activate Virtual Environment (Recommended)
Isolate project dependencies to avoid conflicts with your global Python environment:
# Create virtual environment (Python 3.8+ required)
python -m venv venv
# Activate virtual environment
# Windows (PowerShell/CMD):
venv\Scripts\activate


# 3.Install Dependencies
Run the following command to install the required dependency packages:
pip install -r requirements.txt

# 4. Database Configuration
# Option A: Use MySQL (Recommended for Production)
4.A1. Start MySQL Service: Ensure your local MySQL server is running (check via Services on Windows, systemctl status mysql on macOS/Linux).
4.A2.Create Database: Open your MySQL terminal/tool and run this SQL to create the database
CREATE DATABASE your_database_name DEFAULT CHARSET utf8mb4;
# ------------
4.A3.Edit Database Config: Open TradePlatform/settings.py and update the DATABASES block with your MySQL credentials:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'your_database_name',   # Match the database you just created
        'USER': 'your_database_username',  # Your MySQL username (e.g., root)
        'PASSWORD': 'your_database_password',  # Your MySQL password
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4'
        }
    }
}

# Option B: Use SQLite3 (Simpler for Testing, No MySQL Required)
Skip steps 4.A.1–4.A.3, and replace the entire DATABASES block in TradePlatform/settings.py with:
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
SQLite3 will automatically create a database file when you run migrations.

# 5.Database Migration
Run the following commands to create database table structures:
python manage.py makemigrations
python manage.py migrate

# 6. Create a Super Administrator
You will use this account to log in at http://127.0.0.1:8000/admin/.
python manage.py createsuperuser

# 7.Start the Project
After successful startup, visit the address: http://127.0.0.1:8000/
python manage.py runserver

Test Accounts (for functional verification)
Administrator: Manage all user, order, and logistics data
Enterprise User: Publish, edit, view, and favorite their own orders
Visitor	test_visitor: Browse the order list; operations require login

Core Function Description
Multi-role Permission Control: Strict isolation of permissions for visitors, enterprise users, and administrators.
Order Management: Enterprise users can publish supply/purchase orders; administrators can modify order statuses and delete orders.
Favorites Function: Enterprise users can favorite interested orders; the same order cannot be favorited repeatedly.
Logistics Management: Administrators can maintain logistics route information; enterprise users can select logistics methods when publishing orders.

Unit Test Instructions
The project contains 29 unit test cases covering core models and business logic. Run all tests with the following command:
python manage.py test trade administrator
A successful test run will display OK, indicating all test cases have passed verification.

Notes
Ensure that the MySQL service is installed and running locally, and that the database configuration matches settings.py.
To use the image upload function, ensure the media/ directory has write permissions.
Database migration commands must be executed on the first run; otherwise, a "table does not exist" error will occur.
