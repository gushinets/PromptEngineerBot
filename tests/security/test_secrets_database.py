# Test file for GitLeaks secrets detection - Database credentials
# This file intentionally contains sample secrets for validation
# DO NOT USE THESE CREDENTIALS IN PRODUCTION

# Sample database connection strings with passwords
DATABASE_URL = "postgresql://admin:SuperSecret123@localhost:5432/mydb"

# MySQL example
MYSQL_URL = "mysql://root:MyPassword456@db.example.com:3306/production"

# MongoDB example
MONGO_URI = "mongodb://dbuser:SecurePass789@mongo.example.com:27017/app_db"


def get_db_connection():
    """Example function with hardcoded database URL"""
    return "postgresql://user:HardcodedPass999@prod-db.example.com/main"
