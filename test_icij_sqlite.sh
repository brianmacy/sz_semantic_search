#!/bin/bash

# Test script for ICIJ data with SQLite and NAME_SEM_KEY semantic search
# Uses the G2 build from ~/dev/G2/dev/build/dist

set -e  # Exit on error

echo "=========================================="
echo "ICIJ SQLite Semantic Search Test"
echo "=========================================="
echo ""

# Configuration
PROJECT_DIR="$HOME/open_dev/sz_semantic_search"
G2_DIR="$HOME/dev/G2/dev"
G2_BUILD="$G2_DIR/build/dist"
SZVEC_PATH="$G2_BUILD/lib/szvec.so"
DB_DIR="$PROJECT_DIR/test_db"
DB_PATH="$DB_DIR/icij_test.db"
ICIJ_DATA="$PROJECT_DIR/test_icij_sample.json"

# Test data size (use first N records for testing)
# Set to 0 to use all data, or specify custom file with ICIJ_DATA env var
TEST_RECORDS=1000

echo "Configuration:"
echo "  Project Dir: $PROJECT_DIR"
echo "  G2 Build: $G2_BUILD"
echo "  Database: $DB_PATH"
echo "  ICIJ Data: $ICIJ_DATA"
echo "  Test Records: $TEST_RECORDS (0 = all)"
echo ""

# Source the G2 environment
echo "Step 1: Setting up environment..."
source "$G2_DIR/setupEnv"

# Add G2 Python packages to path
export PYTHONPATH="$G2_BUILD/sdk/python:$PYTHONPATH"

# Verify szvec extension exists
if [ ! -f "$SZVEC_PATH" ]; then
    echo "✗ Error: szvec.so not found at $SZVEC_PATH"
    exit 1
fi
echo "✓ Found szvec extension: $SZVEC_PATH"

# Create database directory
mkdir -p "$DB_DIR"

# Remove old database if exists
if [ -f "$DB_PATH" ]; then
    echo "  Removing old database..."
    rm "$DB_PATH"
fi

# Create database from schema
echo ""
echo "Step 2: Creating SQLite database with G2 schema..."
SCHEMA_FILE="$G2_BUILD/resources/schema/szcore-schema-sqlite-create.sql"
if [ ! -f "$SCHEMA_FILE" ]; then
    echo "✗ Error: Schema file not found at $SCHEMA_FILE"
    exit 1
fi

echo "  Creating database from schema..."
sqlite3 "$DB_PATH" < "$SCHEMA_FILE"
echo "✓ Database created from schema"

# Initialize configuration using Python API
python3 << EOF
import sys
sys.path.insert(0, "$G2_BUILD/sdk/python")

from senzing_core import SzAbstractFactoryCore
import json

instance_name = "icij_test"
import os

license_key = os.getenv("SENZING_LICENSE_BASE64", "")
pipeline_config = {
    "CONFIGPATH": "$G2_BUILD/resources/templates",
    "RESOURCEPATH": "$G2_BUILD/resources",
    "SUPPORTPATH": "$G2_BUILD/data"
}

if license_key:
    pipeline_config["LICENSESTRINGBASE64"] = license_key

settings = {
    "PIPELINE": pipeline_config,
    "SQL": {
        "CONNECTION": "sqlite3://na:na@$DB_PATH?extensions=$SZVEC_PATH"
    }
}

print("  Initializing configuration...")
try:
    factory = SzAbstractFactoryCore(instance_name, json.dumps(settings))
    config_manager = factory.create_configmanager()

    # Create default config from template
    sz_config = config_manager.create_config_from_template()
    config_json = sz_config.export()

    # Register as default
    config_id = config_manager.register_config(config_json, "Initial configuration")
    config_manager.set_default_config_id(config_id)
    print(f"✓ Default configuration created (ID: {config_id})")

    # Initialize engine
    engine = factory.create_engine()
    engine.prime_engine()

    product = factory.create_product()
    version_data = json.loads(product.get_version())
    print(f"✓ Senzing Version: {version_data['VERSION']}")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo "✗ Database initialization failed"
    exit 1
fi

# Setup environment variable for subsequent scripts
if [ -n "$SENZING_LICENSE_BASE64" ]; then
    export SENZING_ENGINE_CONFIGURATION_JSON=$(cat << EOF
{
    "PIPELINE": {
        "CONFIGPATH": "$G2_BUILD/resources/templates",
        "RESOURCEPATH": "$G2_BUILD/resources",
        "SUPPORTPATH": "$G2_BUILD/data",
        "LICENSESTRINGBASE64": "$SENZING_LICENSE_BASE64"
    },
    "SQL": {
        "CONNECTION": "sqlite3://na:na@$DB_PATH?extensions=$SZVEC_PATH"
    }
}
EOF
)
else
    export SENZING_ENGINE_CONFIGURATION_JSON=$(cat << EOF
{
    "PIPELINE": {
        "CONFIGPATH": "$G2_BUILD/resources/templates",
        "RESOURCEPATH": "$G2_BUILD/resources",
        "SUPPORTPATH": "$G2_BUILD/data"
    },
    "SQL": {
        "CONNECTION": "sqlite3://na:na@$DB_PATH?extensions=$SZVEC_PATH"
    }
}
EOF
)
fi

echo ""
echo "Step 3: Setting up vector tables with szvec..."
cd "$PROJECT_DIR"
./setup_vector_tables.py --sqlite --szvec-path "$SZVEC_PATH" --db-path "$DB_PATH" --dimension 384

if [ $? -ne 0 ]; then
    echo "✗ Vector table setup failed"
    exit 1
fi

echo ""
echo "Step 4: Creating NAME_SEM_KEY feature type..."
./enable_semantic_candidates.py

if [ $? -ne 0 ]; then
    echo "✗ Feature creation failed"
    exit 1
fi

echo ""
echo "Step 5: Preparing test data..."
if [ $TEST_RECORDS -gt 0 ]; then
    echo "  Creating subset with first $TEST_RECORDS records..."
    head -n $TEST_RECORDS "$ICIJ_DATA" > "$DB_DIR/icij_subset.json"
    LOAD_FILE="$DB_DIR/icij_subset.json"
else
    echo "  Using full dataset ($(wc -l < $ICIJ_DATA) records)..."
    LOAD_FILE="$ICIJ_DATA"
fi

echo ""
echo "Step 6: Loading data with embeddings..."
echo "  This may take a while..."
./semantic_load.py "$LOAD_FILE" -x  # -x skips engine prime

if [ $? -ne 0 ]; then
    echo "✗ Data loading failed"
    exit 1
fi

echo ""
echo "Step 7: Verifying data loaded..."
sqlite3 "$DB_PATH" << EOF
.mode column
.headers on
SELECT 'OBS_ENT records' AS table_name, COUNT(*) AS count FROM OBS_ENT
UNION ALL
SELECT 'NAME_SEM_KEY vectors', COUNT(*) FROM NAME_SEM_KEY
UNION ALL
SELECT 'LIB_FEAT records', COUNT(*) FROM LIB_FEAT;
EOF

echo ""
echo "Step 8: Creating search queries..."
# Extract some sample names for searching
head -n 100 "$LOAD_FILE" | python3 -c "
import sys
import json
for i, line in enumerate(sys.stdin):
    if i >= 10:  # Create 10 search queries
        break
    rec = json.loads(line)
    search_rec = {
        'RECORD_ID': f'SEARCH_{i:03d}',
    }
    # Copy name fields
    for key in ['NAME_FULL', 'NAME_ORG', 'NAME_FIRST', 'NAME_LAST']:
        if key in rec:
            search_rec[key] = rec[key]
            break
    print(json.dumps(search_rec))
" > "$DB_DIR/search_queries.json"

echo "✓ Created $(wc -l < $DB_DIR/search_queries.json) search queries"

echo ""
echo "Step 9: Running semantic searches..."
./semantic_search.py "$DB_DIR/search_queries.json"

if [ $? -ne 0 ]; then
    echo "✗ Search failed"
    exit 1
fi

echo ""
echo "Step 10: Analyzing results..."
sqlite3 "$DB_PATH" << EOF
.mode column
.headers on

SELECT 'Total Entities' AS metric, COUNT(*) AS count FROM RES_ENT
UNION ALL
SELECT 'Entities with multiple records', COUNT(*) FROM (
    SELECT DSRC_ID, ENT_SRC_KEY FROM RES_ENT_OKEY GROUP BY DSRC_ID, ENT_SRC_KEY HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'Records loaded', COUNT(*) FROM OBS_ENT
UNION ALL
SELECT 'Vector embeddings', COUNT(*) FROM NAME_SEM_KEY;

EOF

echo ""
echo "=========================================="
echo "Test Complete!"
echo "=========================================="
echo ""
echo "Database location: $DB_PATH"
echo "Test files: $DB_DIR/"
echo ""
echo "To explore further:"
echo "  sqlite3 $DB_PATH"
echo "  sz_configtool  # (with SENZING_ENGINE_CONFIGURATION_JSON set)"
echo ""
echo "To test with more data, edit TEST_RECORDS at top of script"
