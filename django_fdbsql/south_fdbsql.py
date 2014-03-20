# FoundationDB SQL Layer Adapter for Django
# Copyright (c) 2013-2014FoundationDB, LLC

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

from __future__ import print_function

import uuid
from django.db.backends.util import truncate_name
from south.db import generic


class DatabaseOperations(generic.DatabaseOperations):
    """
    FoundationDB SQL Layer implementation of database operations.
    """

    backend_name = "django_fdbsql"
    allows_combined_alters  = False
    supports_foreign_keys   = False
    has_check_constraints   = False
    has_booleans            = True

    alter_string_set_type  = 'ALTER COLUMN %(column)s SET DATA TYPE %(type)s'
    alter_string_set_null  = 'ALTER COLUMN %(column)s NULL'
    alter_string_drop_null = 'ALTER COLUMN %(column)s NOT NULL'


    @generic.copy_column_constraints
    @generic.delete_column_constraints
    def rename_column(self, table_name, old, new):
        if old == new:
            return []
        self.execute('ALTER TABLE %s RENAME COLUMN %s TO %s;' % (
            self.quote_name(table_name),
            self.quote_name(old),
            self.quote_name(new),
        ))


    def _fill_constraint_cache(self, db_name, table_name):
        schema = self._get_schema_name()
        ifsc_tables = ["key_column_usage"]

        self._constraint_cache.setdefault(db_name, {})
        self._constraint_cache[db_name][table_name] = {}

        for ifsc_table in ifsc_tables:
            rows = self.execute("""
                SELECT kc.constraint_name, kc.column_name, c.constraint_type
                FROM information_schema.%s AS kc
                JOIN information_schema.table_constraints AS c ON
                    kc.schema_name = c.schema_name AND
                    kc.table_name = c.table_name AND
                    kc.constraint_name = c.constraint_name
                WHERE
                    kc.schema_name = %%s AND
                    kc.table_name = %%s
            """ % ifsc_table, [schema, table_name])
            for constraint, column, kind in rows:
                self._constraint_cache[db_name][table_name].setdefault(column, set())
                self._constraint_cache[db_name][table_name][column].add((kind, constraint))
        return


    # TODO: Overrides needed?
    #def _default_value_workaround(self, value):
    #    "Support for UUIDs on psql"
    #    if isinstance(value, uuid.UUID):
    #        return str(value)
    #    else:
    #        return super(DatabaseOperations, self)._default_value_workaround(value)

