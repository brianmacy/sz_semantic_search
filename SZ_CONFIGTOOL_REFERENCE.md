# sz_configtool Command Reference

Quick reference guide for the sz_configtool utility.

**Note:** For the complete list of all 120 commands, see [SZ_CONFIGTOOL_COMMANDS.md](SZ_CONFIGTOOL_COMMANDS.md)

This guide covers the most commonly used commands for basic configuration tasks.

## Invocation

```bash
sz_configtool                          # Interactive mode
sz_configtool -f <config_file>         # Execute commands from file
sz_configtool -c <ini_file>            # Specify config ini file
sz_configtool -f <file> --force        # Execute without prompts
```

## Environment Setup

```bash
export SENZING_ENGINE_CONFIGURATION_JSON='{...}'
# or
export SENZING_ROOT=/opt/senzing
```

## Common Commands

### Configuration Management

```bash
# Get current config ID
sz_configtool> getDefaultConfigID

# List all configurations
sz_configtool> getConfigRegistry

# Export configuration to file
sz_configtool> exportToFile config_backup.json

# Import configuration from file
sz_configtool> importFromFile modified_config.json

# Save current changes
sz_configtool> save

# Reload without saving changes
sz_configtool> reload_config
```

### Data Source Management

```bash
# Add a data source
sz_configtool> addDataSource CUSTOMERS

# List all data sources
sz_configtool> listDataSources

# Delete a data source
sz_configtool> deleteDataSource OLD_SOURCE
```

### Feature Type Management

```bash
# List all feature types
sz_configtool> listFeatures

# Get details of a feature type
sz_configtool> getFeature SEMANTIC_VALUE

# Modify a feature type (requires JSON syntax)
sz_configtool> setFeature {"feature": "SEMANTIC_VALUE", "candidates": "Yes"}
sz_configtool> setFeature {"feature": "NAME", "matchkey": "Yes", "candidates": "Yes"}

# Add a new feature type (requires JSON with full definition)
sz_configtool> addFeature {"feature": "NEW_FEATURE", ...}
```

**Note:** Commands use JSON syntax, not simple arguments

### Attribute Management

```bash
# List all attributes
sz_configtool> listAttributes

# Get attribute details
sz_configtool> getAttribute SEMANTIC_EMBEDDING

# Modify an attribute
sz_configtool> setAttribute SEMANTIC_EMBEDDING

# Add new attribute
sz_configtool> addAttribute NEW_ATTR
```

### Element Management

```bash
# List all elements
sz_configtool> listElements

# Get element details
sz_configtool> getElement EMBEDDING

# Modify element
sz_configtool> setElement EMBEDDING
```

## Enabling SEMANTIC_VALUE for Candidates

### Method 1: Interactive (JSON syntax required)

```bash
sz_configtool
sz_configtool> getFeature SEMANTIC_VALUE
# Review current settings
sz_configtool> setFeature {"feature": "SEMANTIC_VALUE", "candidates": "Yes"}
sz_configtool> save
sz_configtool> quit
```

**Important:** The JSON must be properly formatted with quotes around both keys and values.

### Method 2: One-liner

```bash
echo 'setFeature {"feature": "SEMANTIC_VALUE", "candidates": "Yes"}' | sz_configtool
# Then manually save in the tool
```

**Note:** sz_configtool uses JSON syntax for most commands, not simple key-value arguments.

## Output Formats

Many list commands support output formats:

```bash
sz_configtool> listDataSources table     # Table format (default)
sz_configtool> listDataSources json      # JSON format
sz_configtool> listFeatures json         # JSON format
sz_configtool> getConfigRegistry jsonl   # JSON Lines format
```

## Help and Information

```bash
# Get general help
sz_configtool> help

# Get help for specific command
sz_configtool> help addDataSource

# Show command history
sz_configtool> history

# Change display theme
sz_configtool> setTheme dark
sz_configtool> setTheme light
sz_configtool> setTheme default
```

## Workflow Example: Adding Data Source

```bash
sz_configtool
sz_configtool> getDefaultConfigID
# Note current config ID: 1

sz_configtool> addDataSource NEW_CUSTOMERS
sz_configtool> listDataSources
# Verify NEW_CUSTOMERS is listed

sz_configtool> save
# New config created and set as default

sz_configtool> getDefaultConfigID
# New config ID: 2

sz_configtool> quit
```

## Workflow Example: Modifying Feature Type

```bash
sz_configtool
sz_configtool> getFeature NAME
# Review current NAME feature settings

sz_configtool> setFeature NAME
# Interactive prompts for each setting
# FTYPE_CODE: NAME
# FTYPE_DESC: Name
# FTYPE_FREQ: FF
# USED_FOR_CAND: Yes
# ...continue through all settings

sz_configtool> save
sz_configtool> quit
```

## Important Notes

1. **Changes are not saved automatically** - Must use `save` command
2. **Data sources are case-insensitive** - Automatically uppercased
3. **Config IDs are immutable** - Each save creates a new config
4. **Old configs remain** - Can revert by setting old config as default
5. **Requires restart** - Running Sz engines must restart to use new config

## Comparison: sz_configtool vs Python Script

| Aspect | sz_configtool | enable_semantic_candidates.py |
|--------|---------------|-------------------------------|
| Interface | Interactive CLI | Automated script |
| Ease of use | Requires commands | Single command |
| Validation | Manual | Automatic |
| Dry run | No built-in | --dry-run flag |
| Flexibility | Full control | Specific task |
| Best for | Exploration | Automation |

## Advanced: Config File Format (.g2c)

Config files contain one command per line:

```
# Comments start with #
addDataSource CUSTOMERS
addDataSource VENDORS
setFeature SEMANTIC_VALUE USED_FOR_CAND Yes
save
```

Execute with:
```bash
sz_configtool -f setup.g2c
```

Use `--force` to skip confirmation prompts:
```bash
sz_configtool -f setup.g2c --force
```

## Troubleshooting

### "Cannot connect to database"

**Check:**
- `SENZING_ENGINE_CONFIGURATION_JSON` is set
- Database connection string is valid
- Database is running and accessible

### "Feature not found"

**Check:**
- Feature type name spelling (case-sensitive)
- Feature type exists: `listFeatures`

### "Configuration not saved"

**Cause:** Forgot to run `save` command

**Solution:** Run `save` before `quit`

### "Command not recognized"

**Check:**
- Command spelling (case-sensitive)
- Use `help` to see available commands

## Related Tools

- **sz_explorer** - Database and entity exploration
- **sz_diagnostic** - System diagnostics
- **enable_semantic_candidates.py** - Automated SEMANTIC_VALUE enablement

## Python API Equivalent

For scripting, use the Python SDK instead:

```python
from senzing_core import SzAbstractFactoryCore

factory = SzAbstractFactoryCore("app", engine_config)
config_manager = factory.create_config_manager()

# Get current config
config_id = config_manager.get_default_config_id()
config_json = config_manager.get_config(config_id)

# Modify config (parse JSON, make changes)
# ...

# Save new config
new_config_id = config_manager.add_config(new_config_json, "Description")
config_manager.set_default_config_id(new_config_id)
```

See `enable_semantic_candidates.py` for a complete example.

## Reference Links

- [Senzing SDK Documentation](https://docs.senzing.com/)
- sz_configtool - included in senzingsdk-tools package
- Configuration examples - see Senzing SDK documentation
