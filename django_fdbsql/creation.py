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

import time

from django.db.backends.creation import BaseDatabaseCreation
from django.db.backends.util import truncate_name

from helpers import fdb_get_input, fdb_test_setting

class DatabaseCreation(BaseDatabaseCreation):
    data_types = {
        'AutoField':                    'serial',
        'BigIntegerField':              'bigint',
        'BinaryField':                  'blob',
        'BooleanField':                 'boolean',
        'CharField':                    'varchar(%(max_length)s)',
        'CommaSeparatedIntegerField':   'varchar(%(max_length)s)',
        'DateField':                    'date',
        'DateTimeField':                'datetime',
        'DecimalField':                 'decimal(%(max_digits)s, %(decimal_places)s)',
        'FileField':                    'varchar(%(max_length)s)',
        'FilePathField':                'varchar(%(max_length)s)',
        'FloatField':                   'double',
        'GenericIPAddressField':        'char(39)',
        'IPAddressField':               'char(15)',
        'IntegerField':                 'integer',
        'NullBooleanField':             'boolean',
        'OneToOneField':                'integer',
        # Currently no way (e.g. CHECK) to enforce unsigned
        'PositiveIntegerField':         'integer',
        'PositiveSmallIntegerField':    'smallint',
        'SlugField':                    'varchar(%(max_length)s)',
        'SmallIntegerField':            'smallint',
        'TextField':                    'clob',
        'TimeField':                    'time',
    }

    def sql_table_creation_suffix(self):
        suffix = []
        charset = fdb_test_setting(self.connection.settings_dict, 'CHARSET')
        if charset:
            suffix.append('CHARACTER SET %s' % charset)
        collation = fdb_test_setting(self.connection.settings_dict, 'COLLATION')
        if collation:
            suffix.append('COLLATE %s' % collation)
        return ' '.join(suffix)

    def _create_test_db(self, verbosity, autoclobber):
        """
        Internal implementation - creates the test db tables.
        """
        suffix = self.sql_table_creation_suffix()
        test_database_name = self._get_test_db_name()
        qn = self.connection.ops.quote_name
        # Create the test database and connect to it.
        cursor = self.connection.cursor()
        try:
            cursor.execute("CREATE SCHEMA %s %s" % (qn(test_database_name), suffix))
        except Exception, e:
            import sys
            sys.stderr.write("Got an error creating the test database: %s\n" % e)
            if not autoclobber:
                confirm = fdb_get_input("Type 'yes' if you would like to try deleting the test database '%s', or 'no' to cancel: " % test_database_name)
            if autoclobber or confirm == 'yes':
                try:
                    if verbosity >= 1:
                        print("Destroying old test database '%s'..." % self.connection.alias)
                    cursor.execute("DROP SCHEMA %s CASCADE" % qn(test_database_name))
                    cursor.execute("CREATE SCHEMA %s %s" % (qn(test_database_name), suffix))
                except Exception, e:
                    sys.stderr.write("Got an error recreating the test database: %s\n" % e)
                    sys.exit(2)
            else:
                print("Tests cancelled.")
                sys.exit(1)
        self.connection._fdb_create_sequence_reset_function(cursor, qn(test_database_name))
        cursor.close()
        return test_database_name

    def _destroy_test_db(self, test_database_name, verbosity):
        """
        Internal implementation - remove the test db tables.
        """
        # Remove the test database to clean up after
        # ourselves. Connect to the previous database (not the test database)
        # to do so, because it's not allowed to delete a database while being
        # connected to it.
        cursor = self.connection.cursor()
        # Wait to avoid "database is being accessed by other users" errors.
        time.sleep(1)
        cursor.execute("DROP SCHEMA %s CASCADE" % self.connection.ops.quote_name(test_database_name))
        self.connection.close()

