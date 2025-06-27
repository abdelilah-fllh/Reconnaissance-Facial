import psycopg2

DB_PARAMS = {
    "host": "localhost",
    "database": "test",
    "user": "postgres",
    "password": "1234"
}

def get_connection():
    return psycopg2.connect(**DB_PARAMS)