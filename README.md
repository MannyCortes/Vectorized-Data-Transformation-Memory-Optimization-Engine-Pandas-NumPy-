# Scalable Data Ingestion Pipeline

## Overview
A Python based backend pipeline built to safely download, validate, and load unstructured e-commerce datasets into a relational SQLite database. 

The primary problem this solves is handling messy, large scale data without maxing out local memory. Rather than loading massive CSV files all at once and risking a system crash, this pipeline processes data in manageable chunks, strictly validates every row, quarantines bad data, and successfully loads the clean records. 

## Tech Stack
* **Language:** Python  
* **Data Processing:** Pandas, NumPy  
* **Database & ORM:** SQLite, SQLAlchemy  
* **Data Source & Extraction:** Kagglehub API  

## Data Integrity & Error Handling
This system is designed to keep bad data out of the database without interrupting the active ingestion process. Core defensive programming features include:

* **Regex Data Validation:** Before touching the database, specific columns run through a compiled dictionary of Regular Expressions. This ensures strings, dates, and numeric values strictly match the expected schema..  
* **Vectorized Row Masking:** To maximize speed, the pipeline uses NumPy boolean masks to validate data column by column rather than relying on slow, row by row Python loops. If a single column fails the regex check, the entire row is flagged as invalid.  
* **Isolated Quarantine System:** Processing logic physically separates the clean data from the bad. Clean data moves forward to the database, while rejected rows are logged and saved to a localized `quarantined_data.csv` file. This keeps the pipeline running and allows data teams to inspect typos or formatting errors later.  
* **Event Logging:** Python's native logging module captures dataframe creations, regex validation warnings, and database initialization errors, writing them to a silent `pipeline.log` file to keep the active terminal clean.  

## Memory Optimization & Deduplication
To maintain high throughput on local machines with limited RAM, the system utilizes active memory management and incremental database loading.

* **Chunked Ingestion:** The dataset is read and processed in isolated batches of 10,000 rows at a time.  
* **Dynamic Downcasting:** Because Pandas defaults to memory heavy 64-bit data types, the pipeline automatically inspects each column to reduce footprint. It downcasts integers to their smallest possible bit size (using unsigned integers where no negatives exist), compresses floats, and transforms repetitive text columns into highly efficient categorical lookup tables.  
* **Incremental Deduplication:** To prevent SQL injections and primary key conflicts, the pipeline checks incoming batch IDs against the existing database records using NumPy arrays. It acts incrementally, only committing strictly new, unique records to the dimensional tables (Users, Sellers, Products) before appending the final transaction events.  

## Getting Started
The Kaggle API handles the dataset automatically. If you don't have the files, it downloads them; if you do, it seamlessly targets your local cache.  

```bash
# Clone the repository
git clone https://github.com/MannyCortes/kaggle_db
cd kaggle_db

# Set up virtual environment
python3 -m venv venv
source venv/bin/activate # On Windows use: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

#Run Program
python main.py
