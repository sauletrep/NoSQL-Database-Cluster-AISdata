# Filter out noise from a given dataset using NoSQL databases and perform data analysis. 
## Dataset: vessel information. 
## Task: appply various filters to eliminate noise and calculate the time difference between data points for each vessel.

# Import necessary libraries
import pandas as pd

# ----- Task 1: Create a NoSQL Database Cluster -----
def data(file_path):
    '''Function to read data and infer dtypes, then load full dataset.'''
    # Step 1: Read a small sample with Pandas to infer dtypes since collumns have mixed data types and many NaNs
    infersample_df = pd.read_csv(file_path, nrows=1000) # Read first 1000 rows 
    inferred_dtypes = infersample_df.dtypes.astype(str).to_dict() # Infer dtypes from small sample data

    # Step 2: Load the sample data with inferred dtypes
    sample_df = pd.read_csv(file_path, nrows=10000, dtype=inferred_dtypes) # Read first 10,000 rows with inferred dtypes
    sample_df.columns = sample_df.columns.str.strip("# ") # Remove trailing whitespaces and "#" from column names

    # Step 3: Load full dataset with panda using inferred dtypes
    df = pd.read_csv(file_path, dtype=inferred_dtypes) # Read full dataset with inferred dtypes
    df.columns = df.columns.str.strip("# ") 
    
    # Show column names 
    print("Column Names:") 
    print(df.columns)

    # A small preview of data
    print("\nData Preview:")
    print(df.head())
    
    return df, sample_df

# Path to locally stored dataset
file_path = "aisdk-2023-05-01.csv"

# Download and preview data, both full and sample
full_data, sample_data = data(file_path)

df = sample_data # for now use sample data for testing

# Save as JSON (line-delimited format)
df.to_json("ais_clean.json", orient="records", lines=True)

# ----- Task 2: Data Insertion in Parallel -----

# ----- Task 3: Data Noise Filtering in Parallel -----

# ----- Task 4: Calculation of Delta t and Histogram Generation -----

# ----- end of code -----
