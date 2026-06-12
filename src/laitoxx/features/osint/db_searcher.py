import os
import json
from laitoxx.features.utilities.shared_utils import Color
from laitoxx.core.settings.paths import _ROOT


def search_database():
    """
    Searches for data in files located in the 'bd' directory.
    Supports CSV, TXT, JSON, SQL dumps (line-by-line text matching).
    Supports SQLite (.db, .sqlite) natively via sqlite3.
    Supports MongoDB BSON dumps (.bson) natively via pymongo.
    Supports blazingly fast .parquet search via DuckDB.
    """
    db_dir = os.path.join(_ROOT, "bd")
    if not os.path.exists(db_dir) or not os.path.isdir(db_dir):
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} Directory '{db_dir}' does not exist. Please create it and add files for searching."
        )
        return

    files_in_db = [
        f for f in os.listdir(db_dir) if os.path.isfile(os.path.join(db_dir, f))
    ]

    if not files_in_db:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No database files found in the '{db_dir}' directory."
        )
        return

    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} {len(files_in_db)} databases found.\n"
    )

    data_to_search = input(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Enter data to search: "
    )
    if data_to_search is None:
        return

    if not data_to_search:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.DARK_RED} No search data provided."
        )
        return

    print(
        f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} Searching...\n"
    )

    found_results = False

    has_duckdb = False
    try:
        import duckdb

        has_duckdb = True
    except ImportError:
        pass

    for filename in files_in_db:
        filepath = os.path.join(db_dir, filename)

        # --- PARQUET SEARCH via DuckDB ---
        if filename.lower().endswith(".parquet"):
            if not has_duckdb:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.YELLOW} Skipping {filename}: 'duckdb' not installed."
                )
                continue

            try:
                conn = duckdb.connect()
                cols_info = conn.execute(
                    f"DESCRIBE SELECT * FROM '{filepath}'"
                ).fetchall()
                col_names = [c[0] for c in cols_info]

                safe_search = data_to_search.replace("'", "''")
                where_clauses = [
                    f"CAST(\"{c}\" AS VARCHAR) ILIKE '%{safe_search}%'"
                    for c in col_names
                ]
                where_stmt = " OR ".join(where_clauses)

                query = f"SELECT * FROM '{filepath}' WHERE {where_stmt} LIMIT 100"
                results = conn.execute(query).fetchall()
                conn.close()

                if results:
                    if not found_results:
                        print(
                            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search Results:\n"
                        )
                        found_results = True

                    for row in results:
                        formatted_result = (
                            f"{Color.DARK_RED}┌─[ {Color.LIGHT_RED}{filename} (Parquet) {Color.DARK_RED}]─"
                            + "─" * 20
                            + "\n"
                        )
                        for i, val in enumerate(row):
                            formatted_result += f"{Color.DARK_RED}│ {Color.LIGHT_RED}{col_names[i]}: {Color.WHITE}{val}\n"
                        formatted_result += (
                            f"{Color.DARK_RED}└" + "─" * (30 + len(filename)) + "\n"
                        )
                        print(formatted_result)
            except Exception as e:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error reading parquet {filename}: {e}"
                )

            continue

        # --- SQLITE SEARCH ---
        elif filename.lower().endswith((".db", ".sqlite", ".sqlite3")):
            import sqlite3

            try:
                conn = sqlite3.connect(filepath)
                cursor = conn.cursor()

                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]

                for table in tables:
                    cursor.execute(f"PRAGMA table_info('{table}')")
                    columns = [row[1] for row in cursor.fetchall()]
                    if not columns:
                        continue

                    safe_search = data_to_search.replace("'", "''")
                    where_clauses = [
                        f"CAST(\"{c}\" AS TEXT) LIKE '%{safe_search}%'" for c in columns
                    ]
                    where_stmt = " OR ".join(where_clauses)

                    query = f'SELECT * FROM "{table}" WHERE {where_stmt} LIMIT 100'

                    try:
                        cursor.execute(query)
                        results = cursor.fetchall()

                        if results:
                            if not found_results:
                                print(
                                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search Results:\n"
                                )
                                found_results = True

                            for row in results:
                                formatted_result = (
                                    f"{Color.DARK_RED}┌─[ {Color.LIGHT_RED}{filename} -> Table: {table} (SQLite) {Color.DARK_RED}]─"
                                    + "─" * 10
                                    + "\n"
                                )
                                for i, val in enumerate(row):
                                    formatted_result += f"{Color.DARK_RED}│ {Color.LIGHT_RED}{columns[i]}: {Color.WHITE}{val}\n"
                                formatted_result += (
                                    f"{Color.DARK_RED}└"
                                    + "─" * (30 + len(filename))
                                    + "\n"
                                )
                                print(formatted_result)
                    except sqlite3.OperationalError:
                        pass  # Ignore tables that might have query issues

                conn.close()
            except Exception as e:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error reading SQLite {filename}: {e}"
                )

            continue

        # --- MONGODB BSON SEARCH ---
        elif filename.lower().endswith(".bson"):
            try:
                import bson

                with open(filepath, "rb") as f:
                    for doc in bson.decode_file_iter(f):
                        doc_str = json.dumps(doc, default=str, ensure_ascii=False)
                        if data_to_search.lower() in doc_str.lower():
                            if not found_results:
                                print(
                                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search Results:\n"
                                )
                                found_results = True

                            formatted_result = (
                                f"{Color.DARK_RED}┌─[ {Color.LIGHT_RED}{filename} (MongoDB BSON) {Color.DARK_RED}]─"
                                + "─" * 15
                                + "\n"
                            )
                            for k, v in doc.items():
                                formatted_result += f"{Color.DARK_RED}│ {Color.LIGHT_RED}{k}: {Color.WHITE}{v}\n"
                            formatted_result += (
                                f"{Color.DARK_RED}└" + "─" * (30 + len(filename)) + "\n"
                            )
                            print(formatted_result)
            except ImportError:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.YELLOW} Skipping {filename}: 'pymongo' not installed."
                )
            except Exception as e:
                print(
                    f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error reading BSON {filename}: {e}"
                )

            continue

        # --- TEXT SEARCH (CSV/TXT/JSON/SQL) ---
        try:
            with open(filepath, "r", encoding="UTF-8", errors="ignore") as f:
                header_line = f.readline().strip()
                delimiters = [",", ";", "\t", "|"]
                delimiter = next((d for d in delimiters if d in header_line), None)
                header = header_line.split(delimiter) if delimiter else [header_line]

                for line in f:
                    if data_to_search in line:
                        if not found_results:
                            print(
                                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_GREEN} Search Results:\n"
                            )
                            found_results = True

                        formatted_result = (
                            f"{Color.DARK_RED}┌─[ {Color.LIGHT_RED}{filename} {Color.DARK_RED}]─"
                            + "─" * 30
                            + "\n"
                        )

                        line_parts = (
                            line.strip().split(delimiter)
                            if delimiter
                            else [line.strip()]
                        )

                        for i, part in enumerate(line_parts):
                            header_name = (
                                header[i] if i < len(header) else f"Field {i + 1}"
                            )
                            formatted_result += f"{Color.DARK_RED}│ {Color.LIGHT_RED}{header_name.strip()}: {Color.WHITE}{part.strip()}\n"

                        formatted_result += (
                            f"{Color.DARK_RED}└" + "─" * (40 + len(filename)) + "\n"
                        )
                        print(formatted_result)
                        break

        except FileNotFoundError:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error: File not found {filename}"
            )
        except Exception as e:
            print(
                f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.LIGHT_RED} Error reading file {filename}: {e}"
            )

    if not found_results:
        print(
            f"{Color.DARK_GRAY}[{Color.DARK_RED}⛧{Color.DARK_GRAY}]{Color.RED} No matches found."
        )
