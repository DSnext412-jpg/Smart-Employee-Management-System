import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# MySQL configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "employee360")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))

# Flask configuration
SECRET_KEY = os.getenv("SECRET_KEY", "a-dev-secret-key-change-in-production")
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Base directory
basedir = os.path.abspath(os.path.dirname(__file__))