from snowflake.sqlalchemy import URL
from snowflake.connector.pandas_tools import pd_writer
from sqlalchemy import create_engine
import sqlalchemy
import pandas as pd


class SnowflakeOperator:
    def __init__(self):
        pass

    @staticmethod
    def create_engine(account, user, password, database, schema, warehouse):
        """
        Create SQLAlchemy engine to connect to a Snowflake database
        :param account: str, the Snowflake account name
        :param user: str, the Snowflake username
        :param password: str, the Snowflake user's password
        :param database: str, the name of the Snowflake database to connect to
        :param schema: str, the name of the Snowflake schema to use
        :param warehouse: str, the name of the Snowflake warehouse to use
        :return: SQLAlchemy engine object
        """
        engine = create_engine(URL(
            account=account,
            user=user,
            password=password,
            database=database,
            schema=schema,
            warehouse=warehouse
        ))
        return engine

    @staticmethod
    def upload_dataframe_to_snowflake(df_to_upload, table_name, engine):
        """
        Create table and upload the DataFrame to Snowflakes. If the table exists, it will be overwritten!
        :param df_to_upload: DataFrame to upload
        :param table_name: str, <table_name_in_lowercase>
        :param engine: SQLAlchemy engine to connect to a Snowflake database
        """
        with engine.connect() as connection:
            try:
                df_to_upload.to_sql(name=table_name,
                                    con=engine,
                                    if_exists="replace",
                                    index=False,
                                    dtype={'PLOT_NAME': sqlalchemy.types.VARCHAR()},
                                    method=pd_writer)
            except ConnectionError as error_c:
                print("Unable to connect to database!", error_c)
            except ValueError as error_v:
                print("Error!", error_v)
            finally:
                connection.close()
                engine.dispose()
        return

    @staticmethod
    def load_dataframe_from_snowflake(engine, table_name):
        """
        Loads Snowflake table as DataFrame.
        :param engine: SQLAlchemy engine to connect to a Snowflake database
        :param table_name: str
        :return: DataFrame
        """
        with engine.connect() as connection:
            try:
                database, schema = engine.url.database.split('/')
                query = 'SELECT * FROM {}.{}.{};'.format(database, schema, table_name)
                df = pd.read_sql(query, connection)
            except ConnectionError as error_c:
                print("Unable to connect to database!", error_c)
            except ValueError as error_v:
                print("Error!", error_v)
            finally:
                connection.close()
                engine.dispose()
        return df
