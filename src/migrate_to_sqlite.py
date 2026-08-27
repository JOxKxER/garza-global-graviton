import sqlite3

def execute_query(database, query, params):
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()