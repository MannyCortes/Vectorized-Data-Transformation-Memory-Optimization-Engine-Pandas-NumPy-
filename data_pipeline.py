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
            #where keeps whatever returns true and replaces false with None
            logging.info(f"Dataframe created")
    return df_container

def regex_cleaning(df):
    #create a bool mask and start all True
    #use numpy array for vectorized operations/ data structure is 1D, each row is T/F 
    #accepts length of the dataframe and creates a boolean array of the same length
    #np.ones creates a memory block of 1s,meaning true
    is_valid_mask=np.ones(len(df), dtype=bool)
    # PANDAS NOTES, masking using boolean logic, and using & oopperand to create a copy of the data frame
    #utilizes dict to pair column names and regex patterns
    for col, pattern in regex_schema.items():
        if col in df.columns:
        #using pandas&regex allows for column by column checking rather than python looping through every row
            valid_col = df[col].str.match(pattern, na=False)
            #once a row in the mask is false it will remain false, if a single col is false the whole row is false
            # is_valid_mask now updates and valid_col is a series of T/F for each row in the column
            is_valid_mask = is_valid_mask & valid_col
        #if a single col contains false the  whole row is false.
        #COPY is needed since pandas creates a view(pointer) of the original dataframe, and if you try to modify it you will get a warning.
        #the mask is in a numpy array format, needs to convert to df
    clean_data = df[is_valid_mask].copy()
    quarantined_data = df[~is_valid_mask].copy()
    numeric_columns = [
    'price', 'discount', 'final_price', 'rating', 
    'review_count', 'stock', 'shipping_time_days',
    'seller_rating'
    ]
    del df
    gc.collect()  # Force garbage collection to free up memory
    for col in numeric_columns:
        #convert each data type back into their respective types
        if col in clean_data.columns:
            clean_data[col] = pd.to_numeric(clean_data[col])
    print(len(clean_data))
    if len(quarantined_data) > 0:
        logging.warning(f"Quarantined {len(quarantined_data)} rows due to regex validation failure.")
        quarantined_data.to_csv("quarantined_data.csv", date_format=dt.datetime.now(), index=False)
        del quarantined_data
        gc.collect()
    return clean_data

def optimize_memory(df):
    #pandas defaults to 64bit/8byte data types, its best to downsize for optimization
    # int/bit 8 = 256 or -128 to 127. every bit doubles from the previous one 
    #example 4 bits goes 1, 2, 4, 8 and can represent 0-15 meaning 16 total
    try:
        columns = df.columns.tolist()
        for col in columns:
            d_type = str(df[col].dtype).lower()
            #strings/object data types use 64 bit pointers to point to the string in memory
            #if unique/total row is around 50% using 'category' creates a look up table,
            # the with an integer-key, the integer is storedon the table rather than a pointer  
            if d_type == "object":
                #counts unique strings
                unique_str = df[col].nunique()
                #how many rows foreach column
                total_rows = len(df[col])
                if unique_str/total_rows < 0.5:
                    df[col] = df[col].astype('category')
            #pandas has several int tpes
            elif "int" in d_type:
                df_min = df[col].min()
                # if no negatives in the column we can use 
                if df_min >= 0:
                    #pandas calculates the needed int size
                    # to_numeric creates a replica column with adjusted downcast, the headers(pointers) points to the new column
                    #since pandas likes to group all the same data types together, it will move the new column to the front of mathing "blocks" called BLOCK managr
                    df[col] = pd.to_numeric(df[col], downcast='unsigned')
                else: df[col] = pd.to_numeric(df[col], downcast='integer')
            elif "float" in d_type:
                df[col]= pd.to_numeric(df[col], downcast='float')
        return df
    except Exception as e:
        logging.error(f"An error occurred during memory optimization: {e}")
