import mysql.connector

def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123@",  # Enter your MySQL password here if you have one
        database="foodbridge"
    )

def execute_query(query, values=None):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(query, values or ())
    conn.commit()

    result = cursor.lastrowid

    cursor.close()
    conn.close()

    return result


def fetch_all(query, values=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(query, values or ())
    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return result


def fetch_one(query, values=None):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(query, values or ())
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return result