# Testing and Validation Checklist

## Prerequisites

- [ ] Senzing SDK installed with Advanced Search license
- [ ] Database configured (PostgreSQL with pgvector OR SQLite with szvec)
- [ ] Python 3.10+ with required packages
- [ ] SENZING_ENGINE_CONFIGURATION_JSON environment variable set

## Phase 1: Environment Validation

### Check Senzing Installation

```bash
# Check environment variable
echo $SENZING_ENGINE_CONFIGURATION_JSON

# Verify Python packages
python3 -c "import senzing_core; print('✓ senzing_core installed')"
python3 -c "import orjson; print('✓ orjson installed')"
python3 -c "from fast_sentence_transformers import FastSentenceTransformer; print('✓ fast_sentence_transformers installed')"

# For PostgreSQL
python3 -c "import psycopg2; import pgvector; print('✓ PostgreSQL packages installed')"

# Check Senzing version
python3 -c "import senzing_core; factory = senzing_core.SzAbstractFactoryCore('test', '$SENZING_ENGINE_CONFIGURATION_JSON'); print(factory.create_product().get_version())"
```

**Expected:** All checks pass without errors

### Check Database Connection

```bash
# For PostgreSQL - verify pgvector extension
psql <your_db> -c "SELECT * FROM pg_extension WHERE extname='vector';"

# For SQLite - verify szvec extension loads
sqlite3 <your_db> "SELECT load_extension('/path/to/szvec.so');"
```

**Expected:** Extensions are available

## Phase 2: Vector Table Setup

### Run setup_vector_tables.py

```bash
# PostgreSQL (default)
./setup_vector_tables.py

# PostgreSQL with custom dimension
./setup_vector_tables.py --dimension 768

# SQLite (set SENZING_ENGINE_CONFIGURATION_JSON to point to SQLite)
./setup_vector_tables.py --sqlite
```

**Expected Output:**
```
Setting up vector tables with dimension 384...
✓ Enabled pgvector extension (or loaded szvec)
✓ Created NAME_SEM_KEY table
✓ Created HNSW index on NAME_SEM_KEY.EMBEDDING
✓ Created SEMANTIC_VALUE table
✓ Created HNSW index on SEMANTIC_VALUE.EMBEDDING
...
✓ Setup complete!
```

### Verify Tables Created

```bash
# PostgreSQL
psql <your_db> -c "\d NAME_SEM_KEY"
psql <your_db> -c "SELECT indexname FROM pg_indexes WHERE tablename='name_sem_key';"

# SQLite
sqlite3 <your_db> ".schema NAME_SEM_KEY"
sqlite3 <your_db> "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%SEM%';"
```

**Expected:** Tables exist with EMBEDDING column and HNSW indexes

## Phase 3: Configuration - Create NAME_SEM_KEY

### Dry Run Test

```bash
./enable_semantic_candidates.py --dry-run
```

**Expected Output:**
```
Initializing Senzing SDK...
✓ Current default config ID: <number>
✓ Configuration exported
Creating NAME_SEM_KEY feature type...
✓ Found SEMANTIC_VALUE feature type (FTYPE_ID: 99)
✓ Created NAME_SEM_KEY feature type (FTYPE_ID: <new_id>)
  USED_FOR_CAND: Yes (candidates enabled)
  SHOW_IN_MATCH_KEY: No (scoring disabled)
✓ Found 3 SEMANTIC_VALUE attributes to copy
  ✓ Created attribute: NAME_SEM_KEY_EMBEDDING (ATTR_ID: <id>)
  ✓ Created attribute: NAME_SEM_KEY_LABEL (ATTR_ID: <id>)
  ✓ Created attribute: NAME_SEM_KEY_ALGORITHM (ATTR_ID: <id>)
✓ Found 3 FBOM entries to copy

[DRY RUN] Changes would be applied but not committed
```

**Validation:**
- [ ] No errors or exceptions
- [ ] NAME_SEM_KEY feature created
- [ ] Three attributes created
- [ ] FBOM entries copied

### Apply Configuration

```bash
./enable_semantic_candidates.py
```

**Expected Output:**
```
...
✓ New configuration added with ID: <new_id>
✓ Configuration <new_id> set as default

SUCCESS: NAME_SEM_KEY feature type created
```

**Validation:**
- [ ] Configuration ID incremented
- [ ] No errors
- [ ] Success message displayed

### Verify Configuration with sz_configtool

```bash
# Start sz_configtool
sz_configtool

# In sz_configtool:
sz_configtool> getFeature NAME_SEM_KEY jsonl
sz_configtool> listAttributes NAME_SEM_KEY
sz_configtool> quit
```

**Expected:**
- [ ] NAME_SEM_KEY feature exists
- [ ] candidates: "Yes"
- [ ] matchKey: "No"
- [ ] comparison: "" (empty/not present)
- [ ] Three attributes: NAME_SEM_KEY_EMBEDDING, NAME_SEM_KEY_LABEL, NAME_SEM_KEY_ALGORITHM

## Phase 4: Data Loading

### Create Test Data

```bash
cat > test_load.json << 'EOF'
{"DATA_SOURCE": "TEST", "RECORD_ID": "001", "NAME_FULL": "John Smith", "PHONE_NUMBER": "555-1234"}
{"DATA_SOURCE": "TEST", "RECORD_ID": "002", "NAME_FULL": "Jon Smyth", "EMAIL": "jon@example.com"}
{"DATA_SOURCE": "TEST", "RECORD_ID": "003", "NAME_FIRST": "Jane", "NAME_LAST": "Doe", "PHONE_NUMBER": "555-5678"}
EOF
```

### Load Test Data

```bash
./semantic_load.py test_load.json
```

**Expected Output:**
```
Device: cpu (or cuda)
Threads: 20
Processed 3...
0 records left...
```

**Validation:**
- [ ] No errors during loading
- [ ] All records loaded successfully
- [ ] Embeddings generated

### Verify Data in Database

```bash
# Check vector table has data
# PostgreSQL
psql <your_db> -c "SELECT COUNT(*) FROM NAME_SEM_KEY;"
psql <your_db> -c "SELECT LIB_FEAT_ID, LABEL, array_length(EMBEDDING::float[], 1) as dim FROM NAME_SEM_KEY LIMIT 3;"

# SQLite
sqlite3 <your_db> "SELECT COUNT(*) FROM NAME_SEM_KEY;"
sqlite3 <your_db> "SELECT LIB_FEAT_ID, LABEL FROM NAME_SEM_KEY LIMIT 3;"
```

**Expected:**
- [ ] 3 records in NAME_SEM_KEY table
- [ ] EMBEDDING dimension is 384 (or your configured dimension)
- [ ] LABEL values match name fields

### Verify Records in Sz

```bash
python3 << 'EOF'
import senzing_core
import os
import json

engine_config = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
factory = senzing_core.SzAbstractFactoryCore("test", engine_config)
engine = factory.create_engine()

# Get entity
result = engine.get_entity_by_record_id("TEST", "001")
entity = json.loads(result)
print(json.dumps(entity, indent=2))
EOF
```

**Expected:**
- [ ] Record retrieved successfully
- [ ] Entity formed (if similar names matched)

## Phase 5: Search Testing

### Create Search Queries

```bash
cat > test_search.json << 'EOF'
{"RECORD_ID": "search_001", "NAME_FULL": "John Smith"}
{"RECORD_ID": "search_002", "NAME_FULL": "Jonathan Smithe"}
EOF
```

### Run Searches

```bash
./semantic_search.py test_search.json
```

**Expected Output:**
```
Device: cuda (or cpu)
Searching with <N> threads
...
Processed 2 searches, <M> entities returned:
  avg[X.XXXs] tps[X.X/s] min[X.XXXs] max[X.XXXs]
```

**Validation:**
- [ ] No errors during search
- [ ] Entities returned for similar names
- [ ] Performance metrics displayed

### Verify Semantic Matching

```bash
python3 << 'EOF'
import senzing_core
import os
import json
from senzing import SzEngineFlags

engine_config = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
factory = senzing_core.SzAbstractFactoryCore("test", engine_config)
engine = factory.create_engine()

# Search with embeddings
query = {
    "NAME_FULL": "Jonathan Smithe"
}

result = engine.search_by_attributes(
    json.dumps(query),
    SzEngineFlags.SZ_SEARCH_BY_ATTRIBUTES_MINIMAL_ALL
)

search_result = json.loads(result)
print(f"Found {len(search_result.get('RESOLVED_ENTITIES', []))} entities")
for entity in search_result.get('RESOLVED_ENTITIES', []):
    print(f"  Entity ID: {entity['ENTITY_ID']}, Match Score: {entity.get('MATCH_SCORE', 'N/A')}")
EOF
```

**Expected:**
- [ ] Finds "John Smith" entity when searching for "Jonathan Smithe"
- [ ] Match score indicates similarity

## Phase 6: Validation with WHY

### Check WHY Output

```bash
python3 << 'EOF'
import senzing_core
import os
import json

engine_config = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
factory = senzing_core.SzAbstractFactoryCore("test", engine_config)
engine = factory.create_engine()

# Get WHY for two similar records
why = engine.why_records("TEST", "001", "TEST", "002")
why_data = json.loads(why)

# Check for NAME_SEM_KEY in candidate keys
print(json.dumps(why_data, indent=2))
EOF
```

**Expected in WHY output:**
- [ ] NAME_SEM_KEY appears in WHY_RESULT
- [ ] Shows as candidate builder (not in scoring)
- [ ] Indicates how records were found

## Phase 7: Performance Testing

### Load Larger Dataset

```bash
# Create larger test file (1000 records)
python3 << 'EOF'
import json
import random

names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez"]
first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Eve", "Frank", "Grace", "Henry"]

with open("test_large.json", "w") as f:
    for i in range(1000):
        record = {
            "DATA_SOURCE": "TEST",
            "RECORD_ID": f"L{i:04d}",
            "NAME_FULL": f"{random.choice(first_names)} {random.choice(names)}",
            "PHONE_NUMBER": f"555-{random.randint(1000,9999)}"
        }
        f.write(json.dumps(record) + "\n")
EOF

./semantic_load.py test_large.json
```

**Validation:**
- [ ] Loads complete without errors
- [ ] Reasonable performance (check records/sec)
- [ ] Vector table populated

### Search Performance

```bash
# Create search queries
python3 << 'EOF'
import json
import random

names = ["Smith", "Johnson", "Williams"]
first_names = ["John", "Jane", "Bob"]

with open("test_search_large.json", "w") as f:
    for i in range(100):
        record = {
            "RECORD_ID": f"S{i:04d}",
            "NAME_FULL": f"{random.choice(first_names)} {random.choice(names)}"
        }
        f.write(json.dumps(record) + "\n")
EOF

./semantic_search.py test_search_large.json
```

**Expected:**
- [ ] All searches complete
- [ ] Reasonable performance (check tps)
- [ ] P90/P95/P99 metrics reasonable

## Phase 8: Edge Cases

### Test Records Without Names

```bash
cat > test_noname.json << 'EOF'
{"DATA_SOURCE": "TEST", "RECORD_ID": "NO_NAME_001", "PHONE_NUMBER": "555-9999"}
EOF

./semantic_load.py test_noname.json
```

**Expected:**
- [ ] Loads without error
- [ ] No embedding created (no name field)
- [ ] No entry in NAME_SEM_KEY table for this record

### Test Multiple Name Formats

```bash
./semantic_load.py test_name_formats.json
```

**Expected:**
- [ ] All name formats handled
- [ ] Structured names (NAME_FIRST/LAST) constructed properly
- [ ] NAME_ORG handled

## Troubleshooting

### Issue: "Module not found" errors

**Solution:** Install missing packages
```bash
pip install senzing senzing-core psycopg2-binary pgvector orjson fast-sentence-transformers
```

### Issue: "Embedding candidate license disallows"

**Solution:** Requires Advanced Search license. Contact Senzing.

### Issue: Tables not created

**Solution:**
- Check database connection
- Verify pgvector/szvec extension available
- Check permissions

### Issue: No semantic matches

**Solution:**
- Verify NAME_SEM_KEY feature created: `sz_configtool` → `getFeature NAME_SEM_KEY`
- Check vector table has data: `SELECT COUNT(*) FROM NAME_SEM_KEY`
- Verify embeddings in records: Check LIB_FEAT table

### Issue: Slow performance

**Solution:**
- Check HNSW index created
- Increase thread count: `export SENZING_THREADS_PER_PROCESS=40`
- Use GPU for embedding generation (device="cuda")

## Success Criteria

- [x] Environment configured correctly
- [x] Vector tables created with HNSW indexes
- [x] NAME_SEM_KEY feature type created
- [x] Three attributes created and linked
- [x] Test data loads successfully
- [x] Embeddings stored in vector tables
- [x] Searches return semantically similar results
- [x] WHY shows NAME_SEM_KEY as candidate builder
- [x] Performance is acceptable
- [x] All edge cases handled

## Cleanup (Optional)

```bash
# Remove test data
python3 << 'EOF'
import senzing_core
import os

engine_config = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
factory = senzing_core.SzAbstractFactoryCore("test", engine_config)
engine = factory.create_engine()

# Delete test records
for i in range(1000):
    try:
        engine.delete_record("TEST", f"L{i:04d}")
    except:
        pass
EOF

# Remove test files
rm -f test_load.json test_search.json test_large.json test_search_large.json test_noname.json
```

## Next Steps After Successful Testing

1. Load production data with `semantic_load.py`
2. Monitor performance and adjust HNSW parameters if needed
3. Tune vector similarity threshold if too many/few candidates
4. Consider enabling SEMANTIC_VALUE for scoring (separate feature)
