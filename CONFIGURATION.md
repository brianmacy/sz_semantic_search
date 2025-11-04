# Sz NAME_SEM_KEY Configuration Guide

This guide explains how to create the NAME_SEM_KEY feature type for semantic candidate generation in Senzing (Sz).

## Overview

Instead of modifying SEMANTIC_VALUE, this approach creates a **separate feature type** called NAME_SEM_KEY:
- **NAME_SEM_KEY**: Used for candidate generation only (no scoring)
- **SEMANTIC_VALUE**: Remains available for scoring if needed later

This separation keeps candidate generation and scoring independent.

## Configuration Changes Required

### 1. Create NAME_SEM_KEY Feature Type

The script creates a new feature type by copying SEMANTIC_VALUE:

```
FTYPE_CODE: 'NAME_SEM_KEY'
FTYPE_DESC: 'Name semantic key for candidate generation'
USED_FOR_CAND: 'Yes'         ← Enable for candidate building
COMPARISON_FUNC: (none)      ← No comparison function = no scoring
SHOW_IN_MATCH_KEY: 'No'      ← Don't show in match keys
```

**Key differences from SEMANTIC_VALUE:**
- `USED_FOR_CAND='Yes'` - Generates candidates via vector similarity
- No comparison function (removed SEMANTIC_SIMILARITY_COMP) - THIS disables scoring
- `SHOW_IN_MATCH_KEY='No'` - Doesn't appear in match keys (cosmetic)

### 2. Configuration File Location

The configuration is typically found in:
- JSON config: Look for the `G2_CONFIG` or feature type configuration section
- Config tool: Use `G2ConfigTool.py` to export, modify, and import the configuration
- Direct database: The `SYS_CFG_FTYPE` table if modifying directly

### 3. Using the Configuration Script (Recommended)

The easiest way to create NAME_SEM_KEY is to use the included Python script:

```bash
# Preview changes without applying
./enable_semantic_candidates.py --dry-run

# Create NAME_SEM_KEY feature type
./enable_semantic_candidates.py
```

The script will:
1. Export the current default configuration
2. Find SEMANTIC_VALUE and copy its structure
3. Create NAME_SEM_KEY with:
   - New feature type (NAME_SEM_KEY)
   - New attributes (NAME_SEM_KEY_EMBEDDING, NAME_SEM_KEY_LABEL, NAME_SEM_KEY_ALGORITHM)
   - USED_FOR_CAND='Yes', SHOW_IN_MATCH_KEY='No'
4. Add the new configuration and set it as default

**Output example:**
```
✓ Found SEMANTIC_VALUE feature type (FTYPE_ID: 99)
✓ Created NAME_SEM_KEY feature type (FTYPE_ID: 100)
  USED_FOR_CAND: Yes (candidates enabled)
  SHOW_IN_MATCH_KEY: No (scoring disabled)
✓ Found 3 SEMANTIC_VALUE attributes to copy
  ✓ Created attribute: NAME_SEM_KEY_EMBEDDING (ATTR_ID: 2818)
  ✓ Created attribute: NAME_SEM_KEY_LABEL (ATTR_ID: 2819)
  ✓ Created attribute: NAME_SEM_KEY_ALGORITHM (ATTR_ID: 2820)
```

### 3b. Using sz_configtool (Alternative)

You can also manually create the feature type using sz_configtool, but this requires multiple steps and is more error-prone. The Python script is recommended.

### 4. Manual Configuration with Sz SDK

If you prefer to modify the configuration manually:

```python
import senzing_core
import orjson as json

factory = senzing_core.SzAbstractFactoryCore("config", engine_config)
config_manager = factory.create_config_manager()

# Get current config
config_id = config_manager.get_default_config_id()
config_json = config_manager.get_config(config_id)
config = json.loads(config_json)

# Modify SEMANTIC_VALUE
for ftype in config["G2_CONFIG"]["CFG_FTYPE"]:
    if ftype["FTYPE_CODE"] == "SEMANTIC_VALUE":
        ftype["USED_FOR_CAND"] = "Yes"
        break

# Save new config
new_config_json = json.dumps(config).decode('utf-8')
new_config_id = config_manager.add_config(new_config_json, "Enable SEMANTIC_VALUE candidates")
config_manager.set_default_config_id(new_config_id)
```

## Database Setup

### PostgreSQL with pgvector

Run the setup script to create required vector tables:

```bash
./setup_vector_tables.py
```

Or manually:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA pg_catalog;

-- Create SEMANTIC_VALUE table (384 dimensions for all-MiniLM-L6-v2)
CREATE TABLE IF NOT EXISTS SEMANTIC_VALUE (
    LIB_FEAT_ID BIGINT NOT NULL,
    LABEL VARCHAR(250) NOT NULL,
    EMBEDDING VECTOR(384),
    PRIMARY KEY(LIB_FEAT_ID)
);

-- Create HNSW index for fast similarity search
CREATE INDEX IF NOT EXISTS semantic_value_embedding_idx
ON SEMANTIC_VALUE USING hnsw (EMBEDDING vector_cosine_ops);
```

### Vector Dimensions

The vector dimension must match your embedding model:

| Model | Dimension |
|-------|-----------|
| all-MiniLM-L6-v2 (this project) | 384 |
| BERT-base | 768 |
| OpenAI text-embedding-ada-002 | 1536 |
| OpenAI text-embedding-3-small | 1536 |
| OpenAI text-embedding-3-large | 3072 |

To use a different dimension:

```bash
./setup_vector_tables.py --dimension 768
```

## License Requirements

**IMPORTANT**: Using SEMANTIC_VALUE for candidate generation requires the **Senzing Advanced Search license**.

Without this license, Sz will reject the configuration change with an error.

## Verification

After making these changes:

1. **Restart Sz** to load the new configuration
2. **Load test data** with embeddings using `semantic_load.py`
3. **Search test data** using `semantic_search.py`
4. **Check WHY output** to verify SEMANTIC_VALUE appears in candidate key information

Example WHY output showing SEMANTIC_VALUE in candidates:

```json
{
  "MATCH_INFO": {
    "CANDIDATE_KEYS": {
      "+SEMANTIC_VALUE": ["SEMANTIC_VALUE matching used for candidates"]
    },
    "FEATURE_SCORES": {
      "SEMANTIC_VALUE": [{
        "SCORE": 99,
        "SCORE_BUCKET": "SAME"
      }]
    }
  }
}
```

## Configuration Summary

| Configuration | Scoring Only | Candidate + Scoring |
|---------------|--------------|---------------------|
| USED_FOR_CAND | 'No' | 'Yes' |
| License Required | Basic | Advanced Search |
| Behavior | Only scores existing candidates | Generates new candidates via vector search |
| Performance | Faster (fewer candidates) | Slower (more candidates) |

## Configuration Details

The default SEMANTIC_VALUE configuration has:

```
FTYPE_CODE: 'SEMANTIC_VALUE'
USED_FOR_CAND: 'No'  ← Default: scoring only
```

NAME_SEM_KEY is created as a separate feature with:

```
FTYPE_CODE: 'NAME_SEM_KEY'
USED_FOR_CAND: 'Yes'  ← Candidate generation enabled
COMPARISON_FUNC: (none)  ← No scoring
```

## Related Configuration

Other SEMANTIC_VALUE configuration that's already correct:

- **CFG_ATTR.data**: Defines SEMANTIC_EMBEDDING, SEMANTIC_LABEL, SEMANTIC_ALGORITHM attributes
- **CFG_FELEM.data**: Defines EMBEDDING element with DATA_TYPE='EMBEDDING'
- **CFG_CFUNC.data**: Defines SEMANTIC_SIMILARITY_COMP comparison function
- **CFG_CFCALL.data**: Links SEMANTIC_VALUE to SEMANTIC_SIMILARITY_COMP

These don't need to be changed - they're already correctly configured in the G2 codebase.

## Troubleshooting

### Error: "Embedding candidate license disallows"

**Cause**: Advanced Search license not present

**Solution**: Contact Senzing to obtain Advanced Search license

### Error: "relation 'semantic_value' does not exist"

**Cause**: Vector tables not created

**Solution**: Run `./setup_vector_tables.py`

### No candidates generated from SEMANTIC_VALUE

**Cause**: USED_FOR_CAND still set to 'No'

**Solution**: Verify configuration change was applied and Sz was restarted

### Performance issues

**Cause**: HNSW index not created or vector dimension mismatch

**Solution**:
- Verify index exists: `\d SEMANTIC_VALUE` in psql
- Check embedding dimension matches table definition
- Consider tuning HNSW parameters for larger datasets
