"""
Defines the Postgres migrator for moving data into BlazingDB from Postgres
"""

import logging

from blazingdb import sources


class PostgresSource(sources.BaseSource):
    """ Handles connecting and retrieving data from Postgres, and loading it into BlazingDB """

    def __init__(self, connection, schema, **kwargs):
        super(PostgresSource, self).__init__()
        self.logger = logging.getLogger(__name__)

        self.connection = connection
        self.schema = schema

        self.fetch_count = kwargs.get("fetch_count", 10000)

    def get_tables(self):
        """ Retrieves a list of the tables in this source """
        cursor = self.connection.cursor()
        cursor.execute(" ".join([
            str.format(
                "SELECT DISTINCT table_name FROM information_schema.tables"),
            str.format(
                "WHERE table_schema = '{0}' and table_type = 'BASE TABLE'",
                self.schema)
        ]))

        return [row[0] for row in cursor.fetchall()]

    def get_columns(self, table):
        """ Retrieves a list of columns for the given table from the source """
        cursor = self.connection.cursor()
        cursor.execute(" ".join([
            str.format("SELECT column_name, data_type, character_maximum_length"),
            str.format("FROM information_schema.columns"),
            str.format("WHERE table_schema = '{0}' AND table_name = '{1}'", self.schema, table)
        ]))

        columns = []
        for row in cursor.fetchall():
            datatype = convert_datatype(row[1], row[2])
            columns.append({"name": row[0], "type": datatype})

        return columns

    def retrieve(self, table):
        """ Retrieves data for the given table from the source """
        columns = self.get_columns(table)

        cursor = self.connection.cursor()
        cursor.execute(" ".join([
            str.format("SELECT {0}", ",".join(column.name for column in columns)),
            str.format("FROM {0}.{1}", self.schema, table)
        ]))

        while True:
            chunk = cursor.fetchmany(self.fetch_count)
            if not chunk:
                break

            for row in chunk:
                mapped_row = []
                for i, value in enumerate(row):
                    datatype = columns[i].type
                    transformed = transform_value(datatype, value)
                    mapped_row.append(transformed)

                yield mapped_row


def default_transform(value):
    """ Default transform for unknown data types """
    return value


def date_transform(value):
    """ Datatype transform for date data types """
    return value.strftime("%Y-%m-%d")


DATATYPE_MAP = {
    'bit': 'long', 'boolean': 'long', 'smallint': 'long',
    'integer': 'long', 'bigint': 'long',

    'double precision': 'double', 'money': 'double',
    'numeric': 'double', 'real': 'double',

    'character': 'string({0})',
    'character varying': 'string({0})',
    'text': 'string({0})',

    'date': 'date',
    'time with time zone': 'date',
    'time without time zone': 'date',
    'timestamp with time zone': 'date',
    'timestamp without time zone': 'date'
}
DATATYPE_TRANSFORMS = {
    'date': date_transform,
    'time with time zone': date_transform,
    'time without time zone': date_transform,
    'timestamp with time zone': date_transform,
    'timestamp without time zone': date_transform
}


def convert_datatype(datatype, size):
    """ Converts a PostgreSQL data type into a BlazingDB data type """
    return DATATYPE_MAP.get(datatype).format(size)


def transform_value(datatype, value):
    """ Transforms a value from PostgreSQL into one BlazingDB can understand """
    if value is None:
        return value

    return DATATYPE_TRANSFORMS.get(datatype, default_transform)(value)
