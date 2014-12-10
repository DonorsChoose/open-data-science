#!/usr/bin/python
__author__ = 'Vlad Dubovskiy, DonorsChoose.org'

# Takes raw or cleaned up schema, infers sortkeys from all constraints, assigns manual sortkeys and inferred sortkeys to tables, exports as a new schema file.
# Usage: python p2r_add_sortkeys.py -i db_schema_clean.sql -o db_schema_final.sql

import re
import argparse

########################################
#           Setup Globals
########################################
# They are passed through command line arguments. Keeping here for reference
#input_filename = 'db_schema_clean.sql'
#output_filename = 'db_schema_final.sql'
#raw_schema_flag = False # we cleaned up the file with some regex in p2r_main.sh before sending it to python. 
						# You might have to do the same, as this flag doesn't handle all cases (ex: CHECK constraints will stay in the final file, which you don't want)

########################################
#       Define custom sorkeys
########################################

# These are sortkeys added on top of existent constraints in the database. It's a good practice to add sortkeys to columns by which you filter a lot, like dates
# By default, no manualkeys are set up. Format: manualkeys = {'table1': 'col1', 'table1': 'col2', 'table2': 'col1'}
manualkeys = {}

def add_sortkeys(input_filename, output_filename, raw_schema_flag=False):

	with open(input_filename) as input_file:
		lines = input_file.readlines()

	text = ' '.join(lines)

	# Building automatic table:sortkey dict from existent constraints
	alter_pattern = r'ALTER TABLE[^;]*(?=PRIMARY KEY|FOREIGN KEY|UNIQUE).*'
	alter_statements = re.findall(alter_pattern, text)
	autokeys={}
	for con in alter_statements:
		line = con.split('\n')
		if raw_schema_flag is True:
			t = re.findall(r'ALTER TABLE ONLY(.*?)$', line[0])
		else: t = re.findall(r'ALTER TABLE(.*?)$', line[0])
		c = re.findall(r'FOREIGN KEY \((.*?)\)|PRIMARY KEY \((.*?)\)|UNIQUE \((.*?)\)', line[1])
		# remove tuples, empties created by regex trying to match all alternatives
		vals = []
		for x in list(c[0]):
			if len(x) > 0:
				vals.append(x)
		# check if a table was already added to the dict
		table = t[0].strip()
		if table not in autokeys:
			autokeys[table] = []
			autokeys[table].append(','.join(vals))
		else:
			autokeys[table].append(','.join(vals))

	# remove duplicate and merged values from autokeys for each table
	for key, value in autokeys.iteritems():
		autokeys[key] = list(set([x.strip() for x in ','.join(value).split(',')]))

	# append manual keys to autokeys before populating tables with sortkeys:
	for key, value in manualkeys.iteritems():
	    autokeys[key].append(value)

	# Let's keep all the tables that are not needing the sortkeys
	# Build a list of all tables in the schema and then ensure they are being printed out in the for loop
	table_name = r'CREATE TABLE(.*?)\('
	# remove any whitespaces
	tables = [t.strip() for t in re.findall(table_name, text)]

	output_file = open(output_filename, 'w')

	# loop through all tables
	for table in tables:
		pattern = '(CREATE TABLE '+table+'\s[^;]*)'
		# if it needs a sortkey
		if table in autokeys.keys():
			columns = autokeys[table]
			match = re.findall(pattern, text)
			block = re.sub(pattern, match[0]+' sortkey(%s)'+';', match[0]) %(', '.join(columns))
			output_file.write('\n\n %s' % block)
		else:
			output_file.write('\n\n %s' % re.findall(pattern, text)[0]+';')
	
	output_file.write('\n\n')
	input_file.close()
	output_file.close()

if __name__ == "__main__":

	parser = argparse.ArgumentParser(description='This script adds sortkeys to postgres schema dump')
	parser.add_argument('-i','--input', help='Input file name', required=True)
	parser.add_argument('-o','--output',help='Output file name', required=True)
	args = parser.parse_args()
	add_sortkeys(args.input, args.output)
