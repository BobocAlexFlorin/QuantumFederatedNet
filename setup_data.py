import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, LabelEncoder
from sklearn.decomposition import PCA
import sys
import os
import requests
import gzip
import shutil

# CONFIGURATION
SAMPLE_SIZE = 2000 
NUM_CLIENTS = 2
CSV_FILENAME = "atlas-higgs-challenge-2014-v2.csv"
# Direct link to the CERN Open Data Portal file (Gzipped)
DATA_URL = "http://opendata.cern.ch/record/328/files/atlas-higgs-challenge-2014-v2.csv.gz"

def download_and_extract():
    """Downloads the dataset from CERN if it doesn't exist."""
    if os.path.exists(CSV_FILENAME):
        print(f"[DATA ENGINEER] ✅ Dataset '{CSV_FILENAME}' found locally.")
        return

    print(f"[DATA ENGINEER] ⬇️  Downloading dataset from CERN ({DATA_URL})...")
    print("                 (This may take a minute...)")
    
    try:
        # 1. Download the .gz file
        response = requests.get(DATA_URL, stream=True)
        if response.status_code == 200:
            with open("temp_data.csv.gz", 'wb') as f:
                f.write(response.content)
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            sys.exit(1)

        # 2. Decompress it
        print("[DATA ENGINEER] 📦 Decompressing GZIP...")
        with gzip.open("temp_data.csv.gz", 'rb') as f_in:
            with open(CSV_FILENAME, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # 3. Cleanup
        os.remove("temp_data.csv.gz")
        print("[DATA ENGINEER] ✅ Download & Extraction Complete.")

    except Exception as e:
        print(f"❌ Download Failed: {e}")
        sys.exit(1)

def process_higgs_data():
    # --- STEP 0: ENSURE DATA EXISTS ---
    download_and_extract()

    print(f"[DATA ENGINEER] 🧹 Loading ATLAS Higgs Dataset...")
    
    try:
        df = pd.read_csv(CSV_FILENAME)
    except Exception as e:
        print(f"❌ Read Error: {e}")
        sys.exit(1)

    # 1. CLEANING
    print("[DATA ENGINEER] 🏷️  Encoding Labels (s -> 1, b -> -1)...")
    le = LabelEncoder()
    # Handle column name variations
    label_col = 'Label' if 'Label' in df.columns else df.columns[-1]
    
    df[label_col] = le.fit_transform(df[label_col]) 
    y = 2 * df[label_col].values - 1 

    # Drop non-physics columns
    drop_cols = ['EventId', 'Weight', 'Label', 'KaggleSet', 'KaggleWeight']
    cols_to_drop = [c for c in drop_cols if c in df.columns]
    X_raw = df.drop(columns=cols_to_drop).values

    # Handle missing values
    X_raw[X_raw == -999.0] = 0

    # 2. SAMPLING
    indices = np.random.choice(len(X_raw), size=min(SAMPLE_SIZE, len(X_raw)), replace=False)
    X_sample = X_raw[indices]
    y_sample = y[indices]

    # 3. DIMENSIONALITY REDUCTION
    print(f"[DATA ENGINEER] 📉 Performing PCA (30 features -> 2 features)...")
    pca = PCA(n_components=2)
    X_pca = pca.fit_transform(X_sample)

    # 4. NORMALIZATION
    print("[DATA ENGINEER] ⚖️  Scaling features to [0, 1]...")
    scaler = MinMaxScaler()
    X_scaled = scaler.fit_transform(X_pca)

    # 5. DISTRIBUTE
    print(f"[DATA ENGINEER] 📦 Splitting data for {NUM_CLIENTS} clients...")
    X_splits = np.array_split(X_scaled, NUM_CLIENTS)
    y_splits = np.array_split(y_sample, NUM_CLIENTS)

    for i in range(NUM_CLIENTS):
        filename = f"client_data_{i}.npz"
        np.savez(filename, X=X_splits[i], y=y_splits[i])

    print("[DATA ENGINEER] ✅ Data Preparation Complete.\n")

if __name__ == "__main__":
    process_higgs_data()
