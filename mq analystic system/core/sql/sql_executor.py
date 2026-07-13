import sqlite3
import pandas as pd

def execute_sql(df, sql_query):
    conn = sqlite3.connect(":memory:")
    df.to_sql("data_table", conn, index=False, if_exists="replace")

    try:
        result = pd.read_sql(sql_query, conn)
    except Exception as e:
        return None, str(e)

    return result, None