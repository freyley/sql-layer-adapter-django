# FoundationDB SQL Layer Adapter for Django South
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

from south.db import generic

orig_constraints_affecting_columns = generic.DatabaseOperations._constraints_affecting_columns

class DatabaseOperations(generic.DatabaseOperations):
    """
    FoundationDB SQL Layer implementation of database operations.
    """

    alter_string_set_type  = 'ALTER COLUMN %(column)s SET DATA TYPE %(type)s'
    alter_string_set_null  = 'ALTER COLUMN %(column)s NULL'
    alter_string_drop_null = 'ALTER COLUMN %(column)s NOT NULL'
    drop_index_string = 'DROP INDEX %(table_name)s.%(index_name)s'
    elete_primary_key_sql = "ALTER TABLE %(table)s DROP PRIMARY KEY"

    backend_name = "fdbsql"

    allows_combined_alters  = False
    supports_foreign_keys   = True
    has_check_constraints   = False
    has_booleans            = True
    raises_default_errors   = True


    @generic.copy_column_constraints
    @generic.delete_column_constraints
    def rename_column(self, table_name, old, new):
        """
        Renames the column 'old' from the table 'table_name' to 'new'.
        """
        if old == new:
            return []
        self.execute('ALTER TABLE %s RENAME COLUMN %s TO %s;' % (
            self.quote_name(table_name),
            self.quote_name(old),
            self.quote_name(new),
        ))

    def _fill_constraint_cache(self, db_name, table_name):
        self._constraint_cache.setdefault(db_name, {})
        self._constraint_cache[db_name][table_name] = {}
        rows = self.execute(
            """
            SELECT kc.constraint_name, kc.column_name, c.constraint_type
            FROM information_schema.key_column_usage AS kc
            JOIN information_schema.table_constraints AS c ON
                kc.table_schema = c.table_schema AND
                kc.table_name = c.table_name AND
                kc.constraint_name = c.constraint_name
            WHERE
                kc.table_schema = %s AND
                kc.table_name = %s
            """,
            (db_name, table_name)
        )
        for constraint, column, kind in rows:
            # Note: Remove prefixed table_name from constraint name (prepended as As of SQL Layer 1.9.3) 
            if constraint.startswith(table_name + '.'):
                constraint = constraint[len(table_name)+1:]
            self._constraint_cache[db_name][table_name].setdefault(column, set())
            self._constraint_cache[db_name][table_name][column].add((kind, constraint))

    def _constraints_affecting_columns(self, table_name, columns, type="UNIQUE"):
        """
        Gets the names of the constraints affecting the given columns.
        If columns is None, returns all constraints of the type on the table.
        """
        if type == "PRIMARY KEY":
            type = "PRIMARY"
        return orig_constraints_affecting_columns(self, table_name, columns, type)

