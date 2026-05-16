# This module handles all interactions with the Oracle database, including connection pooling and query execution.
import os
import oracledb
from flask import g

# We use a global pool to manage multiple database connections efficiently.
_pool = None

# This function initializes the Oracle database connection pool using environment variables.
def init_db():
    global _pool
    if _pool is not None:
        return

    # Build the Data Source Name (DSN) for the Oracle connection.
    dsn = f"{os.getenv('ORACLE_HOST')}:{os.getenv('ORACLE_PORT', '1521')}/{os.getenv('ORACLE_SERVICE')}"

    # Create the pool with specified connection limits.
    _pool = oracledb.create_pool(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=dsn,
        min=1,
        max=5,
        increment=1
    )

# Retrieves a connection from the pool and stores it in the Flask 'g' object for the duration of the request.
def get_conn():
    if "db_conn" not in g:
        if _pool is None:
            init_db()
        g.db_conn = _pool.acquire()
    return g.db_conn

# Closes the database connection associated with the current request context.
def close_db(error=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()

# Executes a SQL query and returns the first row as a dictionary.
def fetch_one(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        row = cur.fetchone()
        if row is None:
            return None
        columns = [col[0].lower() for col in cur.description]
        
        # Handle LOB (Large Objects) which aren't JSON serializable by reading them into strings/bytes.
        dict_row = dict(zip(columns, row))
        for key, val in dict_row.items():
            if hasattr(val, "read"):
                dict_row[key] = val.read()
        return dict_row

# Executes a SQL query and returns all matching rows as a list of dictionaries.
def fetch_all(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        rows = cur.fetchall()
        columns = [col[0].lower() for col in cur.description]
        
        results = []
        for row in rows:
            dict_row = dict(zip(columns, row))
            # Handle LOB (Large Objects) which aren't JSON serializable.
            for key, val in dict_row.items():
                if hasattr(val, "read"):
                    dict_row[key] = val.read()
            results.append(dict_row)
        return results

# Executes a Data Manipulation Language (DML) statement like INSERT, UPDATE, or DELETE and commits the transaction.
def execute_dml(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
    conn.commit()