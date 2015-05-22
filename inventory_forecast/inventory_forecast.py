#!/usr/bin/python
__author__ = 'Thomas Vo, DonorsChoose.org'

# sample forecasting script for blog post using both Python and R

import dataset
import numpy as np
import pandas as pd
import rpy2.robjects as ro
from math import factorial

# smoothing function (source = http://wiki.scipy.org/Cookbook/SavitzkyGolay)
def smoothing(y, window_size, order, deriv = 0, rate = 1):
    
    order_range = range(order + 1)
    half_window = (window_size -1) // 2
    
    b = np.mat([[k ** i for i in order_range] for k in range(-half_window, half_window + 1)])
    m = np.linalg.pinv(b).A[deriv] * rate ** deriv * factorial(deriv)
    
    firstvals = y[0] - np.abs( y[1:half_window + 1][::-1] - y[0] )
    lastvals = y[-1] + np.abs(y[-half_window - 1:-1][::-1] - y[-1])
    y = np.concatenate((firstvals, y, lastvals))
    
    return np.convolve(m[::-1], y, mode = 'valid')

# connects to DB, runs SQL query, returns dataframe
def download_data(api_url, query_filename, colname_date, colname_value):

    # load the query
    with open(query_filename, 'r') as query_file:
        sql_query = query_file.read()

    # connect to the database
    db_connect = dataset.connect(url = api_url, reflectMetadata = False)

    # run the query
    query_results = db_connect.query(sql_query)

    # load query results into dataframe
    new_df = pd.DataFrame()
    for row in query_results:
        new_df = new_df.append({
            colname_date: row[colname_date],
            colname_value: row[colname_value]
        }, ignore_index = True)

    return new_df

# didn't want to deal with February 29ths
def drop_leap(df, colname_date):

    leap_indices = []

    for i in range(df.shape[0]):
        if (df.ix[i, colname_date].month == 2) & (df.ix[i, colname_date].day == 29):
            leap_indices.append(i)

    df = df.drop(df.index[leap_indices])
    df.reset_index(drop = True, inplace = True)

    return df

# provide a df with date and value column to forecast
def forecast(df, r_filename, r_function, colname_date, colname_value, years_to_forecast = 1):

    # only predict in increments of years, simplifies things
    days_to_forecast = years_to_forecast * 365

    # load the R script
    with open(r_filename, 'r') as r_file:
        r_script = r_file.read()

    # sending an R function into Python
    ro.r(r_script)
    r_function = ro.globalenv[r_function]

    # running the R function inside of Python, can only interpret lists
    vec = r_function(list(df[colname_value]), log_vec = True, forecast_units = days_to_forecast)

    # smooth the vector
    vec = smoothing(y = np.array(vec), window_size = 51, order = 3)

    # only keep the predicted values
    vec = vec[::-1][:days_to_forecast][::-1]

    # add new dates and values
    for i in range(years_to_forecast):

        # make new_df with 365 days into the future
        new_df = df[(df.shape[0] - 365):].copy()
        new_df.reset_index(drop = True, inplace = True)
        new_df.loc[:, colname_date] = pd.DatetimeIndex(new_df.loc[:, colname_date]) + pd.DateOffset(years = 1)
        new_df.loc[:, colname_value] = vec[((i) * 365):((i + 1) * 365)]

        # merge new_df back to df
        df = pd.concat([df, new_df])
        df.reset_index(drop = True, inplace = True)

    return df

def upload_data(api_url, df, tablename, colname_date, colname_value):

    # connect to the database
    db_connect = dataset.connect(url = api_url, reflectMetadata = False)

    # assuming the user has write access, remove the entries uploaded from the previous run
    db_connect.query('DELETE FROM ' + tablename + ';')

    # insert rows
    table = db_connect.load_table(tablename)
    rows = [{colname_date: c1, colname_value: c2} for c1, c2 in zip(df[colname_date], df[colname_value])]
    table.insert_many(rows)

if __name__ == '__main__':

    # parameters that need to be specified
    your_api_url = 'your_username:your_password.your_instance_name.redshift.amazonaws.com'
    your_query_filename = 'inventory_query.sql'
    your_tablename = 'inventory_forecast'
    your_colname_date = 'date_of_interest'
    your_colname_value = 'project_count'
    your_r_filename = 'forecast.r'
    your_r_function = 'forecast_vec'

    temp_df = download_data(
        api_url = your_api_url, 
        query_filename = your_query_filename,
        colname_date = your_colname_date,
        colname_value = your_colname_value)

    temp_df = drop_leap(
        df = temp_df,
        colname_date = your_colname_date)

    temp_df = forecast(
        df = temp_df,
        r_filename = your_r_filename,
        r_function = your_r_function,
        colname_date = your_colname_date,
        colname_value = your_colname_value,
        years_to_forecast = 1)

    upload_data(
        api_url = your_api_url,
        df = temp_df,
        tablename = your_tablename,
        colname_date = your_colname_date,
        colname_value = your_colname_value)