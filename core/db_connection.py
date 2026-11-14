import os
import psycopg2
from psycopg2.extras import RealDictCursor

from core.app_functions import clean_errors


class MESRawDB:
    """MES DB \n
    DB Connection to MES, Running Raw Query \n
    Usage:
    1. For TATA/BLDR data sync
    2. Use only once: reset DB index
    3.
    """

    def __str__(self):
        return f"MS SQL Server DB:{self.host}"

    def __init__(self, as_dict=False, *, db_name="", read_only=True):
        try:
            if not db_name:
                mydb_dict = {
                    "host": os.environ.get("POSTGRES_HOST", "127.0.0.1"),
                    "user": os.environ.get("POSTGRES_USER", "postgres"),
                    "password": os.environ.get("POSTGRES_PASSWORD", ""),
                    "database": os.environ.get("POSTGRES_DB", "pi_platform"),
                    "port": os.environ.get("POSTGRES_PORT", "5432"),
                }
            else:
                raise ValueError(f"{db_name} is not defined. ")

            self.host = mydb_dict.get("host", "")
            self.mydb = psycopg2.connect(**mydb_dict)
            self.mydb.set_session(readonly=read_only)
        except Exception as e:
            print(e)
            raise ValueError(f"DB Connection Error. {self.host}")

        try:
            if as_dict:
                self.cursor = self.mydb.cursor(cursor_factory=RealDictCursor)
            else:
                self.cursor = self.mydb.cursor()
        except Exception as e:
            self.mydb.close()
            print(e)
            raise ValueError("DB Cursor Error. ")

    def test_connection(self):
        # self.cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES")
        self.cursor.execute("SELECT name FROM master.sys.databases")
        result = self.cursor.fetchall()
        self.close()
        return result

    def execute(self, query, test=True):
        """execute and close

        Args:
            query (str): the query that need to be executed

        Returns:
            out ( status (str), result (list or str) ):
            status: "success" or "failure" \n
            result (list or str): query result or error message
        """
        try:
            self.cursor.execute(query)
            result = ""
            if query.lower().startswith("select"):
                result = self.cursor.fetchall()
            status = "success"
            self.mydb.commit()
        except Exception as e:
            print(e)
            status = "error"
            result = f"Error when execute query, contact MES group. {clean_errors(e)}"

        finally:
            self.close()

        return status, result

    def reset_index(self, seq_list):
        self.mydb.set_session(readonly=False)
        # execute raw query
        # Resetting Sequence to 1
        for seq in seq_list:
            try:
                self.cursor.execute(f"ALTER SEQUENCE public.{seq} RESTART 1;")
                self.mydb.commit()
            except Exception as e:
                self.mydb.rollback()
                continue

        self.close()

    def close(self):
        self.cursor.close()
        self.mydb.close()
