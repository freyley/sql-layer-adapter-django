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

import binascii
import datetime
import sys
import warnings

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.db import utils
from django.db.backends import BaseDatabaseFeatures, BaseDatabaseWrapper, BaseDatabaseValidation
from django.utils.safestring import SafeUnicode, SafeString

from operations import DatabaseOperations
from client import DatabaseClient
from creation import DatabaseCreation
from introspection import DatabaseIntrospection

from helpers import (
    DJANGO_GTEQ_1_4, DJANGO_GTEQ_1_5, DJANGO_GTEQ_1_6, DJANGO_GTEQ_1_7,
    fdb_check_use_tz, fdb_force_str, fdb_reraise, timezone
)

MIN_LAYER_VERSION = [1,9,3]

if not DJANGO_GTEQ_1_6:
    from django.db.backends.signals import connection_created

if DJANGO_GTEQ_1_7:
    from schema import DatabaseSchemaEditor

try:
    import psycopg2 as DBAPI
    import psycopg2.extensions as DBAPI_EXT
except ImportError, e:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured("Error loading psycopg2 module: %s" % e)

try:
    import pytz
except ImportError:
    pytz = None

class FDBBinary(object):
    def __init__(self, value):
        self.value = value

def create_binary(value):
    return FDBBinary(value)

def adapt_buffer(b):
    hex_str = binascii.hexlify(b)
    return DBAPI_EXT.AsIs("x'%s'" % hex_str)

def adapt_binary(b):
    if b.value is None:
        return DBAPI_EXT.AsIs('NULL')
    return adapt_buffer(b.value)

def adapt_date(value):
    return DBAPI_EXT.AsIs("'%s'" % value.isoformat())

def adapt_time(value):
    return DBAPI_EXT.AsIs("'%s'" % value.strftime("%H:%M:%S"))

def adapt_datetime(value):
    if fdb_check_use_tz(settings):
        if timezone.is_naive(value):
            warnings.warn("FDBSQL received a naive datetime (%s)" % value, RuntimeWarning)
            value = timezone.make_aware(value, timezone.get_default_timezone())
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return DBAPI_EXT.AsIs("'%s'" % value.isoformat())

orig_DATETIME_TYPE = DBAPI_EXT.string_types[1114]
def wrapped_datetime_cast(value, cursor):
    dt = orig_DATETIME_TYPE(value, cursor)
    # Confirm that dt is naive before overwriting its tzinfo.
    if dt is not None and fdb_check_use_tz(settings) and timezone.is_naive(dt):
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

DBAPI_EXT.register_type(DBAPI_EXT.new_type(orig_DATETIME_TYPE.values,
                                           orig_DATETIME_TYPE.name,
                                           wrapped_datetime_cast))

DBAPI_EXT.register_type(DBAPI_EXT.UNICODE)
DBAPI_EXT.register_adapter(SafeString, DBAPI_EXT.QuotedString)
DBAPI_EXT.register_adapter(SafeUnicode, DBAPI_EXT.QuotedString)

# Override stock adapters to prevent :: quoting
DBAPI_EXT.register_adapter(FDBBinary, adapt_binary)
DBAPI_EXT.register_adapter(buffer, adapt_buffer)
DBAPI_EXT.register_adapter(bytearray, adapt_buffer)
DBAPI_EXT.register_adapter(memoryview, adapt_buffer)
DBAPI_EXT.register_adapter(datetime.date, adapt_date)
DBAPI_EXT.register_adapter(datetime.time, adapt_time)
DBAPI_EXT.register_adapter(datetime.datetime, adapt_datetime)

DBAPI.BINARY = FDBBinary
DBAPI.Binary = DBAPI_EXT.Binary = create_binary

DatabaseError = DBAPI.DatabaseError
IntegrityError = DBAPI.IntegrityError


class DatabaseFeatures(BaseDatabaseFeatures):
    # Although we do support it, Django unconditionally uses NULL for the value,
    # instead of DEFAULT, which we don't.
    #can_combine_inserts_with_and_without_auto_increment_pk = True
    can_defer_constraint_checks = True
    can_introspect_ip_address_field = False
    can_introspect_small_integer_field = True
    can_return_id_from_insert = True
    can_rollback_ddl = False
    if DJANGO_GTEQ_1_7:
        closed_cursor_error_class = utils.InterfaceError
    has_bulk_insert = True
    has_case_insensitive_like = False
    has_real_datatype = True
    has_select_for_update = False
    has_select_for_update_nowait = False
    # If symbolic timezone names can be used, both in the backend and queries
    has_zoneinfo_database = (pytz is not None)
    max_index_name_length = 63
    needs_datetime_string_cast = False
    nulls_order_largest = False
    related_fields_match_type = True
    requires_literal_defaults = True
    requires_rollback_on_dirty_transaction = True
    requires_sqlparse_for_splitting = False
    supports_check_constraints = False
    supports_column_check_constraints = False
    supports_combined_alters = False
    supports_foreign_keys = True
    supports_forward_references = False
    supports_microsecond_precision = False
    supports_regex_backreferencing = True
    # Off by default as ALTER RESTART WITH auto-commits, breaking test assumptions.
    # __init__ below allows via configuration for manual usage.
    supports_sequence_reset = False
    # If there is a type that supports timezones for when USE_TZ=False
    supports_timezones = False
    supports_transactions = True
    supports_combined_alters = False
    uses_savepoints = False

    def __init__(self, connection):
        super(DatabaseFeatures, self).__init__(connection)
        self.supports_sequence_reset = connection.settings_dict.get('OPTIONS', {}).get('supports_sequence_reset', False)


class DatabaseWrapper(BaseDatabaseWrapper):
    Database = DBAPI
    vendor = 'fdbsql'
    operators = {
        'exact': '= %s',
        'iexact': '= UPPER(%s)',
        'contains': 'LIKE %s',
        'icontains': 'LIKE UPPER(%s)',
        'gt': '> %s',
        'gte': '>= %s',
        'lt': '< %s',
        'lte': '<= %s',
        'startswith': 'LIKE %s',
        'endswith': 'LIKE %s',
        'istartswith': 'LIKE UPPER(%s)',
        'iendswith': 'LIKE UPPER(%s)',
    }
    # Use alternative reset function (allows transactional increase)
    _use_sequence_reset_function = False

    if DJANGO_GTEQ_1_7:
        pattern_ops = {
            'startswith': "LIKE %s || '%%%%'",
            'istartswith': "LIKE UPPER(%s) || '%%%%'",
        }

    def __init__(self, *args, **kwargs):
        super(DatabaseWrapper, self).__init__(*args, **kwargs)
        self._use_sequence_reset_function = self.settings_dict.get('OPTIONS', {}).get('use_sequence_reset_function', None)
        self.features = DatabaseFeatures(self)
        self.ops = DatabaseOperations(self)
        self.client = DatabaseClient(self)
        self.creation = DatabaseCreation(self)
        self.introspection = DatabaseIntrospection(self)
        self.validation = BaseDatabaseValidation(self)

    def close(self):
        try:
            super(DatabaseWrapper, self).close()
        except DBAPI.Error:
            # Ensure connection is unset even for an error
            self.connection = None
            logger.warning('error while closing', exc_info=sys.exc_info())
            raise

    if DJANGO_GTEQ_1_6:
        def get_connection_params(self):
            return self._fdb_get_connection_params()

        def get_new_connection(self, conn_params):
            return self._fdb_get_new_connection(conn_params)

        def init_connection_state(self):
            return self._fdb_init_connection_state()

        def create_cursor(self):
            return self._fdb_create_cursor()

        def check_constraints(self, table_names=None):
            # Not implemented as there is no way to COMMIT with a broken reference
            pass

        def is_usable(self):
            try:
                self.connection.cursor().execute("SELECT 1")
            except (DBAPI.DatabaseError, DBAPI.InterfaceError):
                return False
            else:
                return True

        def _set_autocommit(self, autocommit):
            # Assumes psycopg2 >= 2.4.2
            self.connection.autocommit = autocommit
    else:
        def _cursor(self):
            if self.connection is None:
                params = self._fdb_get_connection_params()
                self.connection = self._fdb_get_new_connection(params)
                self._fdb_init_connection_state()
                connection_created.send(sender=self.__class__, connection=self)
            return self._fdb_create_cursor()

        def _commit(self):
            try:
                super(DatabaseWrapper, self)._commit()
            except IntegrityError, e:
                fdb_reraise(utils.IntegrityError, utils.IntegrityError(*tuple(e.args)), sys.exc_info()[2])
            except DatabaseError, e:
                fdb_reraise(utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2])

    if DJANGO_GTEQ_1_7:
        def schema_editor(self, *args, **kwargs):
            return DatabaseSchemaEditor(self, *args, **kwargs)

    #
    # Internal Methods
    #

    def _fdb_get_connection_params(self):
        settings_dict = self.settings_dict
        if not settings_dict['NAME']:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "settings.DATABASES is improperly configured. "
                "Please supply the NAME value."
            )
        conn_params = {
            'database': settings_dict['NAME'],
        }
        conn_params.update(settings_dict['OPTIONS'])
        # Adapter options that don't apply to the connection
        conn_params.pop('autocommit', False)
        conn_params.pop('supports_sequence_reset', False)
        conn_params.pop('use_sequence_reset_function', False)
        user = settings_dict.get('USER', '')
        password = fdb_force_str(settings_dict.get('PASSWORD', ''))
        host = settings_dict.get('HOST', '')
        port = settings_dict.get('PORT', '')
        conn_params['user'] = user if len(user) > 0 else 'django'
        conn_params['password'] = password
        conn_params['host'] = host if len(host) > 0 else 'localhost'
        conn_params['port'] = port if len(port) > 0 else '15432'
        return conn_params

    def _fdb_get_new_connection(self, conn_params):
        conn = DBAPI.connect(**conn_params)
        self._fdb_check_layer_version(conn)
        return conn

    def _fdb_init_connection_state(self):
        self.connection.set_client_encoding('UTF8')

    def _fdb_create_cursor(self):
        cursor = self.connection.cursor()
        return self._fdb_wrap_cursor(cursor)

    def _fdb_wrap_cursor(self, cursor):
        if DJANGO_GTEQ_1_6:
            return cursor
        return CursorWrapper(cursor)

    def _fdb_check_layer_version(self, conn):
        ver = conn.get_parameter_status('foundationdb_server')
        if ver:
            ver = [int(x) for x in ver.split('.')]
        if ver < MIN_LAYER_VERSION:
            raise ImproperlyConfigured("SQL Layer >= %s required but connected to version: %s" % (MIN_LAYER_VERSION, ver))

    def _fdb_create_sequence_reset_function(self, cursor, quoted_schema_name):
        if self.features.supports_sequence_reset and self._use_sequence_reset_function:
           import sequence_reset_function
           sequence_reset_function.create_or_replace(cursor, quoted_schema_name)

if not DJANGO_GTEQ_1_6:
    class CursorWrapper(object):
        def __init__(self, cursor):
            self.cursor = cursor

        def execute(self, query, args=None):
            try:
                return self.cursor.execute(query, args)
            except IntegrityError, e:
                fdb_reraise(utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2])
            except DatabaseError, e:
                fdb_reraise(utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2])

        def executemany(self, query, args):
            try:
                return self.cursor.executemany(query, args)
            except IntegrityError, e:
                fdb_reraise(utils.IntegrityError, utils.IntegrityError(*tuple(e)), sys.exc_info()[2])
            except DatabaseError, e:
                fdb_reraise(utils.DatabaseError, utils.DatabaseError(*tuple(e)), sys.exc_info()[2])

        def __getattr__(self, attr):
            if attr in self.__dict__:
                return self.__dict__[attr]
            else:
                return getattr(self.cursor, attr)

        def __iter__(self):
            return iter(self.cursor)

