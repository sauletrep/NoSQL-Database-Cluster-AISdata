CSV_PATH  = r"aisdk-2023-05-01.csv"
MONGO_URI = ("mongodb://localhost:27017/")

RAW_COLL   = "raw_vessels_limited" # Collection to insert raw data
CLEAN_COLL = "clean_vessels" # Collection to insert cleaned data
DB_NAME    = "ais" # database name

CHUNKSIZE  = 50_000
BATCH_SIZE = 1_000

DTYPE_MAP = {
    "Type of mobile": "category", "MMSI": "int64",
    "Latitude": "float64", "Longitude": "float64",
    "Navigational status": "category", "ROT": "float64",
    "SOG": "float64", "COG": "float64", "Heading": "float64",
    "IMO": "string", "Callsign": "string", "Name": "string",
    "Ship type": "category", "Cargo type": "string",
    "Width": "float64", "Length": "float64",
    "Type of position fixing device": "category",
    "Draught": "float64", "Destination": "string",
    "ETA": "string", "Data source type": "category",
    "A": "string", "B": "string", "C": "string", "D": "string",
}

REQ = ["MMSI", "Timestamp", "Latitude", "Longitude"]  # columns that are needed
