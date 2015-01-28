# FoundationDB SQL Layer Adapter for Django
# Copyright (c) 2013-2015 FoundationDB, LLC
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

def create_or_replace(cursor, quoted_schema_name, quoted_function_name="django_fdbsql_sequence_reset"):
    cursor.execute("""
CREATE OR REPLACE FUNCTION %s.%s
    (schema_name VARCHAR(128), table_name VARCHAR(128), column_name VARCHAR(128))
RETURNS INT LANGUAGE javascript PARAMETER STYLE java EXTERNAL NAME 'f' AS $$
    function f(schema_name, table_name, column_name) {
        var conn = java.sql.DriverManager.getConnection("jdbc:default:connection");
        // Safe identifiers
        var q_schema_name = '"' + schema_name.replace(/"/g, '""') + '"';
        var q_table_name = '"' + table_name.replace(/"/g, '""') + '"';
        var q_column_name = '"' + column_name.replace(/"/g, '""') + '"';
        // Find the associated sequence name
        var s = conn.createStatement();
        var rs = s.executeQuery(
            "SELECT QUOTE_IDENT(sequence_schema, '\\"', true), QUOTE_IDENT(sequence_name, '\\"', true) "+
            "FROM information_schema.columns "+
            "WHERE table_schema = '" + schema_name +
            "' AND table_name = '" + table_name +
            "' AND column_name = '" + column_name + "'"
        );
        var next_val = null;
        if(rs.next()) {
            var seq_schema = rs.getString(1);
            var seq_name = rs.getString(2);
            // Find how far we have to go
            rs = s.executeQuery("SELECT MAX(" + q_column_name  +") FROM " + q_schema_name + "." + q_table_name);
            rs.next();
            var max_col= rs.getObject(1);
            if(max_col == null) {
                // No rows yet
                next_val = 0;
            } else {
                // Bump until we hit the max
                var ps = conn.prepareStatement("SELECT NEXT VALUE FOR " + seq_schema + "." + seq_name);
                do {
                    rs = ps.executeQuery();
                    rs.next();
                    next_val = rs.getInt(1);
                    rs.close();
                } while(next_val < max_col);
                ps.close();
            }
            next_val += 1;
        }
        s.close();
        conn.close();
        return next_val;
        return 0;
    }
$$;
""" % (quoted_schema_name, quoted_function_name))
