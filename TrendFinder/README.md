# TrendFinder

A collection of trend detection and analysis tools and modules designed to work in tandem to generate a BI dashboard for monitoring trends in real-time on DonorsChoose.org's platform. These tools can operate on any given subset of data (e.g. by subject, metro area, etc.) and also have the ability to detect and analyze trends that have occurred in the past.

The overall pipeline is comprised of a number of core capabilities:

### Trend Detection
* Real-time (e.g. What are the biggest trends in Math over the last 10 years?) - by default, trends occurring the past 2 weeks
* Historical (i.e. What is currently trending on our platform?)

### Trend analysis
* Overview: Getting a high-level overview of trend over time and demographic breakdown
* Context: Providing top keyword co-occurrences
* Demography: Uncovering interesting correlations and anomalies with demographic variables
* Geography: Understanding geographic origin and spread

Currently, the pipeline is designed to run on a biweekly basis, but these default options are easily configurable.