from django.db.backends import BaseDatabaseIntrospection

class DatabaseIntrospection(BaseDatabaseIntrospection):
    data_types_reverse = {
        16: 'BooleanField',
        20: 'BigIntegerField',
        21: 'SmallIntegerField',
        23: 'IntegerField',
        25: 'TextField',
        700: 'FloatField',
        701: 'FloatField',
        869: 'IPAddressField',
        1043: 'CharField',
        1082: 'DateField',
        1083: 'TimeField',
        1114: 'DateTimeField',
        1184: 'DateTimeField',
        1266: 'TimeField',
        1700: 'DecimalField',
    }
        
    def get_table_list(self, cursor):
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = CURRENT_SCHEMA
        """)
        return [row[0] for row in cursor.fetchall()]

    def get_table_description(self, cursor, table_name):
        "Returns a description of the table, with the DB-API cursor.description interface."
        # As cursor.description does not return reliably the nullable property,
        # we have to query the information_schema (#7783)
        cursor.execute("""
            SELECT column_name, is_nullable
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = CURRENT_SCHEMA
        """, [self.connection.ops.quote_name(table_name)])
        null_map = dict(cursor.fetchall())
        cursor.execute("SELECT * FROM %s LIMIT 1" % self.connection.ops.quote_name(table_name))
        return [line[:6] + (null_map[line[0]]=='YES',)
                for line in cursor.description]
    
    # TODO
    #def get_relations(self, cursor, table_name):
    #    """
    #    Returns a dictionary of {field_index: (field_index_other_table, other_table)}
    #    representing all relationships to the given table. Indexes are 0-based.
    #    """
    #    cursor.execute("""
    #        SELECT con.conkey, con.confkey, c2.relname
    #        FROM pg_constraint con, pg_class c1, pg_class c2
    #        WHERE c1.oid = con.conrelid
    #            AND c2.oid = con.confrelid
    #            AND c1.relname = %s
    #            AND con.contype = 'f'""", [table_name])
    #    relations = {}
    #    for row in cursor.fetchall():
    #        # row[0] and row[1] are single-item lists, so grab the single item.
    #        relations[row[0][0] - 1] = (row[1][0] - 1, row[2])

    def get_indexes(self, cursor, table_name):
        """
        Return dict of column names that exists as first in an index.
        Maps to a dict containing True|False for primary_key and unique
        """
        # This query retrieves each index on the given table, including the
        # first associated field name
        cursor.execute("""
            SELECT ic.column_name, i.index_name = 'PRIMARY', i.is_unique = 'YES'
            FROM information_schema.indexes i
            INNER JOIN information_schema.index_columns ic 
                ON i.schema_name = ic.schema_name
                AND i.table_name = ic.index_table_name
            WHERE
                i.schema_name = CURRENT_SCHEMA
                AND i.table_name = %s
                AND ic.ordinal_position = 0
                AND i.index_type IN ('INDEX', 'PRIMARY', 'UNIQUE')
        """, [self.connection.ops.quote_name(table_name)])
        indexes = {}
        for row in cursor.fetchall():
            col_name = row[0]
            props = indexes.get(col_name, None)
            if props is None:
                props = { 'primary_key': False, 'unique': False }
            props['primary_key'] |= row[1]
            props['uniqu'] |= row[2]
            indexes[col_name] = props
        return indexes

