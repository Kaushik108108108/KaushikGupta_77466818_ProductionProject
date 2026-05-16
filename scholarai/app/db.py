# This file manages everything related to our Oracle database.
import os
import oracledb
from flask import g

_pool = None

# This function starts the database connection pool so we can talk to the database efficiently.
def init_db():
    global _pool
    if _pool is not None:
        return

    # we build the connection address using the settings from our environment variables.
    dsn = f"{os.getenv('ORACLE_HOST')}:{os.getenv('ORACLE_PORT', '1521')}/{os.getenv('ORACLE_SERVICE')}"

    # We create a pool of connections so multiple users can access the database at once.
    _pool = oracledb.create_pool(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=dsn,
        min=1,
        max=5,
        increment=1
    )

# This function grabs a single connection from our pool for a specific task.
def get_conn():
    if "db_conn" not in g:
        if _pool is None:
            init_db()
        g.db_conn = _pool.acquire()
    return g.db_conn

# This function closes the database connection once a task is finished.
def close_db(error=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()

# This function is used when we only need one specific piece of information from the database.
def fetch_one(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        row = cur.fetchone()
        if row is None:
            return None
        # We transform the raw row into a clean dictionary for easier use in the code.
        columns = [col[0].lower() for col in cur.description]
        
        # We also make sure to handle large text objects correctly.
        dict_row = dict(zip(columns, row))
        for key, val in dict_row.items():
            if hasattr(val, "read"):
                dict_row[key] = val.read()
        return dict_row

# This function is used when we want to get a whole list of items from the database.
def fetch_all(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        rows = cur.fetchall()
        columns = [col[0].lower() for col in cur.description]
        
        results = []
        for row in rows:
            # Each row is turned into a dictionary so we can access data by name.
            dict_row = dict(zip(columns, row))
            for key, val in dict_row.items():
                if hasattr(val, "read"):
                    dict_row[key] = val.read()
            results.append(dict_row)
        return results

# This function is used for updating, inserting, or deleting information in the database.
def execute_dml(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
    # We commit the changes to make sure they are saved permanently.
    conn.commit()