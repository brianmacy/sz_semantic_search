# ICIJ SQLite Test - Quick Start Guide

**⚠️ DEVELOPMENT ENVIRONMENT ONLY**

This guide is for testing with a local G2 development build. Do not publish this file.
For production documentation, see [USAGE.md](USAGE.md) and [TESTING.md](TESTING.md).

---

This guide will help you test the semantic search with ICIJ data using SQLite and the G2 build.

## Prerequisites

- G2 build at `~/dev/G2/dev/build/dist`
- ICIJ data at `~/open_dev/sz_semantic_search/test_icij.json`
- Python packages: `fast-sentence-transformers`, `orjson`

## Quick Test (10,000 records)

```bash
cd ~/open_dev/sz_semantic_search
./test_icij_sqlite.sh
```

This will:
1. ✓ Source G2 environment (`setupEnv`)
2. ✓ Create SQLite database with G2 schema
3. ✓ Setup vector tables with szvec extension
4. ✓ Create NAME_SEM_KEY feature type
5. ✓ Load first 10,000 ICIJ records with embeddings
6. ✓ Generate 10 search queries
7. ✓ Run semantic searches
8. ✓ Show results and statistics

**Expected time:** ~5-10 minutes for 10,000 records

## Full Test (All ~2M records)

Edit `test_icij_sqlite.sh` and change:

```bash
TEST_RECORDS=0  # 0 = use all data
```

Then run:

```bash
./test_icij_sqlite.sh
```

**Expected time:** ~2-4 hours for full dataset (depends on CPU/GPU)

## What Gets Created

```
~/open_dev/sz_semantic_search/test_db/
├── icij_test.db           # SQLite database with G2 schema + vectors
├── icij_subset.json       # First 10k records (if TEST_RECORDS > 0)
└── search_queries.json    # Generated search queries
```

## Manual Step-by-Step

If you prefer to run steps manually:

### 1. Setup Environment

```bash
cd ~/open_dev/sz_semantic_search
source ~/dev/G2/dev/setupEnv

export PYTHONPATH="$HOME/dev/G2/dev/build/dist/python:$PYTHONPATH"

export SENZING_ENGINE_CONFIGURATION_JSON='{
    "PIPELINE": {
        "CONFIGPATH": "'$HOME'/dev/G2/dev/build/dist/resources/config",
        "RESOURCEPATH": "'$HOME'/dev/G2/dev/build/dist/resources",
        "SUPPORTPATH": "'$HOME'/dev/G2/dev/build/dist/data"
    },
    "SQL": {
        "CONNECTION": "sqlite3://na:na@'$HOME'/open_dev/sz_semantic_search/test_db/icij_test.db"
    }
}'
```

### 2. Initialize Database

```bash
mkdir -p test_db

python3 << 'EOF'
from senzing import SzAbstractFactory
import json
import os

settings_str = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
sz_factory = SzAbstractFactory("init", settings_str)
sz_engine = sz_factory.create_sz_engine()
sz_engine.prime_engine()
print("✓ Database initialized")
EOF
```

### 3. Setup Vector Tables

```bash
./setup_vector_tables.py \
    --sqlite \
    --szvec-path ~/dev/G2/dev/build/dist/lib/szvec.so \
    --db-path test_db/icij_test.db \
    --dimension 384
```

### 4. Create NAME_SEM_KEY

```bash
./enable_semantic_candidates.py --dry-run  # Preview
./enable_semantic_candidates.py            # Apply
```

### 5. Prepare Test Data

```bash
# Use subset for testing
head -n 10000 test_icij.json > test_db/icij_subset.json

# Or use full dataset
# cp test_icij.json test_db/icij_subset.json
```

### 6. Load Data

```bash
./semantic_load.py test_db/icij_subset.json -x
```

### 7. Create Search Queries

```bash
head -n 10 test_db/icij_subset.json | \
  python3 -c "
import sys, json
for i, line in enumerate(sys.stdin):
    rec = json.loads(line)
    search = {'RECORD_ID': f'SEARCH_{i}'}
    for k in ['NAME_FULL', 'NAME_ORG', 'NAME_FIRST', 'NAME_LAST']:
        if k in rec:
            search[k] = rec[k]
            break
    print(json.dumps(search))
" > test_db/search_queries.json
```

### 8. Run Searches

```bash
./semantic_search.py test_db/search_queries.json
```

## Verifying Results

### Check Database

```bash
sqlite3 test_db/icij_test.db << 'EOF'
.mode column
.headers on

-- Count records
SELECT COUNT(*) as total_records FROM OBS_ENT;

-- Count entities
SELECT COUNT(*) as total_entities FROM RES_ENT;

-- Count vector embeddings
SELECT COUNT(*) as vector_embeddings FROM NAME_SEM_KEY;

-- Show sample embeddings
SELECT LIB_FEAT_ID, LABEL FROM NAME_SEM_KEY LIMIT 5;

-- Check for merged entities (semantic matches)
SELECT COUNT(*) as merged_entities FROM (
    SELECT DSRC_ID, ENT_SRC_KEY
    FROM RES_ENT_OKEY
    GROUP BY DSRC_ID, ENT_SRC_KEY
    HAVING COUNT(*) > 1
);
EOF
```

### Check Configuration

```bash
sz_configtool << 'EOF'
getFeature NAME_SEM_KEY jsonl
listAttributes NAME_SEM_KEY
quit
EOF
```

### Manual Search Test

```bash
python3 << 'EOF'
from senzing import SzAbstractFactory, SzEngineFlags
import json
import os

settings_str = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
sz_factory = SzAbstractFactory("search", settings_str)
sz_engine = sz_factory.create_sz_engine()

# Search for a name
query = {"NAME_FULL": "John Smith"}
result = sz_engine.search_by_attributes(
    json.dumps(query),
    SzEngineFlags.SZ_SEARCH_BY_ATTRIBUTES_MINIMAL_ALL
)

data = json.loads(result)
print(f"Found {len(data['RESOLVED_ENTITIES'])} entities")
for entity in data['RESOLVED_ENTITIES'][:5]:
    print(f"  Entity {entity['ENTITY_ID']}: {entity.get('ENTITY_NAME', 'N/A')}")
EOF
```

## Performance Tuning

### Use GPU for Embeddings

Edit `semantic_load.py` and `semantic_search.py`:

```python
model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2",
    device="cuda",  # Change from "cpu" to "cuda"
)
```

### Increase Thread Count

```bash
export SENZING_THREADS_PER_PROCESS=40
```

### Adjust Test Size

```bash
# In test_icij_sqlite.sh
TEST_RECORDS=1000   # Smaller for quick tests
TEST_RECORDS=50000  # Medium test
TEST_RECORDS=0      # Full dataset
```

## Troubleshooting

### Error: "szvec.so not found"

**Check:**
```bash
ls ~/dev/G2/dev/build/dist/lib/szvec.so
```

**Solution:** Build G2 with vector extension support

### Error: "Module not found"

**Solution:**
```bash
pip install fast-sentence-transformers orjson
export PYTHONPATH="$HOME/dev/G2/dev/build/dist/python:$PYTHONPATH"
```

### Error: "Database is locked"

**Solution:** Close any other connections to the database

```bash
# Kill any running processes
pkill -f semantic_load.py
pkill -f semantic_search.py
```

### Slow Performance

**Solutions:**
- Use GPU for embeddings (device="cuda")
- Reduce TEST_RECORDS for initial testing
- Check HNSW index created: `SELECT name FROM sqlite_master WHERE type='index' AND name LIKE '%embedding%';`

### No Semantic Matches

**Check:**
1. Vector table populated: `SELECT COUNT(*) FROM NAME_SEM_KEY;`
2. NAME_SEM_KEY feature created: `sz_configtool` → `getFeature NAME_SEM_KEY`
3. Records have name fields: `head -5 test_icij.json`

## Expected Results

For 10,000 records:
- **Load time:** 5-10 minutes (CPU), 2-3 minutes (GPU)
- **Search time:** <1 second per query
- **Entities created:** ~9,500-9,800 (depends on duplicates in data)
- **Vector embeddings:** ~10,000 (one per record with name)

## Cleanup

```bash
# Remove test database and files
rm -rf test_db/

# Or keep database for further exploration
# Database is at: test_db/icij_test.db
```

## Next Steps

After successful test:
1. Analyze semantic matches with WHY
2. Compare with/without NAME_SEM_KEY
3. Tune HNSW parameters if needed
4. Test with production data
5. Deploy to production environment

## Files Created

- `test_db/icij_test.db` - SQLite database with G2 schema and vectors
- `test_db/icij_subset.json` - Test data subset (if using TEST_RECORDS)
- `test_db/search_queries.json` - Generated search queries

## Script Details

The `test_icij_sqlite.sh` script performs:
- Environment setup from G2 build
- Database initialization
- Vector table creation with szvec
- NAME_SEM_KEY configuration
- Data loading with embeddings
- Search query generation
- Semantic search execution
- Results analysis

All in a single automated run!
