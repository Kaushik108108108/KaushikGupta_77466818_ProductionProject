import os
import oracledb
from flask import g

_pool = None

def init_db():
    global _pool
    if _pool is not None:
        return

    dsn = f"{os.getenv('ORACLE_HOST')}:{os.getenv('ORACLE_PORT', '1521')}/{os.getenv('ORACLE_SERVICE')}"

    _pool = oracledb.create_pool(
        user=os.getenv("ORACLE_USER"),
        password=os.getenv("ORACLE_PASSWORD"),
        dsn=dsn,
        min=1,
        max=5,
        increment=1
    )

def get_conn():
    if "db_conn" not in g:
        if _pool is None:
            init_db()
        g.db_conn = _pool.acquire()
    return g.db_conn

def close_db(error=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()

def fetch_one(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        row = cur.fetchone()
        if row is None:
            return None
        columns = [col[0].lower() for col in cur.description]
        
        # Handle LOB (Large Objects) which aren't JSON serializable
        dict_row = dict(zip(columns, row))
        for key, val in dict_row.items():
            if hasattr(val, "read"):
                dict_row[key] = val.read()
        return dict_row

def fetch_all(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
        rows = cur.fetchall()
        columns = [col[0].lower() for col in cur.description]
        
        results = []
        for row in rows:
            dict_row = dict(zip(columns, row))
            # Handle LOB (Large Objects) which aren't JSON serializable
            for key, val in dict_row.items():
                if hasattr(val, "read"):
                    dict_row[key] = val.read()
            results.append(dict_row)
        return results

def execute_dml(sql, params=None):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(sql, params or {})
    conn.commit()