from auth import hash_password
from db import get_connection

username = "admin"
password = "admin123"
fullname = "Admin"

conn = get_connection()
cur = conn.cursor()

cur.execute("""
    INSERT INTO login (username, password_hash, fullname)
    VALUES (%s, %s, %s)
    ON CONFLICT (username) DO NOTHING
""", (username, hash_password(password), fullname))

conn.commit()
cur.close()
conn.close()

print("✅ Admin user inserted into login table.")
