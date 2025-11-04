#! /usr/bin/env python3

import argparse
import orjson as json
import os
import sys
import traceback
import threading
import concurrent

import senzing_core

from sentence_transformers import SentenceTransformer
# from fast_sentence_transformers import FastSentenceTransformer as SentenceTransformer

global records_left
data = threading.local()

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2", device="cpu"
)
print(f"Device: {model.device}")


def add_embeddings_to_record(record):
    """Add SEMANTIC_EMBEDDING and SEMANTIC_LABEL fields to record based on name fields."""
    names_found = []

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

    def extract_names(obj, path=""):
        """Recursively extract name fields from record."""
        if isinstance(obj, dict):
            # Check for structured name (NAME_FIRST, NAME_MIDDLE, NAME_LAST)
            constructed_name = construct_name_from_parts(obj)
            if constructed_name:
                names_found.append(("CONSTRUCTED_NAME", constructed_name))

            # Also check for full name fields
            for key, val in obj.items():
                if isinstance(val, dict):
                    extract_names(val, f"{path}.{key}" if path else key)
                elif val and isinstance(val, str):
                    key_upper = key.upper()
                    if key_upper.endswith("NAME_ORG") or key_upper.endswith("NAME_FULL"):
                        names_found.append((key, val))

    extract_names(record)

    # Add embeddings for each name found
    if names_found:
        # Use the first name found (prioritize full names over constructed)
        key, name_val = names_found[0]
        embedding = model.encode(name_val)

        # Convert numpy array to list for JSON serialization
        # Use NAME_SEM_KEY for candidate generation (no scoring)
        record["NAME_SEM_KEY_LABEL"] = name_val
        record["NAME_SEM_KEY_EMBEDDING"] = json.dumps(embedding.tolist()).decode('utf-8')

    return record


def process_record(engine, line):
    global records_left
    try:
        if not hasattr(data, "engine"):
            data.engine = engine

        rec = json.loads(line)
        data_source = rec["DATA_SOURCE"]
        record_id = rec["RECORD_ID"]

        # Add embeddings directly to the record
        rec = add_embeddings_to_record(rec)

        # Add the record to Sz with embeddings
        data.engine.add_record(data_source, record_id, json.dumps(rec))

        records_left -= 1

        if records_left % 10000 == 0:
            print(f"{records_left} records left...")
    except Exception as ex:
        traceback.print_exc()
        print(ex)


parser = argparse.ArgumentParser()
parser.add_argument("fileToProcess", default=None)
parser.add_argument(
    "-t",
    "--debugTrace",
    dest="debugTrace",
    action="store_true",
    default=False,
    help="output debug trace information",
)
parser.add_argument(
    "-x",
    "--skipEnginePrime",
    dest="skipEnginePrime",
    action="store_true",
    default=False,
    help="skip the engine prime_engine to speed up execution",
)
args = parser.parse_args()

engine_config = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
if not engine_config:
    print(
        "The environment variable SENZING_ENGINE_CONFIGURATION_JSON must be set with a proper JSON configuration.",
        file=sys.stderr,
    )
    print(
        "Please see https://senzing.zendesk.com/hc/en-us/articles/360038774134-G2Module-Configuration-and-the-Senzing-API",
        file=sys.stderr,
    )
    sys.exit(-1)

# Initialize the G2Engine
factory = senzing_core.SzAbstractFactoryCore(
    "semantic_load", engine_config, verbose_logging=args.debugTrace
)

try:
    engine = factory.create_engine()
    if not args.skipEnginePrime:
        engine.prime_engine()
    print(factory.create_product().get_version())

    with concurrent.futures.ThreadPoolExecutor(20) as executor:
        print(f"Threads: {executor._max_workers}")
        with open(args.fileToProcess, "r") as fp:
            count = 0
            records_left = 0
            for line in fp:
                count += 1
                records_left += 1
                executor.submit(process_record, engine, line)
                if count % 10000 == 0:
                    print(f"Processed {count}...")
        executor.shutdown(wait=True, cancel_futures=False)
except Exception as ex:
    traceback.print_exc()
    print(ex)
    sys.exit(-1)
