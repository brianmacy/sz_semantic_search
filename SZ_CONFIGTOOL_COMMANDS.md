# sz_configtool Complete Command Reference

Complete list of all 120 commands available in sz_configtool.

## General Commands

```
help                           - Get help on commands
history                        - Show command history
quit                          - Exit the tool
exit                          - Exit the tool
save                          - Save configuration changes
shell                         - Execute shell commands
setTheme                      - Set color theme (default/light/dark)
touch                         - Touch/update configuration
```

## Configuration Management

```
getDefaultConfigID            - Get current default config ID
getConfigRegistry             - List all configurations
reload_config                 - Reload config, discard changes
exportToFile                  - Export configuration to file
importFromFile                - Import configuration from file
getCompatibilityVersion       - Get compatibility version
updateCompatibilityVersion    - Update compatibility version
verifyCompatibilityVersion    - Verify compatibility version
updateFeatureVersion          - Update feature version
```

## Configuration Sections

```
addConfigSection              - Add a configuration section
removeConfigSection           - Remove a configuration section
getConfigSection              - Get configuration section details
addConfigSectionField         - Add field to config section
removeConfigSectionField      - Remove field from config section
```

## Data Source Management

```
addDataSource                 - Add/register a data source
listDataSources               - List all data sources
deleteDataSource              - Delete a data source
```

## Feature Type Management

```
addFeature                    - Add a new feature type
setFeature                    - Modify existing feature type
listFeatures                  - List all feature types
getFeature                    - Get feature type details
deleteFeature                 - Delete a feature type
```

## Element Management

```
addElement                    - Add a new element
listElements                  - List all elements
getElement                    - Get element details
deleteElement                 - Delete an element
```

## Feature-Element Relationships

```
addElementToFeature           - Add element to a feature
setFeatureElement             - Set feature element properties
setFeatureElementDerived      - Set element as derived
setFeatureElementDisplayLevel - Set element display level
deleteElementFromFeature      - Remove element from feature
```

## Attribute Management

```
addAttribute                  - Add a new attribute
setAttribute                  - Modify existing attribute
listAttributes                - List all attributes
getAttribute                  - Get attribute details
deleteAttribute               - Delete an attribute
```

## Standardize Functions

```
addStandardizeFunction        - Add standardize function
addStandardizeFunc            - Add standardize function (alias)
removeStandardizeFunction     - Remove standardize function
listStandardizeFunctions      - List all standardize functions
```

## Standardize Calls

```
addStandardizeCall            - Add standardize call
getStandardizeCall            - Get standardize call details
listStandardizeCalls          - List all standardize calls
deleteStandardizeCall         - Delete a standardize call
```

## Expression Functions

```
addExpressionFunction         - Add expression function
addExpressionFunc             - Add expression function (alias)
removeExpressionFunction      - Remove expression function
listExpressionFunctions       - List all expression functions
```

## Expression Calls

```
addExpressionCall             - Add expression call
getExpressionCall             - Get expression call details
listExpressionCalls           - List all expression calls
deleteExpressionCall          - Delete an expression call
addExpressionCallElement      - Add element to expression call
deleteExpressionCallElement   - Remove element from expression call
```

## Comparison Functions

```
addComparisonFunction         - Add comparison function
addComparisonFunc             - Add comparison function (alias)
removeComparisonFunction      - Remove comparison function
listComparisonFunctions       - List all comparison functions
addComparisonFuncReturnCode   - Add return code to comparison function
```

## Comparison Calls

```
addComparisonCall             - Add comparison call
getComparisonCall             - Get comparison call details
listComparisonCalls           - List all comparison calls
deleteComparisonCall          - Delete a comparison call
addComparisonCallElement      - Add element to comparison call
deleteComparisonCallElement   - Remove element from comparison call
```

## Distinct Functions

```
addDistinctFunction           - Add distinct function
listDistinctFunctions         - List all distinct functions
```

## Distinct Calls

```
addDistinctCall               - Add distinct call
getDistinctCall               - Get distinct call details
listDistinctCalls             - List all distinct calls
deleteDistinctCall            - Delete a distinct call
addDistinctCallElement        - Add element to distinct call
deleteDistinctCallElement     - Remove element from distinct call
```

## Feature Comparisons

```
addFeatureComparison          - Add feature comparison
deleteFeatureComparison       - Delete feature comparison
addFeatureComparisonElement   - Add element to feature comparison
deleteFeatureComparisonElement - Remove element from feature comparison
addFeatureDistinctCallElement - Add element to feature distinct call
```

## Comparison Thresholds

```
addComparisonThreshold        - Add comparison threshold
setComparisonThreshold        - Modify comparison threshold
listComparisonThresholds      - List all comparison thresholds
deleteComparisonThreshold     - Delete a comparison threshold
```

## Generic Thresholds

```
addGenericThreshold           - Add generic threshold
setGenericThreshold           - Modify generic threshold
listGenericThresholds         - List all generic thresholds
deleteGenericThreshold        - Delete a generic threshold
```

## Generic Plans

```
listGenericPlans              - List all generic plans
cloneGenericPlan              - Clone a generic plan
deleteGenericPlan             - Delete a generic plan
```

## Rules

```
addRule                       - Add a rule
setRule                       - Modify existing rule
getRule                       - Get rule details
listRules                     - List all rules
deleteRule                    - Delete a rule
```

## Fragments

```
addFragment                   - Add a fragment
setFragment                   - Modify existing fragment
getFragment                   - Get fragment details
listFragments                 - List all fragments
deleteFragment                - Delete a fragment
```

## Behavior Overrides

```
addBehaviorOverride           - Add behavior override
listBehaviorOverrides         - List all behavior overrides
deleteBehaviorOverride        - Delete a behavior override
```

## Entity Scoring

```
addEntityScore                - Add entity score configuration
```

## Name Hashing

```
addToNamehash                 - Add to name hash
deleteFromNamehash            - Remove from name hash
addToNameSSNLast4hash         - Add to name SSN last4 hash
deleteFromSSNLast4hash        - Remove from SSN last4 hash
```

## System Management

```
listSystemParameters          - List all system parameters
setSystemParameter            - Set a system parameter
setSetting                    - Set a setting
listReferenceCodes            - List reference codes
```

## Template Operations

```
templateAdd                   - Add from template
```

## Command Syntax Examples

### Data Sources
```
addDataSource CUSTOMERS
listDataSources
listDataSources json
deleteDataSource OLD_SOURCE
```

### Features
```
getFeature NAME
setFeature {"feature": "NAME_SEM_KEY", "candidates": "Yes"}
listFeatures
listFeatures json
addFeature {"feature": "NEW_FEATURE", ...}
deleteFeature OLD_FEATURE
```

### Attributes
```
getAttribute SEMANTIC_EMBEDDING
setAttribute {"attribute": "SEMANTIC_EMBEDDING", ...}
listAttributes
listAttributes json
deleteAttribute OLD_ATTR
```

### Elements
```
getElement EMBEDDING
listElements
listElements json
addElement {"element": "NEW_ELEMENT", ...}
deleteElement OLD_ELEMENT
```

### Configuration
```
getDefaultConfigID
getConfigRegistry
getConfigRegistry json
exportToFile backup.json
importFromFile modified.json
save
reload_config
```

## Output Formats

Many list commands support output formats:
- `table` - Tabular format (default)
- `json` - JSON format
- `jsonl` - JSON Lines format

Examples:
```
listFeatures table
listFeatures json
listDataSources json
getConfigRegistry jsonl
```

## Important Notes

1. **JSON Syntax Required**: Most add/set commands require JSON syntax
   - Example: `setFeature {"feature": "NAME", "candidates": "Yes"}`
   - Keys and values must be quoted

2. **Save Required**: Changes are not saved automatically
   - Use `save` command before `quit`
   - Or use `reload_config` to discard changes

3. **Case Sensitivity**:
   - Command names are case-sensitive
   - Data source codes are automatically uppercased
   - Feature codes are case-sensitive in JSON

4. **Complex Operations**: Some operations require multiple steps
   - Creating a new feature requires: addFeature, addAttribute, addElementToFeature, etc.
   - Use the Python script for complex operations

## Commonly Used Command Sequences

### Add a Data Source
```
addDataSource CUSTOMERS
save
```

### Modify a Feature Type
```
getFeature NAME_SEM_KEY
setFeature {"feature": "NAME_SEM_KEY", "candidates": "Yes"}
save
```

### Export and Import Configuration
```
exportToFile backup_config.json
# Edit the file externally
importFromFile modified_config.json
save
```

### View All Features
```
listFeatures json
```

### Check Current Config
```
getDefaultConfigID
getConfigRegistry json
```

## Related Files

- sz_configtool source: `~/dev/G2/dev/apps/g2/python/sz-python-tools/sz_tools/sz_configtool`
- Python alternative: `enable_semantic_candidates.py` (automated config modification)

## Getting Help

```
# General help
help

# Help for specific command
help addDataSource
help setFeature
help listFeatures
```

## Tips

1. **Use --dry-run with scripts**: Test configuration changes before applying
2. **Export before major changes**: Always export current config as backup
3. **Use Python scripts for automation**: sz_configtool is better for exploration
4. **Check syntax with help**: Use `help <command>` to see JSON syntax requirements
5. **Save frequently**: Don't lose work - save after significant changes

## Complete Command Count

Total commands: **120**

Organized by category:
- Configuration: 12 commands
- Data Sources: 3 commands
- Features: 5 commands
- Elements: 4 commands
- Attributes: 4 commands
- Standardize: 5 commands
- Expression: 7 commands
- Comparison: 11 commands
- Distinct: 6 commands
- Thresholds: 7 commands
- Rules & Fragments: 8 commands
- Behavior: 3 commands
- System: 4 commands
- Utilities: 8 commands
- Feature Relationships: 9 commands
- Generic Plans: 3 commands
- Name Hashing: 4 commands
- Plus 17 other specialized commands
