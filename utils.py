from constants import *

import pymongo
import matplotlib.pyplot as plt
import csv
import os, time, math
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from pymongo import MongoClient
from tqdm import tqdm

def get_client():
    return MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

# Task 2
def stream_csv(row_cap: int | None):
    rows_read = 0
    for chunk in pd.read_csv(
        CSV_PATH,
        dtype=DTYPE_MAP,
        parse_dates=["# Timestamp"],
        chunksize=CHUNKSIZE,
    ):
        chunk = (
            chunk.rename(columns={"# Timestamp": "Timestamp"})
                 .drop(columns=["A", "B", "C", "D"])
                 .dropna(subset=REQ)
        )
        if row_cap:
            if rows_read >= row_cap:
                break
            allowed = row_cap - rows_read
            chunk   = chunk.head(allowed)
        rows_read += len(chunk)
        yield chunk

def insert_worker(docs, coll_name):
    client = get_client()
    coll   = client[DB_NAME][coll_name]
    # split into 1k-doc bulks
    for s in range(0, len(docs), BATCH_SIZE):
        coll.insert_many(docs[s:s+BATCH_SIZE], ordered=False)

def load_raw_parallel(threads, row_cap):
    client = get_client()
    client[DB_NAME][RAW_COLL].drop()
    client[DB_NAME][RAW_COLL].create_index("MMSI")

    start = time.time()
    total = 0

    with ThreadPoolExecutor(max_workers=threads) as tp:
        futures = []
        for chunk in stream_csv(row_cap):
            docs = chunk.to_dict("records")
            total += len(docs)
            futures.append(tp.submit(insert_worker, docs, RAW_COLL))
        # wait for all workers
        for f in tqdm(as_completed(futures), total=len(futures), desc="Inserting"):
            f.result()

    elapsed = time.time() - start
    print(f"RAW ► Inserted {total:,} docs in {elapsed:,.1f}s "
          f"({total/elapsed:,.0f} docs/s)")

# Task 3
def vessel_counts():
    """one-pass counter (single thread)"""
    counter = Counter()
    for chunk in pd.read_csv(CSV_PATH, usecols=["MMSI"], chunksize=CHUNKSIZE):
        counter.update(chunk["MMSI"])
    return {m for m, c in counter.items() if c >= 100}

def filter_worker(slice_ids, good_mmsi):
    client = get_client()
    src = client[DB_NAME][RAW_COLL]
    dest = client[DB_NAME][CLEAN_COLL]

    bulk = []

    for _id in slice_ids:
        doc = src.find_one({"_id": _id})
        if not doc:
            continue

        # Ensure MMSI is comparable
        try:
            mmsi = int(doc["MMSI"])
        except (KeyError, ValueError, TypeError):
            continue  # skip invalid or missing MMSI

        if mmsi not in good_mmsi:
            continue

        # Check for valid lat/lon
        try:
            lat = float(doc["Latitude"])
            lon = float(doc["Longitude"])
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
        except (KeyError, ValueError, TypeError):
            continue

        required_fields = ["Timestamp", "SOG", "COG"]
        if any(f not in doc or doc[f] is None for f in required_fields):
            continue

        bulk.append(doc)

    # Insert into clean collection if any valid docs
    if bulk:
        dest.insert_many(bulk, ordered=False)
        print(f"[✔] Inserted {len(bulk)} clean docs")
    else:
        print("[⚠] No valid docs in this slice")


def build_clean_parallel(threads):
    client   = get_client()
    raw_coll = client[DB_NAME][RAW_COLL]
    clean    = client[DB_NAME][CLEAN_COLL]
    clean.drop()
    clean.create_index("MMSI")
    clean.create_index("Timestamp")

    good_mmsi = vessel_counts()
    print(f"{len(good_mmsi):,} vessels have ≥ 100 pts")

    # get all _ids so we can shard them
    all_ids = list(raw_coll.find({}, {"_id": 1}))
    slice_size = math.ceil(len(all_ids)/threads)
    id_slices  = [ [d["_id"] for d in all_ids[i:i+slice_size]]
                   for i in range(0, len(all_ids), slice_size)]

    start = time.time()
    with ThreadPoolExecutor(max_workers=threads) as tp:
        futures = [tp.submit(filter_worker, ids, good_mmsi) for ids in id_slices]
        for _ in tqdm(as_completed(futures), total=len(futures), desc="Filtering"):
            pass
    elapsed = time.time() - start
    print(f"CLEAN ► Inserted {clean.count_documents({}):,} docs "
          f"in {elapsed:,.1f}s")

# Task 4
def read_clean_parallel(threads=4):
    client = get_client()
    coll = client[DB_NAME][CLEAN_COLL]

    # Step 1: Get all _ids
    all_ids = list(coll.find({}, {"_id": 1}))
    all_ids = [doc["_id"] for doc in all_ids]
    print(f"📦 Loading all {len(all_ids):,} documents from clean collection...")

    # Step 2: Split IDs across threads
    chunk_size = math.ceil(len(all_ids) / threads)
    id_chunks = [all_ids[i:i + chunk_size] for i in range(0, len(all_ids), chunk_size)]

    # Step 3: Worker function
    def reader_worker(ids):
        client = get_client()
        coll = client[DB_NAME][CLEAN_COLL]
        return list(coll.find({"_id": {"$in": ids}}))

    # Step 4: Run in parallel
    docs = []
    with ThreadPoolExecutor(max_workers=threads) as tp:
        futures = [tp.submit(reader_worker, chunk) for chunk in id_chunks]
        for f in tqdm(as_completed(futures), total=len(futures), desc="Loading clean data"):
            docs.extend(f.result())

    # Step 5: Build and sort DataFrame
    df = pd.DataFrame(docs)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    df = df.sort_values(by=['MMSI', 'Timestamp'])

    print(f"✅ Loaded {len(df)} rows from clean collection.")
    return df

# Calculate delta t in milliseconds between subsequent data points per vessel.
def calculate_delta_t(df):
    delta_t_list = []

    print("Calculating delta t per vessel...")
    for mmsi, group in tqdm(df.groupby('MMSI')):
        group = group.sort_values('Timestamp')
        deltas = group['Timestamp'].diff().dropna()
        delta_ms = deltas.dt.total_seconds() * 1000  # Convert to ms
        delta_t_list.extend(delta_ms.tolist())

    return delta_t_list

# Generate and save histogram of delta t values.
def plot_histogram(delta_t_list, output_path="output/delta_t_histogram.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.hist(delta_t_list, bins=100, color='skyblue', edgecolor='black')
    plt.title("Histogram of Delta t (ms) Between Vessel Data Points")
    plt.xlabel("Delta t (ms)")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.show()

# Return summary of deltas
def analyze_deltas(delta_t_list,  output_path="output/delta_summaries.csv"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    total = len(delta_t_list)
    mean = sum(delta_t_list) / total
    min_val = min(delta_t_list)
    max_val = max(delta_t_list)

    # Print results
    print(f"Total delta t entries: {total}")
    print(f"Mean delta t: {mean:.2f} ms")
    print(f"Min delta t: {min_val:.2f} ms")
    print(f"Max delta t: {max_val:.2f} ms")

    # Save to CSV
    summary = [
        ["Metric", "Value (ms)"],
        ["Total delta t entries", total],
        ["Mean delta t", f"{mean:.2f}"],
        ["Min delta t", f"{min_val:.2f}"],
        ["Max delta t", f"{max_val:.2f}"]
    ]

    with open(output_path, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(summary)

    print(f"Summary saved to {output_path}")

# Generate and save histogram of logged delta t values (logging is needed for visualisation because of outliers)
def plot_histogram_log(delta_t_list, output_path="output/log_delta.png"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    plt.figure(figsize=(10, 6))
    plt.hist(delta_t_list, bins=100, color='skyblue', edgecolor='black', log=True)
    plt.title("Histogram of Delta t (ms) [Log Scale]")
    plt.xlabel("Delta t (ms)")
    plt.ylabel("Log(Frequency)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.show()


# Print vessels with delta t above the threshold (1e6 = 16.7 min).
def find_vessels_with_large_deltas(df, threshold_ms=1e6):
    print(f"\n🔎 Vessels with delta t > {threshold_ms:,} ms:")

    outlier_vessels = []

    for mmsi, group in df.groupby('MMSI'):
        group = group.sort_values('Timestamp')
        deltas = group['Timestamp'].diff().dt.total_seconds() * 1000  # convert to ms
        large_deltas = deltas[deltas > threshold_ms]

        if not large_deltas.empty:
            outlier_vessels.append(mmsi)

    print(f"\n Total vessels with large gaps: {len(outlier_vessels)}")
    return outlier_vessels


