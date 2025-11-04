# Name Format Support

Both `semantic_load.py` and `semantic_search.py` automatically detect and handle all supported Senzing name formats when generating embeddings.

## Supported Name Formats

### 1. Full Name (`NAME_FULL`)

The complete name as a single string.

```json
{
  "DATA_SOURCE": "CUSTOMERS",
  "RECORD_ID": "001",
  "NAME_FULL": "John Smith"
}
```

**Generated embedding from:** `"John Smith"`

### 2. Structured Name (NAME_FIRST, NAME_MIDDLE, NAME_LAST)

Name broken into component parts.

```json
{
  "DATA_SOURCE": "CUSTOMERS",
  "RECORD_ID": "002",
  "NAME_FIRST": "Jane",
  "NAME_LAST": "Doe"
}
```

**Generated embedding from:** `"Jane Doe"` (constructed)

With middle name:

```json
{
  "DATA_SOURCE": "CUSTOMERS",
  "RECORD_ID": "003",
  "NAME_FIRST": "Robert",
  "NAME_MIDDLE": "James",
  "NAME_LAST": "Johnson"
}
```

**Generated embedding from:** `"Robert James Johnson"` (constructed)

### 3. Organization Name (`NAME_ORG`)

Organization or business name.

```json
{
  "DATA_SOURCE": "VENDORS",
  "RECORD_ID": "004",
  "NAME_ORG": "Acme Corporation"
}
```

**Generated embedding from:** `"Acme Corporation"`

## Name Detection Logic

The scripts use the following logic to detect and construct names:

1. **Check for structured names**: If `NAME_FIRST`, `NAME_MIDDLE`, or `NAME_LAST` are present, construct a full name
   - Concatenates parts with spaces: `"<FIRST> <MIDDLE> <LAST>"`
   - Skips empty/missing parts

2. **Check for full name fields**: Look for any field ending in:
   - `NAME_FULL`
   - `NAME_ORG`

3. **Recursive search**: Checks nested dictionaries for name fields

4. **First match wins**: Uses the first name found (full names take priority over constructed)

## Priority Order

When multiple name formats are present in a record:

1. **NAME_FULL** or **NAME_ORG** (if found first)
2. **Constructed name** from NAME_FIRST/MIDDLE/LAST
3. Any nested name fields

Example with multiple formats:

```json
{
  "DATA_SOURCE": "TEST",
  "RECORD_ID": "005",
  "NAME_FULL": "John Smith",
  "NAME_FIRST": "Jonathan",
  "NAME_LAST": "Smythe"
}
```

**Will use:** `"John Smith"` (NAME_FULL found first)

## Nested Name Structures

The scripts handle nested name structures:

```json
{
  "DATA_SOURCE": "TEST",
  "RECORD_ID": "006",
  "PRIMARY_NAME": {
    "NAME_FIRST": "Jane",
    "NAME_LAST": "Doe"
  }
}
```

**Generated embedding from:** `"Jane Doe"`

## Empty or Missing Names

If no name fields are found:
- No embedding is generated
- Record is loaded/searched without SEMANTIC_EMBEDDING
- Sz will not use semantic similarity for that record

```json
{
  "DATA_SOURCE": "TEST",
  "RECORD_ID": "007",
  "PHONE_NUMBER": "555-1234"
}
```

**Result:** Loaded without embedding (standard Sz matching only)

## Test Data

A test file with various name formats is provided:

```bash
cat test_name_formats.json
```

Contains examples of:
- NAME_FULL
- NAME_FIRST + NAME_LAST
- NAME_FIRST + NAME_MIDDLE + NAME_LAST
- NAME_ORG

## Implementation Details

### Name Construction Function

```python
def construct_name_from_parts(obj):
    """Construct full name from NAME_FIRST, NAME_MIDDLE, NAME_LAST."""
    parts = []
    if "NAME_FIRST" in obj and obj["NAME_FIRST"]:
        parts.append(obj["NAME_FIRST"])
    if "NAME_MIDDLE" in obj and obj["NAME_MIDDLE"]:
        parts.append(obj["NAME_MIDDLE"])
    if "NAME_LAST" in obj and obj["NAME_LAST"]:
        parts.append(obj["NAME_LAST"])
    return " ".join(parts) if parts else None
```

### Name Extraction Function

```python
def extract_names(obj, path=""):
    """Recursively extract name fields from record."""
    if isinstance(obj, dict):
        # Check for structured name first
        constructed_name = construct_name_from_parts(obj)
        if constructed_name:
            names_found.append(("CONSTRUCTED_NAME", constructed_name))

        # Check for full name fields
        for key, val in obj.items():
            if isinstance(val, dict):
                extract_names(val, f"{path}.{key}" if path else key)
            elif val and isinstance(val, str):
                key_upper = key.upper()
                if key_upper.endswith("NAME_ORG") or key_upper.endswith("NAME_FULL"):
                    names_found.append((key, val))
```

## Special Cases

### Multiple Names in One Record

If a record has multiple name entries (e.g., aliases), currently only the **first name found** is used for embedding generation.

```json
{
  "DATA_SOURCE": "TEST",
  "RECORD_ID": "008",
  "NAME_FULL": "John Smith",
  "AKA_NAME": "Jon Smythe"
}
```

**Current behavior:** Only generates embedding for `"John Smith"`

**Future enhancement:** Could generate embeddings for all names (see below)

### Case Sensitivity

Field names are checked case-insensitively:
- `NAME_FULL`, `name_full`, `Name_Full` all work
- Values are preserved as-is for embedding generation

### Unicode and Special Characters

The embedding model handles Unicode characters:

```json
{
  "DATA_SOURCE": "TEST",
  "RECORD_ID": "009",
  "NAME_FULL": "José García-López"
}
```

**Works correctly** - Unicode preserved in embedding

## Future Enhancements

Potential improvements for name handling:

### 1. Multiple Embeddings per Record

Generate embeddings for all names (primary + aliases):

```python
# Current: Single embedding
record["SEMANTIC_EMBEDDING"] = embedding_1

# Future: Multiple embeddings (if Sz supports)
record["SEMANTIC_EMBEDDING_1"] = embedding_1
record["SEMANTIC_EMBEDDING_2"] = embedding_2
```

### 2. Name Type Weighting

Weight different name types differently:
- Primary names: Higher weight
- Aliases/AKA: Lower weight
- Organization names: Different scoring

### 3. Name Prefix/Suffix Handling

Include prefixes and suffixes in constructed names:
- NAME_PREFIX: "Dr.", "Mr.", "Ms."
- NAME_SUFFIX: "Jr.", "Sr.", "III"

```python
# Enhanced construction
if "NAME_PREFIX" in obj:
    parts.insert(0, obj["NAME_PREFIX"])
if "NAME_SUFFIX" in obj:
    parts.append(obj["NAME_SUFFIX"])
```

### 4. Field Priority Configuration

Allow users to configure which fields to prioritize:

```python
# Configuration
NAME_PRIORITY = ["NAME_FULL", "NAME_ORG", "CONSTRUCTED"]
```

## Troubleshooting

### No embeddings generated

**Check:**
1. Record has at least one name field (NAME_FULL, NAME_ORG, or NAME_FIRST/LAST)
2. Name field is not empty
3. Name field is a string (not a number or null)

### Wrong name used for embedding

**Check:**
- Order of fields in JSON (first found is used)
- Nested structures (may find nested name first)
- Field naming (must end in NAME_FULL or NAME_ORG, or be NAME_FIRST/MIDDLE/LAST)

### Constructed name missing parts

**Check:**
- Field names match exactly: `NAME_FIRST`, `NAME_MIDDLE`, `NAME_LAST`
- Values are non-empty strings
- No typos in field names

## Testing Name Formats

To test different name formats:

```bash
# Load test data with various name formats
./semantic_load.py test_name_formats.json

# Search with different formats
echo '{"RECORD_ID": "search1", "NAME_FULL": "John Smith"}' > search1.json
echo '{"RECORD_ID": "search2", "NAME_FIRST": "Jane", "NAME_LAST": "Doe"}' > search2.json

./semantic_search.py search1.json
./semantic_search.py search2.json
```

## Additional Name Field Support

If you need to support additional name field patterns, modify the `extract_names()` function:

```python
# Add support for custom fields
if key_upper.endswith("BUSINESS_NAME") or key_upper.endswith("COMPANY_NAME"):
    names_found.append((key, val))
```

Or for specific prefix patterns:

```python
# Support fields starting with NAME_
if key_upper.startswith("NAME_") and len(val) > 0:
    names_found.append((key, val))
```

## References

- Senzing name attribute documentation
- [USAGE.md](USAGE.md) - General usage guide
- [test_name_formats.json](test_name_formats.json) - Example data
