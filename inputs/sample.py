"""
User search service.

Deliberately buggy — used to exercise the code-review loop.
Issues span multiple categories and severities so the Critic has things
to find when the Generator misses them.
"""
import sqlite3
import hashlib

DB_PATH = "/tmp/users.db"
ADMIN_PASSWORD = "admin123"  # security: hardcoded credential


def get_user_by_name(name):
    # security: SQL injection via string concatenation
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT * FROM users WHERE name = '" + name + "'"
    cursor.execute(query)
    result = cursor.fetchall()
    # bug: connection never closed
    return result


def hash_password(pw):
    # security: MD5 is broken for password hashing; no salt
    return hashlib.md5(pw.encode()).hexdigest()


def find_users(names):
    # performance: N queries instead of one IN clause; called in a loop
    out = []
    for n in names:
        users = get_user_by_name(n)
        for u in users:
            out.append(u)
    return out


def check_admin(pw):
    # security: comparing plaintext password
    if pw == ADMIN_PASSWORD:
        return True
    return False


def data(x):
    # naming: 'data' tells you nothing about what x is or what's returned
    # readability: dense one-liner
    return [i for i in x if i % 2 == 0 and i > 0 and len(str(i)) < 4]
