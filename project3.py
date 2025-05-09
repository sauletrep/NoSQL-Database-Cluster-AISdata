# Filter out noise from a given dataset using NoSQL databases and perform data analysis.
## Dataset: vessel information.
## Task: apply various filters to eliminate noise and calculate the time difference between data points for each vessel.

# Import necessary libraries
from utils import *

# ----- Task 1: Create a NoSQL Database Cluster -----


# ----- Task 2: Data Insertion in Parallel -----

# This function inserts data in parallel into the RAW_COLL collection.
load_raw_parallel(threads = os.cpu_count(), row_cap = 1000000)


# ----- Task 3: Data Noise Filtering in Parallel -----

# This function reads the data from RAW_COLL in parallel -> filters out noisy vessels -> inserts into CLEAN_COLL
build_clean_parallel(os.cpu_count())


# ----- Task 4: Calculation of Delta t and Histogram Generation -----

# Just reads the data in parallel (similar to Task 3)
df = read_clean_parallel(threads=os.cpu_count())

# Calculates delta t for all vessels
delta_t_list = calculate_delta_t(df)

# plots histograms
plot_histogram(delta_t_list)
plot_histogram_log(delta_t_list)

# Summaries
analyze_deltas(delta_t_list)
find_vessels_with_large_deltas(df)

