The script to migrate data from Postgres database into Redshift in a single command line

### LICENSE
Author: Vlad Dubovskiy, November 2014, DonorsChoose.org
Special thanks to: David Crane for code snippets on parsing command args
License: Copyright (c) This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 3 of the License, or (at your option) any later version.

### ABOUT THE SCRIPT

1. Connects to Postgres DB and dumps user-defined list of tables or queries into gzipped csv files
2. Ships these files to an AWS S3 bucket via S3 API (chunked, optimized transfer, 1 gzipped file per table)
3. Dumps latest Postgres schema
4. Cleans and edits the schema to match Redshift syntax (according to best practices for optimizing redshift performance)
5. Python script infers and writes in Redshift sortkeys from all existent constraints + support for custom sortkey definitions (sortkeys lead to performance boost)
6. Loads the schema and data into Redshift (restores in temp schema and then swaps complete temp schema for production schema to minimize downtime)
7. Vacuums and Analyzes to compute table stats

### CONFIGURABLE SETTINGS

1. source postgres database
2. target redshift instance
3. set of tables you wish to import (if not all), or custom defined tables (ETL or scrubbed tables)
4. various configurations for redshift import: quotes, escapes, error handling, blanks, empties, delimiter, date formats, nulls, compression
5. define regex to remove any stuff unsupported by Redshift from your schema

### HOW TO RUN THE SCRIPT:

1. Configure p2r_settings.sh first
2. Install any prereqs below
3. chmod u+x *
4. set up a crontab or run: /path/to/p2r_main.sh -h source_db_host_name -p 5432 -U dbuser -d dbname 2>&1 >> /tmp/p2r.log

### PREREQUISITES: 

1. s3cmd (tested on 1.5.0-rc1)
2. Python with re and argparse libraries installed. Tested on python 2.7.8
3. Review sed/perl regex code under "Custom Cleaning" to see if it applies to your schema. You might have to add new replaces for your use case if the schema is not populating in redshift
4. Review parameters of the Redshift copy command to make sure they comply with what you want to happen. Keep in mind, that this specific combo of params successfully handeled all of our cases of dirty data and column types
  
### NOTES:

1. If you are dumping tables from a hot-standby (live) database, then you'll have to pause replication while the dumping takes place. You can bake a command into this script or manage it in your preferred way.
2. The script refreshes data into a temp_schema and once restore is complete, it swaps temp for prod schemas, minimizing refresh downtime to milliseconds
3. You could split this script in two if you prefer to do remote host connection via ssh: http://docs.aws.amazon.com/redshift/latest/dg/loading-data-from-remote-hosts.html

Enjoy,
Vlad from DonorsChoose.org