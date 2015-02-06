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

from django.conf import settings
from django.db.backends import BaseDatabaseOperations

from helpers import (
    DJANGO_GTEQ_1_4, DJANGO_GTEQ_1_5, DJANGO_GTEQ_1_6,
    fdb_check_use_tz, fdb_text_type, fdb_tz_is_aware, timezone
)

class DatabaseOperations(BaseDatabaseOperations):
    def __init__(self, connection):
        if DJANGO_GTEQ_1_4:
            super(DatabaseOperations, self).__init__(connection)
        else:
            super(DatabaseOperations, self).__init__()
            self.connection = connection

    def date_extract_sql(self, lookup_type, field_name):
        """
        Given a lookup_type of 'year', 'month', 'day' or 'weekday', returns
        the SQL that extracts a value from the given date field field_name.
        """
        if lookup_type == 'week_day':
            lookup_type = 'dayofweek'
        return '%s(%s)' % (lookup_type, field_name)

    def date_interval_sql(self, sql, connector, timedelta):
        """
        Implements the interval functionality for expressions
        """
        mods = []
        if timedelta.days:
            mods.append('%s day' % timedelta.days)
        if timedelta.seconds:
            mods.append('%s second' % timedelta.seconds)
        if timedelta.microseconds:
            mods.append('%s microsecond' % timedelta.microseconds)
        conn_sql = ' %s interval ' % connector
        if len(mods) > 0:
            sql = '%s%s' % (sql, conn_sql)
        return '(%s%s)' % (sql, conn_sql.join(mods))

    def date_trunc_sql(self, lookup_type, field_name):
        """
        Given a lookup_type of 'year', 'month' or 'day', returns the SQL that
        truncates the given date field field_name to a date object with only
        the given specificity.
        """
        formats = {
            'year':  '%%Y-01-01',
            'month': '%%Y-%%m-01',
            'day':   '%%Y-%%m-%%d',
        }
        fmt_str = formats[lookup_type]
        cast_to = DJANGO_GTEQ_1_6 and 'DATE' or 'DATETIME'
        return "CAST(DATE_FORMAT(%s, '%s') AS %s)" % (field_name, fmt_str, cast_to)

    if DJANGO_GTEQ_1_6:
        def datetime_extract_sql(self, lookup_type, field_name, tzname):
            """
            Given a lookup_type of 'year', 'month', 'day', 'week_day', 'hour',
            'minute' or 'second', returns the SQL that extracts a value from
            the given datetime field field_name, and a tuple of parameters.
            """
            if settings.USE_TZ:
                field_name = "CONVERT_TZ(%s, 'UTC', %%s)" % field_name
                params = [tzname]
            else:
                params = []
            # Django assumes Sunday=1, Saturday=7, which our DAYOFWEEK does
            if lookup_type == 'week_day':
                lookup_type = 'dayofweek'
            return '%s(%s)' % (lookup_type.upper(), field_name), params

        def datetime_trunc_sql(self, lookup_type, field_name, tzname):
            """
            Given a lookup_type of 'year', 'month', 'day', 'hour', 'minute' or
            'second', returns the SQL that truncates the given datetime field
            field_name to a datetime object with only the given specificity, and
            a tuple of parameters.
            """
            if settings.USE_TZ:
                field_name = "CONVERT_TZ(%s, 'UTC', %%s)" % field_name
                params = [tzname]
            else:
                params = []
            formats = {
                'year':   '%%Y-01-01 00:00:00',
                'month':  '%%Y-%%m-01 00:00:00',
                'day':    '%%Y-%%m-%%d 00:00:00',
                'hour':   '%%Y-%%m-%%d %%H:00:00',
                'minute': '%%Y-%%m-%%d %%H:%%i:00',
                'second': '%%Y-%%m-%%d %%H:%%i:%%S',
            }
            fmt_str = formats[lookup_type]
            return "CAST(DATE_FORMAT(%s, '%s') AS DATETIME)" % (field_name, fmt_str), params

    def deferrable_sql(self):
        """
        Returns the SQL necessary to make a constraint "initially deferred"
        during a CREATE TABLE statement.
        """
        return ' DEFERRABLE INITIALLY DEFERRED'

    def drop_foreignkey_sql(self):
        """
        Returns the SQL command that drops a foreign key.
        """
        # Note: Appended to an ALTER statement
        return 'DROP FOREIGN KEY'

    def fetch_returned_insert_id(self, cursor):
        """
        Given a cursor object that has just performed an INSERT...RETURNING
        statement into a table that has an auto-incrementing ID, returns the
        newly created ID.
        """
        # Note: Goes with features.can_return_id_from_insert and ops.return_insert_id()
        return cursor.fetchone()[0]

    if DJANGO_GTEQ_1_4:
        def for_update_sql(self, nowait=False):
            """
            Returns the FOR UPDATE SQL clause to lock rows for an update operation.
            """
            return ''

    def last_insert_id(self, cursor, table_name, pk_name):
        """
        Given a cursor object that has just performed an INSERT statement into
        a table that has an auto-incrementing ID, returns the newly created ID.

        This method also receives the table name and the name of the primary-key
        column.
        """
        raise NotImplementedError("expected RETURNING/fetch_returned_insert_id")
    
    def lookup_cast(self, lookup_type):
        """
        Returns the string to use in a query when performing lookups
        ("contains", "like", etc). The resulting string should contain a '%s'
        placeholder for the column being searched against.
        """
        # Note: Corresponds to base.operators
        if lookup_type in ('iexact', 'icontains', 'istartswith', 'iendswith'):
            return 'UPPER(%s)'
        return '%s'

    def max_name_length(self):
        """
        Returns the maximum length of table and column names, or None if there
        is no limit.
        """
    	return 128

    def no_limit_value(self):
        """
        Returns the value to use for the LIMIT when we are wanting "LIMIT
        infinity". Returns None if the limit clause can be omitted in this case.
        """
        return None
    
    def return_insert_id(self):
        """
        Returns the SQL and params to append to the INSERT query. The returned
        fragment should contain a format string to hold the appropriate column.
        """
        return "RETURNING %s", ()

    def quote_name(self, name):
        """
        Returns a quoted version of the given table, index or column name. Does
        not quote the given name if it's already been quoted.
        """
        if name.startswith('"') and name.endswith('"'):
            return
        # No other backends worry about escaping
        return '"%s"' % name

    def regex_lookup(self, lookup_type):
        """
        Returns the string to use in a query when performing regular expression
        lookups (using "regex" or "iregex"). The resulting string should
        contain a '%s' placeholders for the column and pattern.
        """
        return "%s(%%s, %%s)" % lookup_type.upper()

    def savepoint_create_sql(self, sid):
        """
        Returns the SQL for starting a new savepoint. Only required if the
        "uses_savepoints" feature is True. The "sid" parameter is a string
        for the savepoint id.
        """
        raise NotImplementedError()

    def savepoint_commit_sql(self, sid):
        """
        Returns the SQL for committing the given savepoint.
        """
        raise NotImplementedError()

    def savepoint_rollback_sql(self, sid):
        """
        Returns the SQL for rolling back the given savepoint.
        """
        raise NotImplementedError()

    # Note: allow_cascade added in 1.6
    def sql_flush(self, style, tables, sequences, allow_cascade=False):
        """
        Returns a list of SQL statements required to remove all data from
        the given database tables (without actually removing the tables
        themselves).

        The returned value also includes SQL statements required to reset DB
        sequences passed in :param sequences:.

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.

        The `allow_cascade` argument determines whether truncation may cascade
        to tables with foreign keys pointing the tables being truncated.
        """
        sql = []
        if tables:
            for t in tables:
                sql.append('%s %s;' % (
                    style.SQL_KEYWORD('DELETE FROM'),
                    style.SQL_FIELD(self.quote_name(t)),
                ))
        sql.extend(self._fdb_sequence_reset_by_name_sql(style, sequences))
        return sql

    if DJANGO_GTEQ_1_5:
        def sequence_reset_by_name_sql(self, style, sequences):
            return self._fdb_sequence_reset_by_name_sql(style, sequences)

    def sequence_reset_sql(self, style, model_list):
        """
        Returns a list of the SQL statements required to reset sequences to
        a value appropriate for the next insert for the given models.

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.
        """
        from django.db import models
        sql = []
        cursor = self.connection.cursor()
        try:
            for m in model_list:
                for f in m._meta.local_fields:
                    if isinstance(f, models.AutoField):
                        sql.extend(self._fdb_reset_sequence_sql(cursor, style, m._meta.db_table, f.column, False))
                        # One AutoField per model
                        break
                for f in m._meta.many_to_many:
                    if not f.rel.through:
                        sql.extend(self._fdb_reset_sequence_sql(cursor, style, f.m2m_db_table(), 'id', False))
        finally:
            cursor.close()
        return sql

    def prep_for_iexact_query(self, x):
        """
        Prepares a value for use in an iexact query.
        """
        return x

    def value_to_db_date(self, value):
        """
        Transform a date value to an object compatible with what is expected
        by the backend driver for date columns.
        """
        if value is None:
            return None
        return fdb_text_type(value)

    def value_to_db_datetime(self, value):
        """
        Transform a datetime value to an object compatible with what is expected
        by the backend driver for datetime columns.
        """
        if value is None:
            return None
        if fdb_tz_is_aware(value):
            if fdb_check_use_tz(settings) and timezone.utc is not None:
                value = value.astimezone(timezone.utc).replace(tzinfo=None)
            else:
                raise ValueError("FDB SQL does not support timezone-aware datetimes when USE_TZ is False.")
        return fdb_text_type(value)

    def value_to_db_time(self, value):
        if value is None:
            return None
        if fdb_tz_is_aware(value):
            raise ValueError("FDB SQL does not support timezone-aware times.")
        return fdb_text_type(value)

    def combine_expression(self, connector, sub_expressions):
        """
        Combine a list of subexpressions into a single expression, using
        the provided connecting operator.
        """
        if connector == '&':
            return 'BITAND(%s)' % ','.join(sub_expressions)
        if connector == '|':
            return 'BITOR(%s)' % ','.join(sub_expressions)
        if connector == '^':
            return 'POW(%s)' % ','.join(sub_expressions)
        conn = ' %s ' % connector
        return conn.join(sub_expressions)
    
    # Added in Django 1.4, TODO: REMOVED IN IN?
    def bulk_insert_sql(self, fields, num_values):
        items_sql = "(%s)" % ", ".join(["%s"] * len(fields))
        return "VALUES " + ", ".join([items_sql] * num_values)

    #
    # Internal Methods
    #

    def _fdb_sequence_reset_by_name_sql(self, style, sequences):
        """
        Returns a list of the SQL statements required to reset sequences
        passed in :param sequences: to their initial start value.

        The `style` argument is a Style object as returned by either
        color_style() or no_style() in django.core.management.color.
        """
        sql = []
        cursor = self.connection.cursor()
        try:
            for s in sequences:
                table_name = s['table']
                column_name = s['column']
                if not (column_name and len(column_name) > 0):
                    # This will be the case if it's an m2m using an autogenerated
                    # intermediate table (see BaseDatabaseIntrospection.sequence_list)
                    column_name = 'id'
                sql.extend(self._fdb_reset_sequence_sql(cursor, style, table_name, column_name, True))
        finally:
            cursor.close()
        return sql

    def _fdb_reset_sequence_sql(self, cursor, style, table_name, column_name, use_start_value):
        """
        Return a SQL statement that will reset the SEQUENCE associated with
        :param table_name:.:param column_name" to its initial value or next
        appropriate value, as specified by :param use_start_value:.
        """
        if not self.connection.features.supports_sequence_reset:
            return []
        if self.connection._use_sequence_reset_function:
            if use_start_value:
                return []
            else:
                return [ "%s django_fdbsql_sequence_reset(CURRENT_SCHEMA, '%s', '%s');" % (
                        style.SQL_KEYWORD('SELECT'),
                        table_name.replace("'", "''"),
                        column_name.replace("'", "''"),
                    )
                ]
        if use_start_value:
            value_str = '1'
        else:
            cursor.execute("SELECT COALESCE(MAX(%s) + 1, 1) FROM %s" % (self.quote_name(column_name), self.quote_name(table_name)))
            value_str = cursor.fetchone()[0]
        return [ "%s %s %s %s %s %s %s %s %s;" % (
                style.SQL_KEYWORD('ALTER'),
                style.SQL_KEYWORD('TABLE'),
                style.SQL_KEYWORD(self.quote_name(table_name)),
                style.SQL_KEYWORD('ALTER'),
                style.SQL_KEYWORD('COLUMN'),
                style.SQL_KEYWORD(self.quote_name(column_name)),
                style.SQL_KEYWORD('RESTART'),
                style.SQL_KEYWORD('WITH'),
                value_str,
            )
        ]

