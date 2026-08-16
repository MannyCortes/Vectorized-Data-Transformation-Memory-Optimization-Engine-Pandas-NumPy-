import os 
import gc
import datetime as dt
import logging
import numpy  as np
import pandas as pd
regex_schema = {
    # Strict Alphanumeric Constraints
    'user_id': r'^U\d{6}$',             
    'product_id': r'^P\d{5}$',          
    'seller_id': r'^S\d{4}$',           

    'device': r'^(Tablet|Mobile App|Web)$', 
    'payment_method': r'^(UPI|Credit Card|Debit Card|Cash on Delivery)$',
    'delivery_status': r'^(Returned|In Transit|Delayed|Delivered)$',
    'is_returned': r'^(True|False)$',

    #Free Text
    'category': r'^[A-Za-z\s]+$',       #Only letters and spaces, no weird symbols
    'subcategory': r'^[A-Za-z\s]+$', 
    'brand': r'^[A-Za-z0-9\s&]+$',      #Must allow '&' specifically for "H&M"
    'location': r'^[A-Za-z\s]+$',

    #Numerics
    'price': r'^\d+(\.\d{1,2})?$',      # Positive numbers, optional max 2 decimal places
    'discount': r'^\d+(\.\d{1,2})?$',   
    'final_price': r'^\d+(\.\d{1,2})?$',
    'review_count': r'^\d+$',           # Whole integers only
    'stock': r'^\d+$',                  
    'shipping_time_days': r'^\d+$',     

    #Bounded Numerics
    'rating': r'^([0-4](\.\d)?|5(\.0)?)$',       # Strictly limits ratings to 0.0 through 5.0
    'seller_rating': r'^([0-4](\.\d)?|5(\.0)?)$',

    #Dates 
    'purchase_date': r'^\d{4}-\d{2}-\d{2}$'      # Must match YYYY-MM-DD
}
def pandas_df(folder_path):
    folder = os.listdir(folder_path)
    #returns a list of directories in the local folder
    for file_name in folder:
        #grab file names from folder
        if file_name.endswith(".csv"):
            cols = ["user_id", "product_id", "category", "subcategory", 
                    "brand", "price", "discount", "final_price", 
                    "rating", "review_count", "stock", "seller_id", 
                    "seller_rating", "purchase_date", "shipping_time_days", "location", 
                    "device", "payment_method", "is_returned", "delivery_status"]
            #create new file path joining folder+file
            final_path = os.path.join(folder_path, file_name)
            #read the csv file into a pandas dataframe using the specified columns
            df_container = pd.read_csv(final_path, usecols=cols, dtype=str, chunksize=10000)
            logging.info(f"Dataframe created")
    return df_container

def regex_cleaning(df):
    is_valid_mask=np.ones(len(df), dtype=bool)
    for col, pattern in regex_schema.items():
        if col in df.columns:
            valid_col = df[col].str.match(pattern, na=False)
            # is_valid_mask now updates and valid_col is a series of T/F for each row in the column
            is_valid_mask = is_valid_mask & valid_col
        #COPY is needed since pandas creates a view(pointer) of the original dataframe, and if you try to modify it you will get a warning.
    clean_data = df[is_valid_mask].copy()
    quarantined_data = df[~is_valid_mask].copy()
    numeric_columns = [
    'price', 'discount', 'final_price', 'rating', 
    'review_count', 'stock', 'shipping_time_days',
    'seller_rating'
    ]
    del df
    for col in numeric_columns:
        #convert each data type back into their respective types
        if col in clean_data.columns:
            clean_data[col] = pd.to_numeric(clean_data[col])
    print(len(clean_data))
    if len(quarantined_data) > 0:
        logging.warning(f"Quarantined {len(quarantined_data)} rows due to regex validation failure.")
        quarantined_data.to_csv("quarantined_data.csv", date_format=dt.datetime.now(), index=False)
        del quarantined_data
    return clean_data

def optimize_memory(df):
    try:
        columns = df.columns.tolist()
        for col in columns:
            d_type = str(df[col].dtype).lower()
            #if unique/total row is around 50% using 'category' creates a look up table,
            if d_type == "object":
                unique_str = df[col].nunique()
                total_rows = len(df[col])
                if unique_str/total_rows < 0.5:
                    df[col] = df[col].astype('category')
            elif "int" in d_type:
                df_min = df[col].min()
                if df_min >= 0:
                    df[col] = pd.to_numeric(df[col], downcast='unsigned')
                else: df[col] = pd.to_numeric(df[col], downcast='integer')
            elif "float" in d_type:
                df[col]= pd.to_numeric(df[col], downcast='float')
        return df
    except Exception as e:
        logging.error(f"An error occurred during memory optimization: {e}")
