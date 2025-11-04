# Changes Summary - Native Sz Semantic Support

## Overview

The code has been converted from using external forced candidate lists to using Sz's native SEMANTIC_VALUE feature type for semantic similarity matching.

## Branch Structure

- **`main`**: New implementation using Sz native embedding support
- **`forced_candidate`**: Previous implementation using external pgvector queries

## Modified Files

### `semantic_load.py`
**Changes:**
- Removed pgvector connection and table insertion code
- Added `add_embeddings_to_record()` function
- Embeddings are now added directly to records as `SEMANTIC_EMBEDDING` and `SEMANTIC_LABEL` fields
- Records loaded via standard `add_record()` API
- Sz handles embedding storage internally

**Key difference:**
```python
# OLD: Insert into separate pgvector table
cursor.execute("INSERT INTO NAME_SEARCH_EMB ...")

# NEW: Add fields to record, Sz handles storage
record["SEMANTIC_EMBEDDING"] = json.dumps(embedding.tolist()).decode('utf-8')
record["SEMANTIC_LABEL"] = name_val
engine.add_record(data_source, record_id, json.dumps(record))
```

### `semantic_search.py`
**Changes:**
- Removed pgvector query code
- Removed `_FORCED_CANDIDATES` building logic
- Added `add_embeddings_to_record()` function
- Search queries enriched with embeddings
- Sz handles candidate generation internally

**Key difference:**
```python
# OLD: Query pgvector, build forced candidates
forced_records = process_record_for_embed(cursor, record)
record["_FORCED_CANDIDATES"] = {"RECORDS": forced_records}

# NEW: Add embeddings to query, let Sz handle it
record = add_embeddings_to_record(record)
response = engine.search_by_attributes(json.dumps(record), flags)
```

## New Files

### `setup_vector_tables.py`
**Purpose:** Creates pgvector tables for Sz's internal use

**What it does:**
- Enables pgvector extension in PostgreSQL
- Creates `SEMANTIC_VALUE` table with vector column
- Creates HNSW indexes for fast similarity search
- Also creates `NAME_EMBEDDING` and `BIZNAME_EMBEDDING` tables

**Usage:**
```bash
./setup_vector_tables.py              # Default 384 dimensions
./setup_vector_tables.py -d 768       # Custom dimensions
```

### `enable_semantic_candidates.py`
**Purpose:** Modifies Sz configuration to enable SEMANTIC_VALUE for candidate generation

**What it does:**
- Exports current Sz configuration
- Finds SEMANTIC_VALUE feature type
- Changes `USED_FOR_CAND` from 'No' to 'Yes'
- Imports updated configuration as new default

**Usage:**
```bash
./enable_semantic_candidates.py --dry-run   # Preview changes
./enable_semantic_candidates.py             # Apply changes
```

### `CONFIGURATION.md`
**Purpose:** Comprehensive guide on configuring Sz for SEMANTIC_VALUE candidates

**Contents:**
- Explanation of USED_FOR_CAND setting
- How to use the configuration script
- Manual configuration methods
- Database setup requirements
- Vector dimension specifications
- License requirements (Advanced Search)
- Troubleshooting

### `USAGE.md`
**Purpose:** Complete usage guide for the semantic search system

**Contents:**
- Prerequisites and setup
- Quick start guide
- Loading data workflow
- Searching data workflow
- Architecture diagrams
- Comparison: old vs new approach
- Performance tuning tips
- Troubleshooting

### `CHANGES.md` (this file)
**Purpose:** Summary of all changes made during the conversion

## Key Architecture Changes

### Before (forced_candidate branch)

```
Python App → pgvector → Find similar records → Build _FORCED_CANDIDATES
    ↓
Sz searches only forced candidates
```

**Characteristics:**
- External vector table management
- Python code builds candidate list
- Two systems to maintain (Sz + pgvector)
- Manual synchronization needed

### After (main branch)

```
Python App → Add SEMANTIC_EMBEDDING to record → Sz API
    ↓
Sz stores embeddings → pgvector tables (internal)
    ↓
Sz generates candidates → Scores with semantic similarity
```

**Characteristics:**
- Sz manages vector tables internally
- Candidate generation fully automatic
- Single integrated system
- No manual synchronization needed

## Configuration Requirements

### Database
- PostgreSQL with pgvector extension
- Vector tables created by `setup_vector_tables.py`
- HNSW indexes for performance

### Sz Configuration
- `USED_FOR_CAND='Yes'` for SEMANTIC_VALUE feature type
- Applied via `enable_semantic_candidates.py`
- Requires Advanced Search license

### Feature Types
Already configured in Sz:
- `SEMANTIC_VALUE` (FTYPE_ID 99)
- `SEMANTIC_EMBEDDING` attribute
- `SEMANTIC_LABEL` attribute
- `SEMANTIC_SIMILARITY_COMP` comparison function

## Migration Steps

If migrating from the old approach:

1. **Backup your data** (optional)
   ```bash
   git checkout forced_candidate  # Save old branch
   ```

2. **Switch to new code**
   ```bash
   git checkout main
   ```

3. **Setup vector tables**
   ```bash
   ./setup_vector_tables.py
   ```

4. **Enable SEMANTIC_VALUE candidates**
   ```bash
   ./enable_semantic_candidates.py
   ```

5. **Reload your data**
   - Data must be reloaded with the new `semantic_load.py`
   - Old data doesn't have SEMANTIC_EMBEDDING fields
   ```bash
   # Test with included sample first
   ./semantic_load.py test_icij_sample.json

   # Then reload your own data
   ./semantic_load.py your_data.json
   ```

6. **Test searches**
   ```bash
   ./semantic_search.py your_queries.json
   ```

## Testing

### Verify Configuration
```bash
# Check that config was updated
./enable_semantic_candidates.py --dry-run
```

### Verify Vector Tables
```sql
-- In psql
\d SEMANTIC_VALUE
-- Should show: EMBEDDING vector(384) column

SELECT * FROM pg_indexes WHERE tablename = 'semantic_value';
-- Should show: HNSW index on EMBEDDING
```

### Verify Data Loading
```bash
# Load a small test file
./semantic_load.py test.json

# Check that embeddings were stored (requires Sz diagnostic API)
```

### Verify Searching
```bash
# Run searches
./semantic_search.py queries.json

# Check WHY output for SEMANTIC_VALUE in candidate keys
```

## Benefits of New Approach

✅ **Simpler architecture** - One system instead of two
✅ **Better integration** - Embeddings are first-class Sz features
✅ **Automatic candidate generation** - No manual forced candidate building
✅ **Consistent storage** - Embeddings stored with other feature data
✅ **Native scoring** - Semantic similarity integrated into Sz scoring
✅ **Single source of truth** - All data in Sz
✅ **Better maintainability** - Less code, fewer moving parts

## Requirements

### Software
- Senzing SDK (with Advanced Search license)
- PostgreSQL with pgvector extension
- Python 3.10+
- Required packages: senzing, senzing-core, psycopg2-binary, pgvector, orjson, fast-sentence-transformers

### Hardware
- GPU recommended (CUDA) for embedding generation
- Sufficient RAM for HNSW index (depends on dataset size)

### Licensing
- **Basic Sz license**: Scoring only (USED_FOR_CAND='No')
- **Advanced Search license**: Candidate generation (USED_FOR_CAND='Yes') ← Required for this implementation

## Rollback

If you need to rollback to the old approach:

```bash
# Switch to old branch
git checkout forced_candidate

# Old scripts work with existing pgvector tables
# No Sz configuration changes needed for old approach
```

## Questions?

See the documentation:
- [USAGE.md](USAGE.md) - How to use the system
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration details
- [README.md](README.md) - Project overview (if exists)

## Credits

Conversion based on Sz's native embedding support as implemented in:
- `~/dev/G2/th4/tests/functional/feature/embeddingFeatures.cpp`
- Sz SEMANTIC_VALUE feature type (FTYPE_ID 99)
- PostgreSQL pgvector extension
