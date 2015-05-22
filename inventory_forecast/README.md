Inventory Forecast
==============

What's this about?
--------------

This is a sample forecasting script accompanying this blog post: http://data.donorschoose.org/data-science-pipeline. The script uses both Python and R (calls R within Python using rpy2) to forecast inventory for a year into the future. Our data is provided so that you can attempt the forecasting yourself, but the script also includes steps for data downloads and uploads from an Amazon Redshift database in case you wanted to set up something similar.

Outline
--------------

1. Run 'create_table_one_time.sql' first to create the table in DB
2. Alter 'inventory_query.sql' to query a date column and a value column from your DB
3. Change API parameters at the bottom of 'inventory_forecast.py'
4. Set up a crontab for 'inventory_forecast.py' to run on a scheduled basis