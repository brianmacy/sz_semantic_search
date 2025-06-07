#! /usr/bin/env python3

import argparse
import orjson as json
import os
import sys
import traceback


import uritools
import psycopg2
import pgvector
from pgvector.psycopg2 import register_vector
import threading


import senzing_core

#from sentence_transformers import SentenceTransformer
from fast_sentence_transformers import FastSentenceTransformer as SentenceTransformer

import concurrent

global records_left
data = threading.local()

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device="cpu") #, device="cuda")
print(f"Device: {model.device}")

def get_postgresql_url(engine_config):
    # BEMIMP currently doesn't support database clustering
    config = json.loads(engine_config)
    senzing_database_url = config["SQL"]["CONNECTION"]

    parsed = uritools.urisplit(senzing_database_url)
    if "schema" in parsed.getquerydict():
        # BEMIMP
        print("Non-default schema not currently supported.")
        sys.exit(-1)

    if not parsed.port and len(parsed.path) <= 1:
        # print("URI with DBi, reparsing modified URI")
        # historically, postgresql URIs allow the DB to be after after a colon
        # or part of the path
        # actual PostgreSQL URIs aren't standard either though the python interface
        # attempts to normalize it so we convert here
        values = parsed.host.split(":")
        host = values[0]
        port = None
        path = None
        if len(values) > 2:
            port = values[1]
            path = "/" + values[2]
        else:
            path = "/" + values[1]

        mod_uri = uritools.uricompose(
            scheme=parsed.scheme,
            userinfo=parsed.userinfo,
            host=host,
            path=path,
            port=port,
            query=parsed.query,
            fragment=parsed.fragment,
        )
        return mod_uri

    return senzing_database_url

def process_name(cursor, data_source, record_id, val):
    if not val:
        return

    try:
        embedding = model.encode(val)
        #print(embedding.shape) ## this defines the size of the vector
        #cursor.execute("INSERT INTO NAME_SEARCH_EMB (DATA_SOURCE, RECORD_ID, EMBEDDING) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",  (data_source, record_id, embedding))
    except Exception as ex:
        traceback.print_exc()
        print(ex)
        print("Make sure the table exists and pgvector is enabled")
        print("CREATE EXTENSION vector")
        print("CREATE TABLE NAME_SEARCH_EMB (DATA_SOURCE TEXT, RECORD_ID TEXT, EMBEDDING VECTOR(384))");
        print("CREATE INDEX ON NAME_SEARCH_EMB USING hnsw (EMBEDDING vector_cosine_ops)");
        print(f"val {val}")
        raise


def process_record_for_embed(cursor, data_source, record_id, record):
    for key,val in record.items():
        if isinstance(val, dict):
            process_record_for_embed(cursor, data_source, record_id, val)
        else:
            if key.upper().endswith('NAME_ORG') or key.upper().endswith('NAME_FULL'):
                process_name(cursor, data_source, record_id, val)

def get_connection(url):
    print(f"Connecting with {url}")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    register_vector(conn)
    return conn

def process_record(url, line):
    global records_left
    try:
        if not hasattr(data, 'conn'):
            data.conn = get_connection(url)

        #print(f"data.conn {data.conn}")
        cur = data.conn.cursor()
        rec = json.loads(line)
        data_source = rec['DATA_SOURCE']
        record_id = rec['RECORD_ID']
        #engine.add_record(data_source, record_id, line)
        process_record_for_embed(cur, data_source, record_id, rec)
        records_left -= 1
        cur.close()

        if records_left % 10000 == 0:
            print(f"{records_left} records left...")
    except Exception as ex:
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

    url = get_postgresql_url(engine_config)
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
                executor.submit(process_record, url, line)
                if count%10000 == 0:
                    print(f"Processed {count}...")
        executor.shutdown(wait=True, cancel_futures=False)
except Exception as ex:
    traceback.print_exc()
    print(ex)
    sys.exit(-1)
