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

from django.db.backends import BaseDatabaseIntrospection

from helpers import DJANGO_GTEQ_1_4, DJANGO_GTEQ_1_7, fdb_field_info, fdb_force_text

class DatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = {
        16:     'BooleanField',
        17:     'BinaryField',
        20:     'BigIntegerField',
        21:     'SmallIntegerField',
        23:     'IntegerField',
        25:     'TextField',
        700:    'FloatField',
        701:    'FloatField',
        1043:   'CharField',
        1082:   'DateField',
        1083:   'TimeField',
        1114:   'DateTimeField',
        1700:   'DecimalField',
    }
        
    def get_table_list(self, cursor):
        "Returns a list of table names in the current schema."
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = CURRENT_SCHEMA
            ORDER BY table_name
            """
        )
        return [row[0] for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        "Returns a description of the table, with the DB-API cursor.description interface."
        # Columns: name, type_code, display_size, internal_size, precision, scale, null_ok
        cursor.execute(
            """
            SELECT c.column_name,
                   t.postgres_oid,
                   NULL,
                   IF(t.postgres_oid = 1043, c.character_maximum_length, NULL),
                   CAST(c.numeric_precision AS INT),
                   CAST(c.numeric_scale AS INT),
                   c.is_nullable='YES'
            FROM information_schema.columns c
            INNER JOIN information_schema.types t
              ON c.data_type = t.type_name
            WHERE table_schema = CURRENT_SCHEMA
              AND table_name = %s
            ORDER BY c.ordinal_position
            """,
            [table_name]
        )
        return [fdb_field_info( ((fdb_force_text(row[0]),) + row[1:]) ) for row in cursor.fetchall()]

    def get_relations(self, cursor, table_name):
        """
        Returns a dictionary of {field_index: (field_index_other_table, other_table)}
        representing all relationships to the given table. Indexes are 0-based.
        """
        name_to_pos = self._fdb_col_positions(cursor, table_name)
        key_columns = self._fdb_get_key_columns(cursor, table_name)
        relations = {}
        for col, o_table, o_col in key_columns:
            col_pos = name_to_pos[col]
            o_col_pos = self._fdb_col_positions(cursor, o_table)[o_col]
            relations[col_pos] = (o_col_pos, o_table)
        return relations

    if DJANGO_GTEQ_1_4:
        def get_key_columns(self, cursor, table_name):
            return self._fdb_get_key_columns(cursor, table_name)

    def get_indexes(self, cursor, table_name):
        """
        Returns a dictionary of indexed { column_name -> info } for the given
        table where each info is a dict in the format:
            {'primary_key': True|False, 'unique': True|False}
        Only single-column indexes are introspected.
        """
        PK = 'primary_key'
        UK = 'unique'
        cursor.execute(
            """
            SELECT i.index_name,
                   ic.column_name,
                   i.index_type = 'PRIMARY',
                   i.is_unique = 'YES'
            FROM information_schema.indexes i
            INNER JOIN information_schema.index_columns ic
               ON i.table_schema = ic.index_table_schema
              AND i.table_name = ic.index_table_name
              AND i.index_name = ic.index_name
            WHERE i.table_schema = CURRENT_SCHEMA
              AND i.table_name = %s
            """,
            [table_name]
        )
        saw = {}
        indexes = {}
        for i_name,c_name,is_primary,is_unique in cursor.fetchall():
            # Should only return single-column indexes, track and skip compound.
            prev_col = saw.get(i_name, False)
            if prev_col:
                indexes.pop(prev_col, None)
            else:
                # Need the union of all values for a given column for those that
                # are over indexed (e.g. self-reference FK to the PK)
                info = indexes.setdefault(c_name, { PK: False, UK: False })
                info[PK] |= is_primary
                info[UK] |= is_unique
                saw[i_name] = c_name
        return indexes

    if DJANGO_GTEQ_1_7:
        def get_constraints(self, cursor, table_name):
            """
            Retrieves any constraints or keys (unique, pk, fk, check, index)
            across one or more columns.

            Returns a dict mapping constraint names to their attributes,
            where attributes is a dict with keys:
             * columns: List of columns this covers
             * primary_key: True if primary key, False otherwise
             * unique: True if this is a unique constraint, False otherwise
             * foreign_key: (table, column) of target, or None
             * check: True if check constraint, False otherwise
             * index: True if index, False otherwise.
            """
            constraints = {}
            # Get PRIMARY and UNIQUE.
            cursor.execute(
                """
                SELECT tc.constraint_name,
                       tc.constraint_type = 'PRIMARY KEY',
                       kcu.column_name
                FROM information_schema.table_constraints tc
                INNER JOIN information_schema.key_column_usage kcu
                    USING (constraint_schema, constraint_name)
                WHERE tc.table_schema = CURRENT_SCHEMA
                  AND tc.table_name = %s
                  AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                ORDER BY tc.constraint_name, kcu.ordinal_position
                """,
                [table_name]
            )
            for con_name, is_primary, col_name in cursor.fetchall():
                con = constraints.get(con_name, None)
                if not con:
                    con = {
                        'columns': [],
                        'primary_key': is_primary,
                        'unique': True,
                        'foreign_key': None,
                        'check': False,
                        'index': False,
                    }
                    constraints[con_name] = con
                con['columns'].append(col_name)
            # Then FOREIGN KEY.
            # NB: Referenced table schema left out as Django doesn't want it.
            cursor.execute(
                """
                SELECT rc.constraint_name,
                       kcu1.column_name,
                       kcu2.table_name,
                       kcu2.column_name
                FROM information_schema.referential_constraints rc
                INNER JOIN information_schema.key_column_usage kcu1
                    USING (constraint_schema, constraint_name)
                INNER JOIN information_schema.key_column_usage kcu2
                    ON rc.unique_constraint_schema = kcu2.constraint_schema
                   AND rc.unique_constraint_name = kcu2.constraint_name
                   AND kcu1.position_in_unique_constraint = kcu2.ordinal_position
                WHERE rc.constraint_schema = CURRENT_SCHEMA
                  AND kcu1.table_schema = CURRENT_SCHEMA
                  AND kcu1.table_name = %s
                ORDER BY rc.constraint_name
                """,
                [table_name]
            )
            for con_name, col_name, ref_table, ref_col in cursor.fetchall():
                # Only allowed to return 1 ref column
                assert con_name not in constraints
                constraints[con_name] = {
                    'columns': [col_name],
                    'primary_key': False,
                    'unique': True,
                    'foreign_key': (ref_table, ref_col),
                    'check': False,
                    'index': False,
                }
            # Then INDEXES.
            # NB: Needs to leave out ones backing PRIMARY or UNIQUE as Django only wants
            #     them once *even if* the constraint name does not match index name.
            # NB: Also exclude group and spatial indexes as not-managed by Django.
            cursor.execute(
                """
                SELECT i.index_name,
                       ic.column_name
                FROM information_schema.indexes i
                INNER JOIN information_schema.index_columns ic
                   ON i.table_schema = ic.index_table_schema
                  AND i.table_name = ic.index_table_name
                  AND i.index_name = ic.index_name
                WHERE i.table_schema = CURRENT_SCHEMA
                  AND i.table_name = %s
                  AND i.index_type = 'INDEX'
                  AND i.join_type IS NULL
                  AND i.index_method IS NULL
                ORDER BY ic.index_name, ic.ordinal_position
                """,
                [table_name]
            )
            for con_name, col_name in cursor.fetchall():
                con = constraints.get(con_name, None)
                # This needs to leave out indexes backing PRIMARY or UNIQUE
                if not con:
                    con = {
                        'columns': [],
                        'primary_key': False,
                        'unique': False,
                        'foreign_key': None,
                        'check': False,
                        'index': True,
                    }
                    constraints[con_name] = con
                elif not con['index']:
                    # Skip over any not added in this pass
                    continue
                con['columns'].append(col_name)
            return constraints

    #
    # Internal Methods
    #

    def _fdb_get_key_columns(self, cursor, table_name):
        """
        Returns a list of (column_name, ref_table_name, ref_column_name)
        for all referenced key columns in given table.
        """
        cursor.execute(
            """
            SELECT kcu.column_name,
                   o_kcu.table_name ref_table,
                   o_kcu.column_name ref_column
            FROM information_schema.referential_constraints rc
            INNER JOIN information_schema.key_column_usage kcu
               ON rc.constraint_name = kcu.constraint_name
              AND rc.constraint_schema = kcu.constraint_schema
            INNER JOIN information_schema.key_column_usage o_kcu
               ON rc.unique_constraint_schema = o_kcu.constraint_schema
              AND rc.unique_constraint_name = o_kcu.constraint_name
              AND kcu.position_in_unique_constraint = o_kcu.ordinal_position
            WHERE rc.constraint_schema = CURRENT_SCHEMA
              AND kcu.table_name = %s
            """,
            [table_name]
        )
        key_columns = cursor.fetchall()
        return key_columns

    def _fdb_col_positions(self, cursor, table_name):
        cursor.execute(
            """
            SELECT column_name,
                   CAST(ordinal_position AS INT)
            FROM information_schema.columns
            WHERE table_schema = CURRENT_SCHEMA
              AND table_name = %s
            """,
            [table_name]
        )
        name_to_index = {}
        for row in cursor.fetchall():
            name_to_index[row[0]] = row[1]
        return name_to_index

