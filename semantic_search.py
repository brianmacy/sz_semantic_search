#! /usr/bin/env python3

import concurrent.futures

import argparse
import pathlib
import orjson as json
import itertools
import uritools

import sys
import os
import time
import threading
from timeit import default_timer as timer
import traceback

import psycopg2
import pgvector
from pgvector.psycopg2 import register_vector

import senzing_core
from senzing import SzEngineFlags, SzError

INTERVAL = 1000

#from sentence_transformers import SentenceTransformer
from fast_sentence_transformers import FastSentenceTransformer as SentenceTransformer

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

def process_name(cursor, val):
    if not val:
        return []

    try:
        ret = []
        embedding = model.encode(val)
        #print(embedding.shape) ## this defines the size of the vector
        #cursor.execute("SELECT DATA_SOURCE, RECORD_ID FROM NAME_SEARCH_EMB ORDER BY EMBEDDING <=> %s LIMIT 100",  (embedding,))
        cursor.execute("SELECT DATA_SOURCE, RECORD_ID, 1-(EMBEDDING <=> %s) FROM NAME_SEARCH_EMB WHERE 1-(EMBEDDING <=> %s) > 0.8 ORDER BY EMBEDDING <=> %s ASC LIMIT 100",  (embedding,embedding,embedding,))
        for row in cursor:
            #print(f"Got {row[0]} : {row[1]} : {row[2]}")
            ret.append([row[0],row[1]])
        #print(ret)
        return ret
    except Exception as ex:
        traceback.print_exc()
        print(ex)
        print("Make sure the table exists and pgvector is enabled")
        print("CREATE EXTENSION vector")
        print("CREATE TABLE NAME_SEARCH_EMB (DATA_SOURCE TEXT, RECORD_ID TEXT, EMBEDDING VECTOR(384))");
        print("CREATE INDEX ON NAME_SEARCH_EMB USING hnsw (EMBEDDING vector_cosine_ops)");
        print(f"val {val}")
        raise


def process_record_for_embed(cursor, record):
    found_records = []

    for key,val in record.items():
        if isinstance(val, dict):
            found_records.extend(process_record_for_embed(cursor, val))
        else:
            if key.upper().endswith('NAME_ORG') or key.upper().endswith('NAME_FULL'):
                found_records.extend(process_name(cursor, val))
    return found_records

def get_connection(url):
    print(f"Connecting with {url}")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    register_vector(conn)
    return conn


def process_line(engine, line, url):

    try:
        if not hasattr(data, 'conn'):
            data.conn = get_connection(url)
        cursor = data.conn.cursor()

        record = json.loads(line.encode())
        startTime = timer()
       
        forced_records = process_record_for_embed(cursor, record)
        if forced_records:
            forced_candidates = dict()
            forced_candidates["RECORDS"] = []
            for dsrc,id in forced_records:
                forced_candidates["RECORDS"].append({"DATA_SOURCE":dsrc,"RECORD_ID":id})
            #print(forced_candidates)
            record["_FORCED_CANDIDATES"] = forced_candidates

        response = None
        response = engine.search_by_attributes(
            json.dumps(record), SzEngineFlags.SZ_SEARCH_BY_ATTRIBUTES_MINIMAL_ALL
        )
        # engine.searchByAttributes( line, response, SzEngineFlags.SZ_SEARCH_INCLUDE_FEATURE_SCORES )
        # engine.searchByAttributes( line, response, SzEngineFlags.SZ_ENTITY_INCLUDE_RECORD_DATA )
        # engine.searchByAttributes( line, response, SzEngineFlags.SZ_SEARCH_INCLUDE_FEATURE_SCORES | SzEngineFlags.SZ_ENTITY_INCLUDE_RECORD_DATA )
        # engine.searchByAttributes( line, response, SzEngineFlags.SZ_SEARCH_INCLUDE_FEATURE_SCORES | SzEngineFlags.SZ_ENTITY_INCLUDE_RECORD_DATA | SzEngineFlags.SZ_ENTITY_INCLUDE_RECORD_JSON_DATA)
        # engine.searchByAttributes( line, response, SzEngineFlags.SZ_SEARCH_INCLUDE_FEATURE_SCORES | SzEngineFlags.SZ_ENTITY_INCLUDE_RECORD_DATA | SzEngineFlags.SZ_ENTITY_INCLUDE_REPRESENTATIVE_FEATURES )
        return (timer() - startTime, record["RECORD_ID"], response)
    except Exception as err:
        traceback.print_exc()
        print(f"{err} [{line}]", file=sys.stderr)
        raise


try:
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
    args = parser.parse_args()

    engine_config = os.getenv("SENZING_ENGINE_CONFIGURATION_JSON")
    if not engine_config:
        print(
            "The environment variable SENZING_ENGINE_CONFIGURATION_JSON must be set with a proper JSON configuration.",
            file=sys.stderr,
        )
        print(
            "Please see https://senzing.zendesk.com/hc/en-us/articles/360038774134-SzModule-Configuration-and-the-Senzing-API",
            file=sys.stderr,
        )
        exit(-1)

    # Initialize Senzing
    factory = senzing_core.SzAbstractFactoryCore(
        "semantic_search", engine_config, verbose_logging=args.debugTrace
    )

    url = get_postgresql_url(engine_config)

    g2 = factory.create_engine()
    g2.prime_engine()
    max_workers = int(os.getenv("SENZING_THREADS_PER_PROCESS", 0))
    if not max_workers:  # reset to null for executors
        max_workers = None

    g2Diagnostic = factory.create_diagnostic()
    response = g2Diagnostic.check_datastore_performance(3)
    print(response)

    beginTime = prevTime = time.time()
    timeMin = timeMax = timeTot = count = 0
    timesAll = []

    with open(args.fileToProcess, "r") as fp:
        numLines = 0
        q_multiple = 2
        total_entities_returned = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers) as executor:
            print(f"Searching with {executor._max_workers} threads")
            try:
                futures = {
                    executor.submit(process_line, g2, line, url): line
                    for line in itertools.islice(fp, q_multiple * executor._max_workers)
                }

                while futures:

                    done, _ = concurrent.futures.wait(
                        futures, return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    for fut in done:
                        result = fut.result()
                        futures.pop(fut)

                        if result:
                            count += 1
                            result_time = result[0]
                            timesAll.append(result)
                            timeTot += result_time
                            if timeMin == 0:
                                timeMin = result_time
                            else:
                                timeMin = min(timeMin, result_time)
                            timeMax = max(timeMax, result_time)
                            response = result[2]
                            if response:
                                resp = json.loads(response)
                                total_entities_returned += len(resp["RESOLVED_ENTITIES"])

                        numLines += 1
                        if numLines % INTERVAL == 0:
                            nowTime = time.time()
                            speed = int(INTERVAL / (nowTime - prevTime))
                            print(
                                f"Processed {numLines} searches, {speed} records per second, entities returned {total_entities_returned}: avg[{timeTot/count:.3f}s] tps[{count/(time.time()-beginTime):.3f}/s] min[{timeMin:.3f}s] max[{timeMax:.3f}s]"
                            )
                            prevTime = nowTime
                        if numLines % 100000 == 0:
                            response = g2.get_stats()
                            print(f"\n{response}\n")

                        line = fp.readline()
                        if line:
                            futures[executor.submit(process_line, g2, line, url)] = line

                print(
                    f"Processed total of {numLines} searches, entities returned {total_entities_returned}: avg[{timeTot/count:.3f}s] tps[{count/(time.time()-beginTime):.3f}/s] min[{timeMin:.3f}s] max[{timeMax:.3f}s]"
                )
                timesAll.sort(key=lambda x: x[0], reverse=True)

                i = 0
                while i < count:
                    if timesAll[i][0] <= 1.0:
                        break
                    i += 1
                print(f"Percent under 1s: {(count-i)/count*100:.1f}%")
                print(f"longest: {timesAll[0][0]:.3f}s record[{timesAll[0][1]}]")

                p99 = int(count * 0.01)
                p95 = int(count * 0.05)
                p90 = int(count * 0.10)

                i = 0
                while i < p90:
                    i += 1
                    if i == p99:
                        print(f"p99: {timesAll[i][0]:.3f}s record[{timesAll[i][1]}]")
                    if i == p95:
                        print(f"p95: {timesAll[i][0]:.3f}s record[{timesAll[i][1]}]")
                    if i == p90:
                        print(f"p90: {timesAll[i][0]:.3f}s record[{timesAll[i][1]}]")

                response = g2.get_stats()
                print(response)

            except Exception as err:
                traceback.print_exc()
                print(f"Shutting down due to error: {err}", file=sys.stderr)
                executor.shutdown()
                exit(-1)

except Exception as err:
    traceback.print_exc()
    print(err, file=sys.stderr)
    exit(-1)
