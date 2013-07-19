"""
Akiban database backend for Django.

Requires psycopg 2: http://initd.org/projects/psycopg2
"""

import sys

from django.db import utils
from django.db.backends import *
from django.db.backends.signals import connection_created
from django.db.backends.akiban.operations import DatabaseOperations as PostgresqlDatabaseOperations
from django.db.backends.akiban.client import DatabaseClient
from django.db.backends.akiban.creation import DatabaseCreation
from django.db.backends.akiban.introspection import DatabaseIntrospection
from django.utils.safestring import SafeUnicode, SafeString

try:
    import psycopg2 as Database
    import psycopg2.extensions
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading psycopg2 module: %s" % e)

DatabaseError = Database.DatabaseError
IntegrityError = Database.IntegrityError

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_adapter(SafeString, psycopg2.extensions.QuotedString)
psycopg2.extensions.register_adapter(SafeUnicode, psycopg2.extensions.QuotedString)

class CursorWrapper(object):
    """
    A thin wrapper around psycopg2's normal cursor class so that we can catch
    particular exception instances and reraise them with the right types.
    """

    def __init__(self, cursor):
        self.cursor = cursor

    def execute(self, query, args=None):
        try:
            return self.cursor.execute(query, args)
        except Database.IntegrityError, e:
            raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
        except Database.DatabaseError, e:
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]

    def executemany(self, query, args):
        try:
            return self.cursor.executemany(query, args)
        except Database.IntegrityError, e:
            raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
        except Database.DatabaseError, e:
            raise utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2]

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

    def __iter__(self):
        return iter(self.cursor)

class DatabaseFeatures(BaseDatabaseFeatures):
    needs_datetime_string_cast = False
    can_return_id_from_insert = True
    has_bulk_insert = True
    requires_rollback_on_dirty_transaction = True
    has_real_datatype = True
    supports_transactions = True
    supports_microsecond_precision = False
    supports_regex_backreferencing = False
    supports_timezones = False
    supports_sequence_reset = False
    uses_autocommit = True
    supports_forward_references = False

class DatabaseOperations(PostgresqlDatabaseOperations):
    def last_executed_query(self, cursor, sql, params):
        # With psycopg2, cursor objects have a "query" attribute that is the
        # exact query sent to the database. See docs here:
        # http://www.initd.org/tracker/psycopg/wiki/psycopg2_documentation#postgresql-status-message-and-executed-query
        return cursor.query

    def return_insert_id(self):
        return "RETURNING %s", ()

class DatabaseWrapper(BaseDatabaseWrapper):
    vendor = 'akiban'
    operators = {
        'exact': '= %s',
        'iexact': '= UPPER(%s)',
        'contains': 'LIKE %s',
        'icontains': 'ILIKE %s',
        'regex': '~ %s',        # TODO Reject?
        'iregex': '~* %s',      # TODO Reject?
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE %s',
        'endswith': 'LIKE %s',
        'istartswith': 'ILIKE %s',
        'iendswith': 'ILIKE %s',
    }

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)

        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def _cursor(self):
        new_connection = False
        settings_dict = self.settings_dict
        if self.connection is None:
            new_connection = True
            if settings_dict['NAME'] == '':
                from django.core.exceptions import ImproperlyConfigured
                raise ImproperlyConfigured("You need to specify NAME in your Django settings file.")
            conn_params = {
                'database': settings_dict['NAME'],
            }
            conn_params.update(settings_dict['OPTIONS'])
            if 'autocommit' in conn_params:
                del conn_params['autocommit']
            if settings_dict['USER']:
                conn_params['user'] = settings_dict['USER']
            if settings_dict['PASSWORD']:
                conn_params['password'] = settings_dict['PASSWORD']
            if settings_dict['HOST']:
                conn_params['host'] = settings_dict['HOST']
            if settings_dict['PORT']:
                conn_params['port'] = settings_dict['PORT']
            self.connection = Database.connect(**conn_params)
            self.connection.set_client_encoding('UTF8')
            self.connection.autocommit = True
            connection_created.send(sender=self.__class__, connection=self)
        cursor = self.connection.cursor()
        cursor.tzinfo_factory = None
        return CursorWrapper(cursor)

    def _commit(self):
        if self.connection is not None:
            try:
                return self.connection.commit()
            except Database.IntegrityError, e:
                raise utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2]
