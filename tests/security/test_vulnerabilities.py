# Test file for Bandit Python security analysis - Vulnerable code patterns
# This file intentionally contains security vulnerabilities for validation
# DO NOT USE THESE PATTERNS IN PRODUCTION CODE

import hashlib
import os
import pickle
import subprocess

import yaml


# ============================================================================
# SQL Injection Vulnerabilities
# ============================================================================
def unsafe_sql_query_fstring(user_id):
    """SQL injection via f-string - VULNERABLE"""
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query


def unsafe_sql_query_concat(username):
    """SQL injection via string concatenation - VULNERABLE"""
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    return query


def unsafe_sql_query_format(email):
    """SQL injection via % formatting - VULNERABLE"""
    query = "SELECT * FROM users WHERE email = '%s'" % email
    return query


# ============================================================================
# Command Injection Vulnerabilities
# ============================================================================
def unsafe_command_shell_true(filename):
    """Command injection via shell=True - VULNERABLE"""
    subprocess.call(f"cat {filename}", shell=True)


def unsafe_command_os_system(path):
    """Command injection via os.system - VULNERABLE"""
    os.system(f"ls -la {path}")


def unsafe_command_popen(directory):
    """Command injection via os.popen - VULNERABLE"""
    result = os.popen(f"find {directory} -name '*.py'").read()
    return result


# ============================================================================
# Insecure Deserialization
# ============================================================================
def unsafe_pickle_loads(data):
    """Insecure deserialization via pickle - VULNERABLE"""
    return pickle.loads(data)


def unsafe_pickle_load(file_obj):
    """Insecure deserialization via pickle.load - VULNERABLE"""
    return pickle.load(file_obj)


# ============================================================================
# Weak Cryptography
# ============================================================================
def weak_hash_md5(password):
    """Weak cryptographic hash (MD5) - VULNERABLE"""
    return hashlib.md5(password.encode()).hexdigest()


def weak_hash_sha1(data):
    """Weak cryptographic hash (SHA1) - VULNERABLE"""
    return hashlib.sha1(data.encode()).hexdigest()


# ============================================================================
# Unsafe YAML Loading
# ============================================================================
def unsafe_yaml_load(yaml_string):
    """Unsafe YAML deserialization - VULNERABLE"""
    return yaml.load(yaml_string)


def unsafe_yaml_load_with_loader(yaml_string):
    """Unsafe YAML deserialization with Loader - VULNERABLE"""
    return yaml.load(yaml_string, Loader=yaml.Loader)


# ============================================================================
# Code Execution Vulnerabilities
# ============================================================================
def unsafe_eval(user_input):
    """Dangerous use of eval - VULNERABLE"""
    result = eval(user_input)
    return result


def unsafe_exec(code_string):
    """Dangerous use of exec - VULNERABLE"""
    exec(code_string)


# ============================================================================
# Hardcoded Credentials (for testing)
# ============================================================================
def get_hardcoded_password():
    """Hardcoded password - VULNERABLE"""
    password = "SuperSecret123!"
    return password


def get_database_credentials():
    """Hardcoded database credentials - VULNERABLE"""
    db_config = {
        "host": "localhost",
        "user": "admin",
        "password": "admin123",
        "database": "production_db",
    }
    return db_config
