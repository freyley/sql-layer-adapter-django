# FoundationDB SQL Layer Adapter for Django
# Copyright (c) 2013-2015 FoundationDB, LLC

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from django.db.backends.schema import BaseDatabaseSchemaEditor

class DatabaseSchemaEditor(BaseDatabaseSchemaEditor):
    # Override defaults
    sql_alter_column_type = "ALTER COLUMN %(column)s SET DATA TYPE %(type)s"
    sql_alter_column_null = "ALTER COLUMN %(column)s NULL"
    sql_alter_column_not_null = "ALTER COLUMN %(column)s NOT NULL"
    sql_create_inline_fk = "REFERENCES %(to_table)s (%(to_column)s)"

    sql_max_column_value = "SELECT COALESCE(MAX(%(column)s), 1) FROM %(table)s"
    sql_alter_column_generated = "ALTER COLUMN %(column)s SET GENERATED BY DEFAULT AS IDENTITY (START WITH %(start_with)d)"

    def _alter_column_type_sql(self, table, column, type):
        """
        Adds special handling for SERIAL
        """
        if type.lower() != "serial":
            return super(DatabaseSchemaEditor, self)._alter_column_type_sql(table, column, type)
        else:
            # ALTER cannot have subquery to get START WITH value so look it up first.
            # TODO: What bout when self.collect_sql is True?
            start_with = None
            with self.connection.cursor() as cursor:
                cursor.execute(self.sql_max_column_value % {
                    "table": table,
                    "column": column,
                })
                start_with = cursor.fetchone()[0]
            return (
                (
                    self.sql_alter_column_type % {
                        "column": self.quote_name(column),
                        "type": "integer",
                    },
                    [],
                ),
                [
                    (
                        self.sql_alter_column % {
                            "table": table,
                            "changes": self.sql_alter_column_generated % {
                                "column": column,
                                "start_with": start_with,
                            }
                        },
                        [],
                    ),
                ],
            )

    def prepare_default(self, value):
        return self.quote_value(value)

    def quote_value(self, value):
        # Inner import for nice failure
        import psycopg2
        return psycopg2.extensions.adapt(value)
