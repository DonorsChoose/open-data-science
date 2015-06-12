#!/bin/sh

### LICENSE
  # Author: Vlad Dubovskiy, November 2014. 
  # License: Copyright (c) This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.

# Export $PATH to work with crontab if you need to, example:
# export PATH="/bin/s3cmd-1.5.0-rc1:/usr/local/pgsql/bin"

# SOURCE DB (Postgres) - params are passed as attributes from the command line, see script usage section in README.md
# TARGET DB (Redshift)
RSHOST=your_instance_name.redshift.amazonaws.com
RSHOSTPORT=5439
RSADMIN=your_superuser
RSNAME=your_db_name
RSKEY=redshift_api_key
RSSECRET=redshift_api_secret
RSUSER=your_user_name # name of the non-superuser! who will get read/write access to your schemas and tables. It's critical that you create this user that is not sudo to avoid concurrent connection limits
RSSCHEMA=public # target schema on your redshift cluster. You could change this, but public is the default schema.
DBSCHEMA=public # source schema on your postgres DB. Public is default
TMPSCHEMA=temp_refresh
# DIRECTORIES
PGSQL_BIN=path_to_your_pgsql_bin # your postgres bin directory. Tested with psql 9.3.1
PYTHONBIN=path_to_your_python_bin # location of your python 2.7.8 executable. Other python version will likely work as well. We install anaconda distribution. Quick and easy
SCRPTDIR=path_to_your_script_directory
DATADIR=path_to_where_to_dump_db_tables # a place to store table dumps. Make sure it's larger than all the DB tables of interest
S3BUCKET=name_of_s3_bucket # S3 bucket to which your machine has API read/write privileges to. Must install s3cmd and configure it
# LOGGING
STDERR=/tmp/p2r.err
STDOUT=/tmp/p2r.out
LOCKFILE=/tmp/p2r.lock
# EMAIL NOTIFICATION
RECIPIENT='you@yoursite.com'
SENDER='system@yoursite.com'
SUBJECT='Redshift Refresh Failures'

# do not add views or functions to redshift. These are actual names of tables in your Postgres database
TABLES='table1 table2 table3 table4 table5
		table6 table7'

# Custom Tables [CT] (some tables are huge due to text data, so you can define custom SQL to either munge your tables or only select certain columns for migration)
# The names of the variables must match actual tables names in the schema. Order commands inside CTSQL list and table names inside CTNAMES list so the indexes of the list match.
# Custom tables must have all the same columns as defined in schema, or you'll have to define a dummy table in your DB or adjust python schema part of the script to accomdate your new table structures
  # If you are just dropping columns (like me), then fill them in with something

## declare an array variable
declare -a CTSQL=("SELECT id, NULL AS text_data  FROM table8" \
                "SELECT id, NULL AS more_text_data FROM table9")
CTNAMES=( table8 table9 )

