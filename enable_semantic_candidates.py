#! /usr/bin/env python3

"""
Create NAME_SEM_KEY feature type for semantic candidate generation.

This script automates the creation of NAME_SEM_KEY by:
1. Getting the current default configuration
2. Copying SEMANTIC_VALUE to create NAME_SEM_KEY
3. Setting NAME_SEM_KEY for candidate generation only (USED_FOR_CAND='Yes', no scoring)
4. Adding required attributes (NAME_SEM_KEY_EMBEDDING, NAME_SEM_KEY_LABEL, NAME_SEM_KEY_ALGORITHM)
5. Adding the new configuration as default

Equivalent sz_configtool commands (if doing manually):

  # Get SEMANTIC_VALUE configuration
  getFeature SEMANTIC_VALUE jsonl

  # Add NAME_SEM_KEY feature (modified from SEMANTIC_VALUE)
  addFeature {"feature": "NAME_SEM_KEY", "class": "OTHER", "behavior": "FF", "anonymize": "No", "candidates": "Yes", "standardize": "", "expression": "", "matchKey": "No", "version": 1, "elementList": [{"element": "EMBEDDING", "expressed": "No", "compared": "No", "derived": "Yes", "display": "No"}, {"element": "ALGORITHM", "expressed": "No", "compared": "No", "derived": "No", "display": "No"}, {"element": "LABEL", "expressed": "No", "compared": "No", "derived": "No", "display": "Yes"}]}

  # Add attribute mappings
  addAttribute {"attribute": "NAME_SEM_KEY_EMBEDDING", "class": "IDENTIFIER", "feature": "NAME_SEM_KEY", "element": "EMBEDDING", "required": "Yes", "default": "", "advanced": "No", "internal": "No"}
  addAttribute {"attribute": "NAME_SEM_KEY_LABEL", "class": "IDENTIFIER", "feature": "NAME_SEM_KEY", "element": "LABEL", "required": "Yes", "default": "", "advanced": "No", "internal": "No"}
  addAttribute {"attribute": "NAME_SEM_KEY_ALGORITHM", "class": "IDENTIFIER", "feature": "NAME_SEM_KEY", "element": "ALGORITHM", "required": "No", "default": "", "advanced": "Yes", "internal": "No"}

  # Save configuration
  save

Key differences from SEMANTIC_VALUE:
  - candidates: "Yes" (was "No") - enables candidate generation
  - comparison: removed (was "SEMANTIC_SIMILARITY_COMP") - removes scoring plugin, disables scoring
  - element compared: "No" (was "Yes") - elements not compared since no comparison function
  - matchKey: "No" (was "Yes") - doesn't show in match keys (cosmetic, since no scoring anyway)
"""

import argparse
import orjson as json
import os
import sys
import traceback
from datetime import datetime

import senzing_core


def create_name_sem_key_feature(config_json):
    """
    Create NAME_SEM_KEY feature type by copying SEMANTIC_VALUE.

    Args:
        config_json: Current configuration as JSON string

    Returns:
        Modified configuration as JSON string
    """
    config = json.loads(config_json)

    if "G2_CONFIG" not in config:
        print("✗ Error: G2_CONFIG not found in configuration", file=sys.stderr)
        return None

    g2_config = config["G2_CONFIG"]

    # Find SEMANTIC_VALUE feature type
    semantic_value_ftype = None
    if "CFG_FTYPE" in g2_config:
        for ftype in g2_config["CFG_FTYPE"]:
            if ftype.get("FTYPE_CODE") == "SEMANTIC_VALUE":
                semantic_value_ftype = ftype
                print(f"✓ Found SEMANTIC_VALUE feature type (FTYPE_ID: {ftype.get('FTYPE_ID')})")
                break

    if not semantic_value_ftype:
        print("✗ Error: SEMANTIC_VALUE feature type not found", file=sys.stderr)
        return None

    # Check if NAME_SEM_KEY already exists
    for ftype in g2_config.get("CFG_FTYPE", []):
        if ftype.get("FTYPE_CODE") == "NAME_SEM_KEY":
            print("✓ NAME_SEM_KEY already exists, will update it")
            ftype["USED_FOR_CAND"] = "Yes"
            ftype["SHOW_IN_MATCH_KEY"] = "No"  # No scoring
            print(f"  Updated FTYPE_ID: {ftype.get('FTYPE_ID')}")
            return json.dumps(config).decode('utf-8')

    # Find highest FTYPE_ID to assign new ID
    max_ftype_id = max([ftype.get("FTYPE_ID", 0) for ftype in g2_config.get("CFG_FTYPE", [])])
    new_ftype_id = max_ftype_id + 1

    # Create NAME_SEM_KEY by copying SEMANTIC_VALUE
    name_sem_key_ftype = dict(semantic_value_ftype)
    name_sem_key_ftype["FTYPE_ID"] = new_ftype_id
    name_sem_key_ftype["FTYPE_CODE"] = "NAME_SEM_KEY"
    name_sem_key_ftype["FTYPE_DESC"] = "Name semantic key for candidate generation"
    name_sem_key_ftype["USED_FOR_CAND"] = "Yes"  # Enable for candidates
    name_sem_key_ftype["SHOW_IN_MATCH_KEY"] = "No"  # Disable scoring

    g2_config["CFG_FTYPE"].append(name_sem_key_ftype)
    print(f"✓ Created NAME_SEM_KEY feature type (FTYPE_ID: {new_ftype_id})")
    print(f"  USED_FOR_CAND: Yes (candidates enabled)")
    print(f"  SHOW_IN_MATCH_KEY: No (scoring disabled)")

    # Find SEMANTIC_VALUE attributes to copy
    semantic_attrs = []
    if "CFG_ATTR" in g2_config:
        for attr in g2_config["CFG_ATTR"]:
            if attr.get("FTYPE_CODE") == "SEMANTIC_VALUE":
                semantic_attrs.append(attr)

    print(f"✓ Found {len(semantic_attrs)} SEMANTIC_VALUE attributes to copy")

    # Find highest ATTR_ID
    max_attr_id = max([attr.get("ATTR_ID", 0) for attr in g2_config.get("CFG_ATTR", [])])

    # Create NAME_SEM_KEY attributes
    attr_mapping = {
        "SEMANTIC_EMBEDDING": "NAME_SEM_KEY_EMBEDDING",
        "SEMANTIC_LABEL": "NAME_SEM_KEY_LABEL",
        "SEMANTIC_ALGORITHM": "NAME_SEM_KEY_ALGORITHM"
    }

    for semantic_attr in semantic_attrs:
        attr_code = semantic_attr.get("ATTR_CODE")
        if attr_code in attr_mapping:
            max_attr_id += 1
            new_attr = dict(semantic_attr)
            new_attr["ATTR_ID"] = max_attr_id
            new_attr["ATTR_CODE"] = attr_mapping[attr_code]
            new_attr["FTYPE_CODE"] = "NAME_SEM_KEY"

            g2_config["CFG_ATTR"].append(new_attr)
            print(f"  ✓ Created attribute: {new_attr['ATTR_CODE']} (ATTR_ID: {max_attr_id})")

    # Update CFG_FBOM (Feature Bill of Materials) - copy from SEMANTIC_VALUE
    if "CFG_FBOM" in g2_config:
        semantic_fboms = [fbom for fbom in g2_config["CFG_FBOM"]
                         if fbom.get("FTYPE_ID") == semantic_value_ftype.get("FTYPE_ID")]

        print(f"✓ Found {len(semantic_fboms)} FBOM entries to copy")

        for semantic_fbom in semantic_fboms:
            new_fbom = dict(semantic_fbom)
            new_fbom["FTYPE_ID"] = new_ftype_id
            g2_config["CFG_FBOM"].append(new_fbom)
            print(f"  ✓ Created FBOM entry for FELEM_ID: {new_fbom.get('FELEM_ID')}")

    return json.dumps(config).decode('utf-8')


def main():
    parser = argparse.ArgumentParser(
        description="Create NAME_SEM_KEY feature type for semantic candidate generation"
    )
    parser.add_argument(
        "-t", "--debugTrace",
        dest="debugTrace",
        action="store_true",
        default=False,
        help="Enable debug trace logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without applying them"
    )
    args = parser.parse_args()

    engine_config = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
    if not engine_config:
        print(
            "Error: SENZING_ENGINE_CONFIGURATION_JSON environment variable not set",
            file=sys.stderr,
        )
        sys.exit(-1)

    try:
        print("Initializing Senzing SDK...")
        factory = senzing_core.SzAbstractFactoryCore(
            "enable_semantic_candidates",
            engine_config,
            verbose_logging=args.debugTrace
        )

        config_manager = factory.create_configmanager()

        # Get current default configuration ID
        print("\nGetting current default configuration...")
        default_config_id = config_manager.get_default_config_id()
        print(f"✓ Current default config ID: {default_config_id}")

        # Export current configuration
        print("\nExporting current configuration...")
        sz_config = config_manager.create_config_from_config_id(default_config_id)
        current_config_json = sz_config.export()
        print("✓ Configuration exported")

        # Modify configuration
        print("\nCreating NAME_SEM_KEY feature type...")
        new_config_json = create_name_sem_key_feature(current_config_json)

        if new_config_json is None:
            print("\n✗ Configuration modification failed", file=sys.stderr)
            sys.exit(-1)

        if args.dry_run:
            print("\n[DRY RUN] Changes would be applied but not committed")
            print("Run without --dry-run to apply changes")
            sys.exit(0)

        # Add new configuration
        print("\nAdding modified configuration...")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        comment = f"Create NAME_SEM_KEY for semantic candidates - {timestamp}"

        new_config_id = config_manager.register_config(new_config_json, comment)
        print(f"✓ New configuration added with ID: {new_config_id}")

        # Set as default
        print("\nSetting new configuration as default...")
        config_manager.set_default_config_id(new_config_id)
        print(f"✓ Configuration {new_config_id} set as default")

        print("\n" + "="*60)
        print("SUCCESS: NAME_SEM_KEY feature type created")
        print("="*60)
        print(f"\nOld config ID: {default_config_id}")
        print(f"New config ID: {new_config_id}")
        print("\nFeature configuration:")
        print("  - NAME_SEM_KEY: Candidates enabled, scoring disabled")
        print("  - SEMANTIC_VALUE: Original settings unchanged")
        print(f"\nNote: Restart any running Sz processes to use the new configuration")
        print("\nIMPORTANT: This feature requires Senzing Advanced Search license")

    except Exception as ex:
        traceback.print_exc()
        print(f"\n✗ Error: {ex}", file=sys.stderr)

        if "license" in str(ex).lower() or "advanced" in str(ex).lower():
            print("\nThis feature requires Senzing Advanced Search license.", file=sys.stderr)
            print("Contact Senzing to obtain the appropriate license.", file=sys.stderr)

        sys.exit(-1)


if __name__ == "__main__":
    main()
