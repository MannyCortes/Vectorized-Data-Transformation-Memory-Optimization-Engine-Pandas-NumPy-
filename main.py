import kagglehub
import logging 
import os
from dotenv import load_dotenv
import data_pipeline
import db_sub
#loads local env fille into local disk/memory OS
load_dotenv()
logging.basicConfig(filename="pipeline.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
# recourse https://github.com/Kaggle/kagglehub/blob/main/README.md#download-dataset
#look for dataset downloader
#downloads dataset, if no download needed returns the local folder path
def main():
    try:
        path = kagglehub.dataset_download("sharmajicoder/amazon-e-commerce")
        #return a pandas df
        engine = db_sub.initialize_db()
        df_container = data_pipeline.pandas_df(path)
        for chunk in df_container:
            df = data_pipeline.regex_cleaning(chunk)
            df = data_pipeline.optimize_memory(df)
            db_sub.load_data_to_db(engine, df)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
if __name__ == "__main__":
    main()