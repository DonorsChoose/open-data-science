# coding: utf-8
# Setup
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

import pandas as pd
import boto3

from lib.helpers import subset_df_by_id, resource_formatter, project_formatter, format_current_trends
from lib import TrendFinder as tf
from lib import overview_traces as ot
from lib import demo
from lib import geo as g
from lib import plot_formatters as pf 

# Style for TrendFinder email
style = """
<style>
body {
    font-family: "Georgia", sans-serif;
}

table {
    border-collapse: collapse;
}

th, td {
    padding: 3px;
    text-align: left;
}

table, th, td {
    border: 1px solid black;
    font-family: Futura;
    font-size: 12px;
    font-weight: normal;
}

th {
    background-color: #065331;
    color: white;
}
</style>
"""
# By default, date is today
DATE = date.today().strftime("%Y-%m-%d")
# Hide pandas warnings
pd.options.mode.chained_assignment = None

# Configuration
# AWS initialization
#############################################################
# Credentials need to be set using awscli (see Directions). #
#############################################################
bucket = "donorschoose-trends" # S3 bucket name
client = boto3.client("s3")
s3 = boto3.resource("s3")

# Pipeline wrapper functions
# Overview (does subset_df at a time)
def build_overview(word, subset_df):
    # Counts
    metro_plot = ot.plot_by_metro(subset_df, word, plot=False)
    income_plot = ot.plot_by_income(subset_df, word, plot=False)
    subject_plot = ot.plot_by_subject(subset_df, word, plot=False)
    grade_plot = ot.plot_by_grade(subset_df, word, plot=False)
    
    pf.output_plot_data(word, metro_plot, 'plot_by_metro', DATE, bucket, client)
    pf.output_plot_data(word, income_plot, 'plot_by_income', DATE, bucket, client)
    pf.output_plot_data(word, subject_plot, 'plot_by_subject', DATE, bucket, client)
    pf.output_plot_data(word, grade_plot, 'plot_by_grade', DATE, bucket, client)

    # Proportions
    metro_percent = ot.percent_by_metro(subset_df, word, plot=False)
    income_percent = ot.percent_by_income(subset_df, word, plot=False)
    subject_percent = ot.percent_by_subject(subset_df, word, plot=False)
    grade_percent = ot.percent_by_grade(subset_df, word, plot=False)

    pf.output_plot_data(word, metro_percent, 'percent_by_metro', DATE, bucket, client)
    pf.output_plot_data(word, income_percent, 'percent_by_income', DATE, bucket, client)
    pf.output_plot_data(word, subject_percent, 'percent_by_subject', DATE, bucket, client)
    pf.output_plot_data(word, grade_percent, 'percent_by_grade', DATE, bucket, client)

# Demographics (does all at once, depends on projects and keyword_ids_dict)
def build_demo():
    cor = demo.Correlator(projects)
    cor.find_trends(keywords_dict = keyword_ids_dict)

    # Default time_interval = 1M
    cor.get_categorical_trends(trend_keywords, prop=False, thres=-1)
    # Test stationarity assumptions
    cor.stationarize()
    cor.stationarity_test_all() # what passes this test is in .passed_trends
    # Calculate correlations
    cor.compare_corrs()

    # Get trends that did not pass
    # demo_not_passed = [word for word in trend_keywords if word not in cor.passed_trends]

    features = [col for col in cor.df.columns if 'Bin' in col]

    # Can only investigate trend features for trends that pass tests
    for word in cor.passed_trends:
        # Get list of sorted correlations
        top_corrs = cor.top_corrs(word)
        pf.output_table_data(word, top_corrs, "top_corrs", DATE, bucket, client, index=True)
        # Correlator
        trend_features_out = demo.plot_trend_features(cor.grouped, trend=word, passed_features = cor.passed_features, date_cutoff=trend_finder.current_start, plot=False)
        pf.output_plot_data(word, trend_features_out, 'plot_trend_features', DATE, bucket, client)
        
    for word in trend_keywords:
        # Ratios
        diffs = demo.compare_ratios(cor.df, cor.grouped, trend=word, features=features)
        diffs_out = demo.plot_diffs(diffs, feat_type=['Poverty', 'Metro', 'Grade', 'Various'], plot=False)
        pf.output_plot_data(word, diffs_out, 'plot_diffs', DATE, bucket, client)

        # Google Trends
        google_trends = demo.ggl_trends(cor.grouped, word)
        ggl_trends_out = demo.plot_ggl_trends(google_trends, word, plot=False)
        pf.output_plot_data(word, ggl_trends_out, 'plot_ggl_trends', DATE, bucket, client)

# Geo (does subset_df at a time)
def build_geo(word, subset_df):
    geo = g.GeoMeta(subset_df)
    
    # Build all splits
    geo.get_all_splits()
    # For sorting dropdown of splits
    trendiest = geo.find_trendiest(as_df=True)
    pf.output_table_data(word, trendiest, "geo_splits", DATE, bucket, client, index=True)
    
    # Plot split vs. non-split over time
    plot_splits_out = geo.plot_splits(word, plot=False)
    pf.output_plot_data(word, plot_splits_out, 'plot_splits', DATE, bucket, client)
    
    # Rolling
    windows = [geo.ONE_MONTH, geo.THREE_MONTHS, geo.SIX_MONTHS, geo.ONE_YEAR]
    for window in windows:
        plot_rolling_out = geo.plot_rolling_splits(word, window=window, plot=False)
        pf.output_plot_data(word, plot_rolling_out, 'plot_rolling_splits_{}'.format(window), DATE, bucket, client)
    
    # Cumulative
    plot_cumulative_out = geo.plot_cumulative_splits(word, plot=False)
    pf.output_plot_data(word, plot_cumulative_out, 'plot_cumulative_splits', DATE, bucket, client)


# Detect trends
# Read in resources
#########################################################################################
# Expecting a .csv with Project ID, Project Posted Date, and Item Cleaned Resource Name #
#########################################################################################
resources = resource_formatter("/shared-files/csv/new_resources_only.csv")

# Create TrendFinder object
trend_finder = tf.TrendFinder(resources)
current_trends = trend_finder.find_current_trends()

# Save keywords to list
trend_keywords = list(current_trends["word"])

current_trends_table = format_current_trends(current_trends)

# Transition from resources to file structure
#############################
# Uncomment this if desired #
#############################
# del resources # For memory

# Email trends
email_trends = current_trends_table.to_html(index=False)
body = """
<p>Welcome to TrendFinder! Below are the trending keywords for the last two weeks.<br>

To view the dashboard, <a href='https://trendfinder.elasticbeanstalk.com'>click here!</a>
</p>
<br>
"""

# Create HTML of email
table_html = "<html>" + style + body + table + "</html>"

#############################
# Put email recipients here #
#############################
recipients = ['DC_USER@gmail.com']

# Create message information
msg = MIMEMultipart('alternative')
msg['Subject'] = "TrendFinder Dashboard"
msg['From'] = 'DC_USER@gmail.com'
msg['To'] = ','.join(recipients)

# Add message contents
email_table = MIMEText(table_html, 'html')
msg.attach(email_table)

# Initiate server and send email
################################################
# Fill in email configuration/credentials here #
################################################
server = smtplib.SMTP_SSL('smtp.gmail.com', 465) # SMTP port for sending email
server.login("DC_USER", "PASSWORD") # Fill this in
server.sendmail(
  "DC_USER@gmail.com", # Put in origin email
  recipients,
  msg.as_string())
server.quit()

# Save trends
pf.output_table_data(trend=None, df=current_trends_table, table_name=None, prefix=DATE, bucket=bucket, s3_client=client, index=False)

# Build keyword-IDs dictionary
# Get dictionary of Project IDs per keyword
keyword_ids_dict = {}

for word in trend_keywords:
    # DataFrame subset for low income
    keyword_ids_dict[word] = trend_finder.subset_resources_by_query(word)["Project ID"].tolist()

# Investigate trends
# Read in project info
#########################################
# Expecting a .csv with project_columns #
#########################################
projects = project_formatter("/shared-files/csv/new_project_info.csv")

# Co-occurrences
# Find co-occurrences
co_occurrences_dict = {}

for word in trend_keywords:
    co_occurrences_dict[word] = pd.DataFrame(trend_finder.find_co_occurrences(word), columns = ["Word", "Count"])
    pf.output_table_data(word, co_occurrences_dict[word], "co_occurrences", DATE, bucket, client, index=True)

# Plot XoX
# Overall trend history
for word in trend_keywords:
    plot_xox_out = trend_finder.plot_xox(word, plot = False)
    pf.output_plot_data(word, plot_xox_out, 'plot_xox', DATE, bucket, client)

# Demo
build_demo()

# Overview/Geo
for word in trend_keywords:
    # Get subset of projects for word
    subset_df = subset_df_by_id(projects, keyword_ids_dict[word])
    # Overview
    build_overview(word, subset_df)
    # Geo
    build_geo(word, subset_df)

print("TrendFinder done!")