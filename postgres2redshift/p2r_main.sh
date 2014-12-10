#!/bin/sh

# Load settings, tables file
source /path_to_scripts/p2r_settings.sh


########################################
#           Data Dump: Params
########################################

# Open lock file sentinal protection
# This section parses command line arguments when you execute the script with /path/to/p2r_main.sh -h source_db_host_name -p 5432 -U dbuser -d dbname 2>&1 >> /tmp/p2r.log

if [ ! -e $LOCKFILE ]; then
  echo "***********************************"
  echo $$ >$LOCKFILE

PROGNAME=`basename $0`

usage ()
{
  echo "usage:  $PROGNAME [-h hostname] [-n] -d dbname -p dbhostport -U username -f filename" >&2
  echo "        -d dbname      (name of postgres database)" >&2
  echo "        -U dbuser      (name of database schema owner)" >&2
  echo "        -h dbhost      (name of database host server)" >&2
  echo "        -p dbhostport  (number of database host port)" >&2
}

DBHOST=''
DBNAME=''
DBOWNER=''
DBHOSTPORT=''

# Break up command-line options for easy parsing.  Reorders legal
# options in front of --, and all others after.  Note that the
# 2-steps with "$@" is essential to preserve multi-word optargs.
GETOPT=`getopt -n $PROGNAME -o h:d:U:f:T:p:n -- "$@"`
if [ $? != 0 ] ; then usage ; rm $LOCKFILE; exit 1 ; fi
eval set -- "$GETOPT"

while true
do
  case "$1" in
    -\?) usage 2>&1; rm $LOCKFILE; exit 0 ;;
    -h) DBHOST="$2"; shift 2;;
    -d) DBNAME="$2"; shift 2;;
    -U) DBOWNER="$2"; shift 2;;
    -p) DBHOSTPORT="$2"; shift 2;;
    --) shift ; break ;;
    * ) echo "Internal error!" >&2; rm $LOCKFILE; exit 1 ;;
  esac
done

# Script invoked with extra command-line args?
if [ $# -ne "0" ]
then
  echo "$PROGNAME: unrecognized parameter -- $*" >&2
  echo >&2
  usage
  rm $LOCKFILE
  exit 2
fi

# Script invoked without required parameters?
if [ -z "$DBNAME" -o -z "$DBOWNER" ]
then
  REQUIRED=''
  if [ -z "$DBNAME" ] ;    then REQUIRED="$REQUIRED -d"; fi
  if [ -z "$DBOWNER" ] ;    then REQUIRED="$REQUIRED -U"; fi
  echo "$PROGNAME: missing required parameter(s) --" $REQUIRED >&2
  echo >&2
  usage
  rm $LOCKFILE
  exit 3
fi

# Close lock file sentinal protection. 
# If you are dumping from hot standby replication server, you can wrap the code here and move removing lockfile right before SHIPPPING TABLES TO S3
# This is here for your convenience, it's not a requirement to have this.
  rm $LOCKFILE
else
  echo "  +------------------------------------"
  echo -n "  | "
  date
  echo "  | critical-section is already running"
  echo "  +------------------------------------"
fi

########################################
#           Begin Data Dump
########################################

echo DUMPING TABLES
date

# dumping original tables
for table in $TABLES
do
  $PGSQL_BIN/psql -h $DBHOST -p $DBHOSTPORT -U $DBOWNER -d $DBNAME -c \
    "\copy ${table} TO STDOUT (FORMAT csv, DELIMITER '|', HEADER 0)" \
    | gzip > $DATADIR/${table}.txt.gz
done

# dumping custom tables
for (( i = 0 ; i < ${#CTSQL[@]} ; i++ )) 
do
  $PGSQL_BIN/psql -h $DBHOST -p $DBHOSTPORT -U $DBOWNER -d $DBNAME -c \
    "\copy ( ${CTSQL[$i]} ) TO STDOUT (FORMAT csv, DELIMITER '|', HEADER 0)" \
    | gzip > $DATADIR/${CTNAMES[$i]}.txt.gz
done

echo DUMPING TABLES COMPLETE
date

########################################
#          SHIP TABLES TO S3
########################################

echo SHIP TO S3
date

# ship original tables
for table in $TABLES
do
  s3cmd put $DATADIR/${table}.txt.gz s3://$S3BUCKET/ --force 1>>$STDOUT 2>>$STDERR
done

# ship custom tables
for table in ${CTNAMES[@]}
do
  s3cmd put $DATADIR/${table}.txt.gz s3://$S3BUCKET/ --force 1>>$STDOUT 2>>$STDERR
done

echo SHIP TO S3 COMPLETE
date


########################################
#       Get and clean schema
########################################

echo GET/CLEAN/UPLOAD DB SCHEMA
date

# remove any schema* files from the directory
rm -rf $SCRPTDIR/schema*

# Dump DB's schema
$PGSQL_BIN/pg_dump -h $DBHOST -p $DBHOSTPORT -U $DBOWNER --schema-only --schema=$DBSCHEMA $DBNAME > $SCRPTDIR/schema.sql

##### 1. Cleanup the schema to conform to RedShift syntax

## Only keep CREATE TABLE statements
sed -n '/CREATE TABLE/,/);/p' $SCRPTDIR/schema.sql > $SCRPTDIR/schema_clean.sql
## Append ALTER TABLE statements
sed -n '/ALTER TABLE/,/;/p' $SCRPTDIR/schema.sql >> $SCRPTDIR/schema_clean.sql

## Cleanup ALTER TABLE statements
# Only keep PRIMARY KEYS, FOREIGN KEYS and UNIQUE. Current regex requires that the ALTER TABLE statement spaces two lines
# http://unix.stackexchange.com/questions/26284/how-can-i-use-sed-to-replace-a-multi-line-string
# http://stackoverflow.com/questions/6361312/negative-regex-for-perl-string-pattern-match
perl -0777 -i -pe 's/ALTER TABLE(?!UNIQUE|PRIMARY|FOREIGN).*;//g' $SCRPTDIR/schema_clean.sql
# Remove ONLY statement that is not supported
perl -0777 -i -pe 's/ALTER TABLE ONLY/ALTER TABLE/g' $SCRPTDIR/schema_clean.sql
# Remove CHECK CONSTRAINTS that Redshift doesn't support, along with last comma
perl -0777 -i -pe 's/,\n(\s*CONSTRAINT.*\n)*(?=\)\;)//g' $SCRPTDIR/schema_clean.sql
# Remove iterators on columns
sed -i.bak 's/DEFAULT nextval.*/NOT NULL,/g' $SCRPTDIR/schema_clean.sql
# Remove system DB tables
sed -i.bak '/CREATE TABLE dba_snapshot*/,/);/d' $SCRPTDIR/schema_clean.sql
sed -i.bak '/CREATE TABLE jbpm*/,/);/d' $SCRPTDIR/schema_clean.sql
sed -i.bak '/ALTER TABLE jbpm*/,/;/d' $SCRPTDIR/schema_clean.sql
# Remove unsupported commands and types (json, numeric(45))
sed -i.bak 's/ON DELETE CASCADE//g' $SCRPTDIR/schema_clean.sql
sed -i.bak 's/ON UPDATE CASCADE//g' $SCRPTDIR/schema_clean.sql
sed -i.bak 's/SET default.*//g' $SCRPTDIR/schema_clean.sql
sed -i.bak 's/numeric(45/numeric(37/g' $SCRPTDIR/schema_clean.sql
sed -i.bak 's/json NOT NULL/text NOT NULL/g' $SCRPTDIR/schema_clean.sql
# Replace columns named "open" with "open_date", as "open" is a reserved word. Other Redshift reserved words: time, user
sed -i.bak 's/open character/open_date character/g' $SCRPTDIR/schema_clean.sql
# Custom Cleaning (add any regex to clean out other edge cases if your schema fails to build in Redshift)
sed -i.bak '/CREATE TABLE your_table_name*/,/);/d' $SCRPTDIR/schema_clean.sql

##### 2. Add sortkeys to table definitions (python script)

$PYTHONBIN $SCRPTDIR/p2r_add_sortkeys.py -i $SCRPTDIR/schema_clean.sql -o $SCRPTDIR/schema_final.sql

# take a nap for 30 seconds while python script completes (there are better approaches in notes)
sleep 30

##### 3. Add ALTER TABLE statements back to the final schema file

sed -n '/ALTER TABLE/,/;/p' $SCRPTDIR/schema_clean.sql >> $SCRPTDIR/schema_final.sql

##### 4. Restore data into a new schema, instead of nuking current schema

# add search_path to temp_schema
sed -i "1 i SET search_path TO ${TMPSCHEMA};" $SCRPTDIR/schema_final.sql

echo CREATE NEW TEMP SCHEMA
$PGSQL_BIN/psql -h $RSHOST -p $RSHOSTPORT -U $RSADMIN -d $RSNAME -c \
  "CREATE SCHEMA $TMPSCHEMA;
  SET search_path TO $TMPSCHEMA;
  GRANT ALL ON SCHEMA $TMPSCHEMA TO $RSUSER;
  GRANT USAGE ON SCHEMA $TMPSCHEMA TO $RSUSER;
  GRANT SELECT ON ALL TABLES IN SCHEMA $TMPSCHEMA TO $RSUSER;
  COMMENT ON SCHEMA $TMPSCHEMA IS 'temporary refresh schema';" 1>>$STDOUT 2>>$STDERR

##### 5. Load schema file into TMPSCHEMA

$PGSQL_BIN/psql -h $RSHOST -p $RSHOSTPORT -U $RSADMIN -d $RSNAME -f $SCRPTDIR/schema_final.sql 1>>$STDOUT 2>>$STDERR


########################################
#        Restore in Redshift
########################################


echo START RESTORE TABLES IN REDSHIFT
date

# Copy a table into Redshift from S3 file:
  # To test without the data load, add NOLOAD to the copy command. 
  # CSV cannot be used with FIXEDWIDTH, REMOVEQUOTES, or ESCAPE.
  # Remove MAXERROR from production. Analysize /tmp/p2r.err for error log
  # NULLify empties: BLANKSASNULL, EMPTYASNULL. See Error management notes below before adding.

# restore original tables
for table in $TABLES
do
  $PGSQL_BIN/psql -h $RSHOST -p $RSHOSTPORT -U $RSADMIN -d $RSNAME -c \
    "SET search_path TO $TMPSCHEMA;
    copy ${table} from 's3://$S3BUCKET/${table}.txt.gz' \
      CREDENTIALS 'aws_access_key_id=$RSKEY;aws_secret_access_key=$RSSECRET' \
      CSV DELIMITER '|' IGNOREHEADER 0 ACCEPTINVCHARS TRUNCATECOLUMNS GZIP TRIMBLANKS DATEFORMAT 'auto' ACCEPTANYDATE COMPUPDATE ON MAXERROR 100000;" 1>>$STDOUT 2>>$STDERR
done

# restore custom tables
for table in ${CTNAMES[@]}
do
  $PGSQL_BIN/psql -h $RSHOST -p $RSHOSTPORT -U $RSADMIN -d $RSNAME -c \
    "SET search_path TO $TMPSCHEMA;
    copy ${table} from 's3://$S3BUCKET/${table}.txt.gz' \
      CREDENTIALS 'aws_access_key_id=$RSKEY;aws_secret_access_key=$RSSECRET' \
      CSV DELIMITER '|' IGNOREHEADER 0 ACCEPTINVCHARS TRUNCATECOLUMNS GZIP TRIMBLANKS DATEFORMAT 'auto' ACCEPTANYDATE COMPUPDATE ON MAXERROR 100000;" 1>>$STDOUT 2>>$STDERR
done

# Swap temp_schema for production schema
echo DROP $RSSCHEMA AND RENAME $TMPSCHEMA SCHEMA TO $RSSCHEMA
$PGSQL_BIN/psql -h $RSHOST -p $RSHOSTPORT -U $RSADMIN -d $RSNAME -c \
  "SET search_path TO $RSSCHEMA;
  DROP SCHEMA IF EXISTS $RSSCHEMA CASCADE;
  ALTER SCHEMA $TMPSCHEMA RENAME TO $RSSCHEMA;
  GRANT ALL ON SCHEMA $RSSCHEMA TO $RSUSER;
  GRANT USAGE ON SCHEMA $RSSCHEMA TO $RSUSER;
  GRANT SELECT ON ALL TABLES IN SCHEMA $RSSCHEMA TO $RSUSER;
  COMMENT ON SCHEMA $RSSCHEMA IS 'analytics data schema';" 1>>$STDOUT 2>>$STDERR

echo RESTORE TABLES COMPLETE
date

echo START VACUUM ANALYZE 

$PGSQL_BIN/psql -h $RSHOST -p $RSHOSTPORT -U $RSADMIN -d $RSNAME -c "vacuum; analyze;" 1>>$STDOUT 2>>$STDERR

echo BULK REFRESH COMPLETE

date
echo "***********************************"


########################################
#        COPY Error Management
########################################

# NOT NULL condition violated in the presence BLANKSASNULL or EMPTYASNULL COPY option:
  # solution: replace empties and blanks in tables, drop COPY options or adjust schema definition. 
    # went with dropping COPY options for now (despite the fact that I'd love to have NULLs over empties)

# table.columnx has a wrong date format error:
  # solution: DATEFORMAT 'auto' ACCEPTANYDATE options, which NULLs any unrecognized date formats

# Query to check errors in redshift
  # select starttime, filename, line_number, colname, position, raw_line, raw_field_value, err_code, err_reason 
  # from stl_load_errors
  # where filename like ('%table_name%')
  # order by starttime DESC
  # limit 110;

########################################
#        Future Improvements
########################################

  # replace wait with proper PIDs: http://stackoverflow.com/questions/356100/how-to-wait-in-bash-for-several-subprocesses-to-finish-and-return-exit-code-0
  # Iterative refresh: incremental inserts (say, every hour) instead of dumping the entire schema or individual tables. Remember to vacuum; analyze; afterwards
