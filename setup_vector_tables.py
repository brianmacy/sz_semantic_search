#! /usr/bin/env python3

import argparse
import orjson as json
import os
import sys
import sqlite3

# Import PostgreSQL libraries only when needed
try:
    import uritools
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

def get_postgresql_url(engine_config):
    """Extract PostgreSQL URL from Senzing engine config."""
    config = json.loads(engine_config)
    senzing_database_url = config["SQL"]["CONNECTION"]

    parsed = uritools.urisplit(senzing_database_url)
    if "schema" in parsed.getquerydict():
        print("Non-default schema not currently supported.")
        sys.exit(-1)

    if not parsed.port and len(parsed.path) <= 1:
        values = parsed.host.split(":")
        host = values[0]
        port = None
        path = None
        if len(values) > 2:
            port = values[1]
            path = "/" + values[2]
        else:
            path = "/" + values[1]

        mod_uri = uritools.uricompose(
            scheme=parsed.scheme,
            userinfo=parsed.userinfo,
            host=host,
            path=path,
            port=port,
            query=parsed.query,
            fragment=parsed.fragment,
        )
        return mod_uri

    return senzing_database_url


def setup_vector_tables(cursor, vector_dimension=384):
    """
    Setup pgvector tables for Sz's internal NAME_SEM_KEY support.

    Args:
        cursor: PostgreSQL database cursor
        vector_dimension: Dimension of the embedding vectors (default 384 for all-MiniLM-L6-v2)
    """

    print(f"Setting up vector tables with dimension {vector_dimension}...")

    # Enable pgvector extension
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA pg_catalog")
    print("✓ Enabled pgvector extension")

    # Create NAME_SEM_KEY table for Sz (candidate generation, no scoring)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS NAME_SEM_KEY (
            LIB_FEAT_ID BIGINT NOT NULL,
            LABEL VARCHAR(250) NOT NULL,
            EMBEDDING VECTOR({vector_dimension}),
            PRIMARY KEY(LIB_FEAT_ID)
        )
    """)
    print("✓ Created NAME_SEM_KEY table")

    # Create HNSW index for fast vector similarity search
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS name_sem_key_embedding_idx
        ON NAME_SEM_KEY USING hnsw (EMBEDDING vector_cosine_ops)
    """)
    print("✓ Created HNSW index on NAME_SEM_KEY.EMBEDDING")

    # Also create SEMANTIC_VALUE table (for scoring, if needed later)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS SEMANTIC_VALUE (
            LIB_FEAT_ID BIGINT NOT NULL,
            LABEL VARCHAR(250) NOT NULL,
            EMBEDDING VECTOR({vector_dimension}),
            PRIMARY KEY(LIB_FEAT_ID)
        )
    """)
    print("✓ Created SEMANTIC_VALUE table")

    # Create HNSW index for SEMANTIC_VALUE
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS semantic_value_embedding_idx
        ON SEMANTIC_VALUE USING hnsw (EMBEDDING vector_cosine_ops)
    """)
    print("✓ Created HNSW index on SEMANTIC_VALUE.EMBEDDING")

    # Also create NAME_EMBEDDING and BIZNAME_EMBEDDING tables (optional, for compatibility)
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS NAME_EMBEDDING (
            LIB_FEAT_ID BIGINT NOT NULL,
            LABEL VARCHAR(250) NOT NULL,
            EMBEDDING VECTOR({vector_dimension}),
            PRIMARY KEY(LIB_FEAT_ID)
        )
    """)
    print("✓ Created NAME_EMBEDDING table")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS name_embedding_embedding_idx
        ON NAME_EMBEDDING USING hnsw (EMBEDDING vector_cosine_ops)
    """)
    print("✓ Created HNSW index on NAME_EMBEDDING.EMBEDDING")

    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS BIZNAME_EMBEDDING (
            LIB_FEAT_ID BIGINT NOT NULL,
            LABEL VARCHAR(250) NOT NULL,
            EMBEDDING VECTOR({vector_dimension}),
            PRIMARY KEY(LIB_FEAT_ID)
        )
    """)
    print("✓ Created BIZNAME_EMBEDDING table")

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS bizname_embedding_embedding_idx
        ON BIZNAME_EMBEDDING USING hnsw (EMBEDDING vector_cosine_ops)
    """)
    print("✓ Created HNSW index on BIZNAME_EMBEDDING.EMBEDDING")

    print("\n✓ All vector tables created successfully!")


def setup_sqlite_vector_tables(conn, vector_dimension=384, szvec_path=None):
    """
    Setup SQLite vector tables using szvec extension.

    Args:
        conn: SQLite database connection
        vector_dimension: Dimension of the embedding vectors (default 384)
        szvec_path: Path to szvec.so extension (optional, uses default if not provided)
    """

    print(f"Setting up SQLite vector tables with dimension {vector_dimension}...")

    # Enable extension loading
    conn.enable_load_extension(True)

    cursor = conn.cursor()

    # Load szvec extension
    if szvec_path:
        cursor.execute(f"SELECT load_extension('{szvec_path}')")
        print(f"✓ Loaded szvec extension from {szvec_path}")
    else:
        # Try default path
        try:
            cursor.execute("SELECT load_extension('szvec')")
            print("✓ Loaded szvec extension")
        except sqlite3.OperationalError as e:
            print(f"\n✗ Error loading szvec extension: {e}", file=sys.stderr)
            print("\nPlease specify the path to szvec.so with --szvec-path", file=sys.stderr)
            print("Example: ./setup_vector_tables.py --sqlite --szvec-path /path/to/szvec.so", file=sys.stderr)
            raise

    # Create NAME_SEM_KEY virtual table (candidate generation, no scoring)
    cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS NAME_SEM_KEY USING szvec(
            LIB_FEAT_ID INTEGER PRIMARY KEY,
            LABEL TEXT,
            EMBEDDING FLOAT[{vector_dimension}] hnsw(M=16, ef_construction=200)
        )
    """)
    print("✓ Created NAME_SEM_KEY virtual table with HNSW index")

    # Create SEMANTIC_VALUE virtual table (for scoring, if needed later)
    cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS SEMANTIC_VALUE USING szvec(
            LIB_FEAT_ID INTEGER PRIMARY KEY,
            LABEL TEXT,
            EMBEDDING FLOAT[{vector_dimension}] hnsw(M=16, ef_construction=200)
        )
    """)
    print("✓ Created SEMANTIC_VALUE virtual table with HNSW index")

    # Also create NAME_EMBEDDING and BIZNAME_EMBEDDING tables (optional, for compatibility)
    cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS NAME_EMBEDDING USING szvec(
            LIB_FEAT_ID INTEGER PRIMARY KEY,
            LABEL TEXT,
            EMBEDDING FLOAT[{vector_dimension}] hnsw(M=16, ef_construction=200)
        )
    """)
    print("✓ Created NAME_EMBEDDING virtual table with HNSW index")

    cursor.execute(f"""
        CREATE VIRTUAL TABLE IF NOT EXISTS BIZNAME_EMBEDDING USING szvec(
            LIB_FEAT_ID INTEGER PRIMARY KEY,
            LABEL TEXT,
            EMBEDDING FLOAT[{vector_dimension}] hnsw(M=16, ef_construction=200)
        )
    """)
    print("✓ Created BIZNAME_EMBEDDING virtual table with HNSW index")

    conn.commit()
    print("\n✓ All SQLite vector tables created successfully!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Setup vector tables for Sz NAME_SEM_KEY support (PostgreSQL or SQLite)"
    )
    parser.add_argument(
        "-d", "--dimension",
        type=int,
        default=384,
        help="Vector dimension (default 384 for all-MiniLM-L6-v2)"
    )
    parser.add_argument(
        "--sqlite",
        action="store_true",
        help="Use SQLite with szvec extension instead of PostgreSQL"
    )
    parser.add_argument(
        "--szvec-path",
        type=str,
        help="Path to szvec.so extension for SQLite (optional)"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        help="Path to SQLite database file (optional, uses config if not specified)"
    )
    args = parser.parse_args()

    engine_config = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
    if not engine_config:
        print(
            "The environment variable SENZING_ENGINE_CONFIGURATION_JSON must be set with a proper JSON configuration.",
            file=sys.stderr,
        )
        sys.exit(-1)

    try:
        if args.sqlite:
            # SQLite mode
            if args.db_path:
                db_path = args.db_path
            else:
                # Extract from config
                config = json.loads(engine_config)
                db_url = config["SQL"]["CONNECTION"]
                # Parse SQLite URL (e.g., sqlite3://na:na@/path/to/db.db)
                if "sqlite3://" in db_url:
                    db_path = db_url.split("@")[-1]
                else:
                    print("Could not extract SQLite path from config. Use --db-path", file=sys.stderr)
                    sys.exit(-1)

            print(f"Connecting to SQLite database: {db_path}")
            conn = sqlite3.connect(db_path)

            setup_sqlite_vector_tables(conn, args.dimension, args.szvec_path)

            conn.close()
            print("\n✓ Setup complete!")

        else:
            # PostgreSQL mode (default)
            url = get_postgresql_url(engine_config)
            print(f"Connecting to PostgreSQL database...")
            conn = psycopg2.connect(url)
            conn.autocommit = True

            cursor = conn.cursor()
            setup_vector_tables(cursor, args.dimension)

            cursor.close()
            conn.close()

            print("\n✓ Setup complete!")

    except Exception as ex:
        import traceback
        traceback.print_exc()
        print(f"\n✗ Error: {ex}", file=sys.stderr)
        sys.exit(-1)
