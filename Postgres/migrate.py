import sqlite3
import psycopg2
import os
import csv
from collections import defaultdict
import re

# Source SQLite database
SQLITE_DB_PATH = "./olist.sqlite"

# PostgreSQL connection parameters
PG_CONN = {
    "dbname": "mydb",
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5432",
}


def clean_table_name(name):
    """Clean table name for PostgreSQL"""
    return re.sub(r"[^a-zA-Z0-9_]", "", name.lower())


def get_sqlite_schema():
    """Get complete schema info including foreign keys from SQLite"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]

    schema_info = {}
    foreign_keys = defaultdict(list)

    for table in tables:
        # Get table columns
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()

        # Get primary keys
        primary_keys = [col[1] for col in columns if col[5] > 0]  # col[5] is pk

        # Get foreign keys
        cursor.execute(f"PRAGMA foreign_key_list({table})")
        fks = cursor.fetchall()

        # Store foreign key info
        for fk in fks:
            foreign_keys[table].append(
                {
                    "id": fk[0],
                    "seq": fk[1],
                    "table": fk[2],
                    "from": fk[3],
                    "to": fk[4],
                    "on_update": fk[5],
                    "on_delete": fk[6],
                    "match": fk[7],
                }
            )

        # Store table schema
        schema_info[table] = {
            "columns": columns,
            "primary_keys": primary_keys,
        }

    conn.close()
    return schema_info, foreign_keys


def type_map(sqlite_type):
    """Map SQLite types to PostgreSQL types"""
    sqlite_type = sqlite_type.upper()
    if "INT" in sqlite_type:
        return "INTEGER"
    elif "CHAR" in sqlite_type or "TEXT" in sqlite_type or "CLOB" in sqlite_type:
        return "TEXT"
    elif "REAL" in sqlite_type or "FLOA" in sqlite_type or "DOUB" in sqlite_type:
        return "FLOAT"
    elif "BLOB" in sqlite_type:
        return "BYTEA"
    elif "BOOL" in sqlite_type:
        return "BOOLEAN"
    elif "DATE" in sqlite_type or "TIME" in sqlite_type:
        return "TIMESTAMP"
    else:
        return "TEXT"  # Default


def check_for_duplicate_keys(schema_info):
    """Check for duplicate primary key values in the database"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()

    duplicates = {}

    for table, info in schema_info.items():
        primary_keys = info["primary_keys"]
        if not primary_keys:
            continue

        # Build a query to check for duplicates
        pk_cols = ", ".join(primary_keys)
        query = f"""
        SELECT {pk_cols}, COUNT(*) as cnt
        FROM {table}
        GROUP BY {pk_cols}
        HAVING COUNT(*) > 1
        """

        try:
            cursor.execute(query)
            dups = cursor.fetchall()
            if dups:
                duplicates[table] = dups
        except sqlite3.Error as e:
            print(f"Error checking for duplicates in {table}: {e}")

    conn.close()
    return duplicates


def create_postgres_schema(schema_info, foreign_keys):
    """Create PostgreSQL schema based on SQLite schema"""
    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(**PG_CONN)
    pg_cursor = pg_conn.cursor()

    # First pass: Create tables with columns but without constraints
    for table, info in schema_info.items():
        columns = []
        for col in info["columns"]:
            name = col[1]
            col_type = type_map(col[2])
            nullable = "" if col[3] else " NOT NULL"
            default = f" DEFAULT {col[4]}" if col[4] is not None else ""

            columns.append(f"{name} {col_type}{nullable}{default}")

        # Create table
        clean_table = clean_table_name(table)
        create_sql = (
            f"CREATE TABLE IF NOT EXISTS {clean_table} (\n  "
            + ",\n  ".join(columns)
            + "\n);"
        )
        try:
            pg_cursor.execute(create_sql)
            print(f"Created table: {clean_table}")
        except Exception as e:
            print(f"Error creating table {clean_table}: {e}")

    pg_conn.commit()

    # Second pass: Add primary keys
    for table, info in schema_info.items():
        if info["primary_keys"]:
            clean_table = clean_table_name(table)
            pk_cols = ", ".join(info["primary_keys"])
            try:
                pg_cursor.execute(
                    f"ALTER TABLE {clean_table} ADD PRIMARY KEY ({pk_cols});"
                )
                print(f"Added primary key to {clean_table}: {pk_cols}")
            except Exception as e:
                print(f"Error adding primary key to {clean_table}: {e}")
                print("Creating unique index instead...")
                try:
                    # Create a unique index instead
                    pg_cursor.execute(
                        f"CREATE UNIQUE INDEX idx_{clean_table}_pk ON {clean_table}({pk_cols});"
                    )
                    print(f"Created unique index on {clean_table}: {pk_cols}")
                except Exception as e:
                    print(f"Error creating unique index on {clean_table}: {e}")

    pg_conn.commit()

    # Third pass: Add foreign keys
    for table, fks in foreign_keys.items():
        clean_table = clean_table_name(table)
        for fk in fks:
            referenced_table = clean_table_name(fk["table"])
            fk_name = f"fk_{clean_table}_{fk['from']}_{referenced_table}_{fk['to']}"
            on_delete = (
                f" ON DELETE {fk['on_delete']}"
                if fk["on_delete"] != "NO ACTION"
                else ""
            )

            try:
                alter_sql = f"""
                ALTER TABLE {clean_table} 
                ADD CONSTRAINT {fk_name} 
                FOREIGN KEY ({fk['from']}) 
                REFERENCES {referenced_table}({fk['to']}){on_delete};
                """
                pg_cursor.execute(alter_sql)
                print(
                    f"Added foreign key: {clean_table}.{fk['from']} -> {referenced_table}.{fk['to']}"
                )
            except Exception as e:
                print(
                    f"Error adding foreign key {clean_table}.{fk['from']} -> {referenced_table}.{fk['to']}: {e}"
                )

    pg_conn.commit()
    pg_conn.close()


def import_data(schema_info):
    """Import data from SQLite to PostgreSQL"""
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
    sqlite_cursor = sqlite_conn.cursor()

    # Connect to PostgreSQL
    pg_conn = psycopg2.connect(**PG_CONN)
    pg_cursor = pg_conn.cursor()

    # Process each table
    for table, info in schema_info.items():
        clean_table = clean_table_name(table)

        # Get column names
        column_names = [col[1] for col in info["columns"]]
        columns_str = ", ".join(column_names)

        # Export data
        sqlite_cursor.execute(f"SELECT {columns_str} FROM {table}")
        rows = sqlite_cursor.fetchall()

        if not rows:
            print(f"No data in table {table}")
            continue

        # Import data in batches
        batch_size = 1000
        placeholders = ", ".join(["%s"] * len(column_names))
        insert_sql = (
            f"INSERT INTO {clean_table} ({columns_str}) VALUES ({placeholders})"
        )

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            try:
                pg_cursor.executemany(insert_sql, batch)
                pg_conn.commit()  # Commit each batch
                print(
                    f"Imported {len(batch)} rows into {clean_table} (total: {i+len(batch)})"
                )
            except Exception as e:
                pg_conn.rollback()
                print(f"Error importing data into {clean_table}: {e}")

                # Try one by one if batch fails
                for row in batch:
                    try:
                        # Convert empty strings to None
                        processed_row = [None if val == "" else val for val in row]
                        pg_cursor.execute(insert_sql, processed_row)
                        pg_conn.commit()
                    except Exception as e2:
                        pg_conn.rollback()
                        print(f"Error importing row into {clean_table}: {e2}")

    sqlite_conn.close()
    pg_conn.close()


def main():
    """Main migration function"""
    print("Analyzing SQLite schema...")
    schema_info, foreign_keys = get_sqlite_schema()

    print("Checking for duplicate primary keys...")
    duplicates = check_for_duplicate_keys(schema_info)
    if duplicates:
        print("Warning: Found duplicate primary keys in these tables:")
        for table, dups in duplicates.items():
            print(f"  {table}: {len(dups)} duplicate sets")

    print("Creating PostgreSQL schema...")
    create_postgres_schema(schema_info, foreign_keys)

    print("Importing data...")
    import_data(schema_info)

    print("Migration completed!")


if __name__ == "__main__":
    main()
