# Sz Semantic Search - Usage Guide

This project demonstrates using Senzing (Sz) with native semantic embedding support for entity resolution.

## Overview

Instead of building forced candidate lists externally, this implementation uses Sz's built-in SEMANTIC_VALUE feature type to:
- Store embeddings directly in Sz records
- Use pgvector for fast similarity search
- Generate candidates automatically based on semantic similarity
- Score matches using cosine similarity

## Prerequisites

1. **Senzing SDK** with Advanced Search license
   - senzingsdk-runtime (core Senzing libraries)
   - senzingsdk-tools (sz_configtool and utilities)

2. **Database** (choose one):
   - **PostgreSQL** with pgvector extension, OR
   - **SQLite** with szvec extension (included in senzingsdk-runtime)

3. **Python 3.10+** with dependencies:
   ```bash
   pip install senzing senzing-core psycopg2-binary pgvector orjson \
               fast-sentence-transformers uritools
   ```

## Setup

### 1. Configure Senzing Environment

```bash
# For PostgreSQL
export SENZING_ENGINE_CONFIGURATION_JSON='{
  "PIPELINE": {
    "CONFIGPATH": "/etc/opt/senzing",
    "LICENSESTRINGBASE64": "YOUR_LICENSE_KEY",
    "RESOURCEPATH": "/opt/senzing/er/resources",
    "SUPPORTPATH": "/opt/senzing/er/data"
  },
  "SQL": {
    "CONNECTION": "postgresql://user:pass@localhost:5432/senzing"
  }
}'

# For SQLite
export SENZING_ENGINE_CONFIGURATION_JSON='{
  "PIPELINE": {
    "CONFIGPATH": "/etc/opt/senzing",
    "LICENSESTRINGBASE64": "YOUR_LICENSE_KEY",
    "RESOURCEPATH": "/opt/senzing/er/resources",
    "SUPPORTPATH": "/opt/senzing/er/data"
  },
  "SQL": {
    "CONNECTION": "sqlite3://na:na@/var/opt/senzing/sqlite/G2C.db"
  }
}'
```

**Note:** These paths are for Senzing SDK v4. Adjust based on your installation location.

### 2. Setup Vector Tables

#### For PostgreSQL with pgvector:

```bash
./setup_vector_tables.py
```

For custom vector dimensions:

```bash
./setup_vector_tables.py --dimension 768  # For BERT-base
```

#### For SQLite with szvec:

```bash
# szvec extension is included in senzingsdk-runtime
./setup_vector_tables.py --sqlite

# If szvec is not in default location, specify path
./setup_vector_tables.py --sqlite --szvec-path /opt/senzing/er/lib/szvec.so
```

### 3. Configure Sz for SEMANTIC_VALUE Candidates

**Important**: You must modify your Sz configuration to enable SEMANTIC_VALUE for candidate generation.

Run the configuration script:

```bash
# Preview the changes first
./enable_semantic_candidates.py --dry-run

# Apply the configuration
./enable_semantic_candidates.py
```

This will change `USED_FOR_CAND` from 'No' to 'Yes' for the SEMANTIC_VALUE feature type.

See [CONFIGURATION.md](CONFIGURATION.md) for:
- Detailed explanation of the configuration changes
- Manual configuration methods
- License requirements
- Troubleshooting

## Loading Data

### Input Data Format

Your JSON records should contain name fields. The loader will automatically generate embeddings from any supported name format:

```json
{
  "DATA_SOURCE": "CUSTOMERS",
  "RECORD_ID": "1001",
  "NAME_FULL": "John Smith",
  "PHONE_NUMBER": "+15551234567"
}
```

**Supported name formats:**
- `NAME_FULL` - Full name as single string
- `NAME_FIRST`, `NAME_MIDDLE`, `NAME_LAST` - Structured name parts
- `NAME_ORG` - Organization/business name

See [NAME_FORMATS.md](NAME_FORMATS.md) for detailed information on all supported formats.

### Load Records with Embeddings

```bash
# Load the included sample data (1000 records)
./semantic_load.py test_icij_sample.json

# Or load your own data
./semantic_load.py your_data.json
```

The loader will:
1. Read each record
2. Extract name fields (NAME_FULL, NAME_ORG, etc.)
3. Generate embeddings using all-MiniLM-L6-v2 (384 dimensions)
4. Add SEMANTIC_EMBEDDING and SEMANTIC_LABEL to the record
5. Load the record into Sz with `add_record()`

Sz will then:
- Parse the SEMANTIC_EMBEDDING field
- Store the embedding in the SEMANTIC_VALUE pgvector table
- Build HNSW index entries for fast similarity search

### Options

```bash
./semantic_load.py test_icij_sample.json -x  # Skip engine prime (faster startup)
./semantic_load.py your_data.json -t  # Enable debug tracing
```

## Searching Data

### Input Search Format

Search queries use the same format as your data:

```json
{
  "RECORD_ID": "search_1",
  "NAME_FULL": "Jon Smyth"
}
```

### Run Searches

```bash
./semantic_search.py search_queries.json
```

The search will:
1. Read each search query
2. Generate embeddings from the name fields
3. Add SEMANTIC_EMBEDDING and SEMANTIC_LABEL to the query
4. Call `search_by_attributes()` with the enriched query

Sz will then:
- Use SEMANTIC_VALUE to generate candidates via vector similarity
- Score all candidates (including semantic similarity score)
- Return ranked results

### Output

The search displays:
- Records processed per second
- Average/min/max search times
- P90/P95/P99 percentiles
- Number of entities returned

Example output:
```
Device: cuda
Searching with 20 threads
Processed 1000 searches, 250 entities returned:
  avg[0.045s] tps[22.2/s] min[0.012s] max[0.234s]
Percent under 1s: 99.8%
p99: 0.156s
p95: 0.089s
p90: 0.067s
```

## How It Works

### Old Approach (forced_candidate branch)

```
1. Load data → separate pgvector table
2. Search query → pgvector lookup → get similar records
3. Build _FORCED_CANDIDATES list
4. Sz searches only forced candidates
```

### New Approach (main branch)

```
1. Load data → Sz records with SEMANTIC_EMBEDDING field
   ↓
   Sz stores embeddings in SEMANTIC_VALUE pgvector table

2. Search query → Sz record with SEMANTIC_EMBEDDING field
   ↓
   Sz uses SEMANTIC_VALUE to:
   - Generate candidates via vector similarity
   - Score all candidates (including semantic score)
   - Return ranked results
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Your Application                          │
│  ┌────────────────────┐              ┌────────────────────┐     │
│  │ semantic_load.py   │              │ semantic_search.py │     │
│  │                    │              │                    │     │
│  │ 1. Read JSON       │              │ 1. Read query JSON │     │
│  │ 2. Generate        │              │ 2. Generate        │     │
│  │    embeddings      │              │    embeddings      │     │
│  │ 3. Add to record   │              │ 3. Add to query    │     │
│  │ 4. add_record()    │              │ 4. search_by_      │     │
│  │                    │              │    attributes()    │     │
│  └──────┬─────────────┘              └──────┬─────────────┘     │
└─────────┼───────────────────────────────────┼───────────────────┘
          │                                   │
          ▼                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Senzing (Sz) Engine                           │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Feature Extraction & Storage                             │   │
│  │  • Parses SEMANTIC_EMBEDDING JSON array                  │   │
│  │  • Stores in SEMANTIC_VALUE feature type                 │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                            │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │ Candidate Generation (if USED_FOR_CAND='Yes')           │   │
│  │  • Vector similarity search in SEMANTIC_VALUE table      │   │
│  │  • HNSW index for fast approximate nearest neighbors     │   │
│  │  • Generates candidates from similar embeddings          │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                            │                                     │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │ Scoring & Resolution                                     │   │
│  │  • Scores all candidates (name, phone, etc.)            │   │
│  │  • Includes SEMANTIC_SIMILARITY_COMP for embedding score│   │
│  │  • Cosine similarity → 0-100 score                      │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬───────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                  PostgreSQL with pgvector                        │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ SEMANTIC_VALUE table                                     │   │
│  │  • LIB_FEAT_ID (primary key)                            │   │
│  │  • LABEL (text)                                         │   │
│  │  • EMBEDDING (vector[384])                              │   │
│  │  • HNSW index on EMBEDDING (vector_cosine_ops)          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Standard Sz tables (RES_ENT, OBS_ENT, LIB_FEAT, etc.)   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Embedding Model

This project uses **all-MiniLM-L6-v2**:
- **Dimensions**: 384
- **Max sequence length**: 256 tokens
- **Performance**: Very fast inference (~3000 sentences/sec on GPU)
- **Quality**: Good for semantic similarity tasks

To change the model, edit both `semantic_load.py` and `semantic_search.py`:

```python
model = SentenceTransformer(
    "sentence-transformers/all-mpnet-base-v2",  # 768 dimensions
    device="cuda"
)
```

**Remember**: Update vector table dimension to match!

```bash
./setup_vector_tables.py --dimension 768
```

## Performance Tuning

### HNSW Index Parameters

For larger datasets, tune HNSW parameters in `setup_vector_tables.py`:

```sql
-- Higher M = better recall, more memory
-- Higher ef_construction = better quality, slower build
CREATE INDEX ... USING hnsw (EMBEDDING vector_cosine_ops)
WITH (m = 16, ef_construction = 200);
```

### Thread Count

Control parallelism via environment variable:

```bash
export SENZING_THREADS_PER_PROCESS=40  # More threads
./semantic_search.py queries.json
```

### GPU Acceleration

Both scripts support CUDA:

```python
# In semantic_search.py
model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2",
    device="cuda",  # Use GPU
)
```

## Troubleshooting

### Issue: "Embedding candidate license disallows"

**Solution**: Requires Senzing Advanced Search license. Contact Senzing.

### Issue: "relation 'semantic_value' does not exist"

**Solution**: Run `./setup_vector_tables.py` to create the vector tables.

### Issue: No semantic matches found

**Possible causes**:
1. USED_FOR_CAND='No' in config → Change to 'Yes' (see CONFIGURATION.md)
2. Vector dimension mismatch → Verify table dimension matches model (384)
3. Embeddings not generated → Check that records have name fields

### Issue: Slow search performance

**Solutions**:
1. Ensure HNSW index exists: `\d SEMANTIC_VALUE` in psql
2. Increase thread count: `export SENZING_THREADS_PER_PROCESS=40`
3. Use GPU: Change `device="cuda"` in search script
4. Tune HNSW parameters for your dataset size

## Comparison with Forced Candidates

| Aspect | Forced Candidates (old) | Native Sz Support (new) |
|--------|-------------------------|-------------------------|
| Configuration | External pgvector table | Sz SEMANTIC_VALUE table |
| Candidate building | Python code | Sz internal |
| Maintenance | Sync two systems | Single system |
| Licensing | Basic Sz | Advanced Search required |
| Performance | Depends on external query | Optimized internally |
| Consistency | Manual sync needed | Automatic |

## Quick Start

Follow these steps to get started:

```bash
# 1. Setup vector tables in PostgreSQL
./setup_vector_tables.py

# 2. Create NAME_SEM_KEY feature for candidate generation
./enable_semantic_candidates.py

# 3. Load your data with embeddings
./semantic_load.py your_data.json

# 4. Run semantic searches
./semantic_search.py your_queries.json
```

## Next Steps

1. **Run setup**: `./setup_vector_tables.py`
2. **Configure Sz**: `./enable_semantic_candidates.py` (see [CONFIGURATION.md](CONFIGURATION.md) for details)
3. **Load test data**: `./semantic_load.py test_data.json`
4. **Run searches**: `./semantic_search.py test_queries.json`
5. **Check WHY output**: Verify SEMANTIC_VALUE in candidate keys

## References

- [NAME_FORMATS.md](NAME_FORMATS.md) - Supported name formats and handling
- [CONFIGURATION.md](CONFIGURATION.md) - Detailed configuration changes
- [CHANGES.md](CHANGES.md) - Summary of all changes and migration guide
- [Senzing SDK Documentation](https://docs.senzing.com/)
- [pgvector documentation](https://github.com/pgvector/pgvector)
- [Sentence Transformers](https://www.sbert.net/)
