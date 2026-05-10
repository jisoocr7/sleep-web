"""WSGI entry point for PythonAnywhere deployment."""
import sys
import os

# Add the project directory to the path
project_home = '/home/sleepwell/sleep_web_mvp'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables if needed
os.environ['FLASK_ENV'] = 'production'

# Import the Flask app from server.py
from server import app as application
