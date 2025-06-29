import bcrypt
from db import get_connection

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def get_user(username):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT username, password_hash, fullname FROM login WHERE username = %s", (username,))
        row = cur.fetchone()
        return dict(zip(["username", "password_hash", "fullname"], row)) if row else None
    except Exception as e:
        print(f"[Auth Error] {e}")
        return None
    finally:
        if 'conn' in locals():
            cur.close()
            conn.close()
