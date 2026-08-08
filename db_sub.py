from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import numpy as np
import logging 
import pandas as pd
import gc

Base = declarative_base()

#when designing a table seperate the nouns and verb/events.
class user(Base): 
    __tablename__ = 'users'
    user_id = Column(String, primary_key=True, unique=True)

class seller(Base):
    __tablename__ = 'sellers'
    seller_id = Column(String, primary_key=True, unique=True)

class product(Base):
    __tablename__ = 'products'
    product_id = Column(String, primary_key=True, unique=True)
    category = Column(String)
    subcategory = Column(String)
    brand = Column(String)

class transaction(Base):
    __tablename__ = 'transactions'
    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('users.user_id'))
    product_id = Column(String, ForeignKey('products.product_id'))
    seller_id = Column(String, ForeignKey('sellers.seller_id'))
    seller_rating = Column(Float)
    payment_method = Column(String)
    device = Column(String)
    location = Column(String)
    price = Column(Float)
    discount = Column(Float)
    final_price = Column(Float)
    rating = Column(Float)
    review_count = Column(Integer)
    stock = Column(Integer)
    shipping_time_days = Column(Integer)
    is_returned = Column(Boolean)
    delivery_status = Column(String)
    purchase_date = Column(DateTime)





def load_data_to_db(engine, df):
        #use conditionals to prevent injections
    with engine.begin() as connection:
        #check if alues already in list
        try:
            # INCREMENTAL DATA LOADER, deduplication
            sql_map = {"users": "user_id", "products": "product_id", "sellers": "seller_id"}
            for key, val in sql_map.items():
                #create a mask to filter out values
                batch_numpy = df[val].unique()
                #batch numpy is turned into an array of unique values from the dataframe for the current column being processed
                sql_query = f"SELECT {val} FROM {key}"
                query_df = pd.read_sql_query(sql_query, connection)
                #np.is in checks every element in the batch and checks df values
                #unique_df then becomes a boolean array matching the shape of our batch_numpy
                #numpy array and t/f values 
                #query_df[val] turns into a 1d array of vals
                unique_df = np.isin(batch_numpy, query_df[val])
                #new_id is still a numpy array holding the unique ids filtered from the mask
                #applies mask to return values not in the db
                new_ids = batch_numpy[~unique_df]
                if len(new_ids) > 0:
                    if key == "products":
                        product_cols = ["product_id", "category", "subcategory", "brand"]
                        #rows to  keep  and columns to keep  drop  duplicates
                        insert_df = df.loc[df['product_id'].isin(new_ids), product_cols].drop_duplicates(subset=['product_id'])
                        insert_df.to_sql(name=key, con=connection, if_exists='append', index=False)
                    else:
                        #{} formats the data so that the frame has a header
                        insert_df = pd.DataFrame({val: new_ids})
                        insert_df.to_sql(name=key, con=connection, if_exists='append', index=False)
                del unique_df, query_df, batch_numpy, new_ids
                gc.collect()
                #inject in loop to check if values already exist       
        #users table, 2 brackets indicates keep the table as a 2D 
        #inner brackets indicates a python list of columns to select outter tells python to filter using that list
            df[['user_id', 'product_id', 'seller_id', 'payment_method', 'purchase_date', 'price', 'discount', 'final_price', 'rating', 'review_count', 'stock', 'shipping_time_days', 'is_returned', 'delivery_status', 'location', 'device', 'seller_rating']].to_sql(name='transactions', con=connection, if_exists='append', index=False)
        except SQLAlchemyError as e:
            logging.error(f"Error loading data to database: {e}")
        del df
        gc.collect()
    

def initialize_db():
    try:
        engine = create_engine('sqlite:///kaggle_amz_db.db')
        #Base.metadata creates the tables and relationships rather than pds
        Base.metadata.create_all(engine)
        logging.info("Database initialized successfully.")
        return engine
    except SQLAlchemyError as e:
        logging.error(f"Error initializing database: {e}")