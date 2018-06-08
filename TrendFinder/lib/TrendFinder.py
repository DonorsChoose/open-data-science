# Python 3
import string
import math
import datetime
import time
import itertools
import warnings
from collections import defaultdict, Counter

import pandas as pd
import numpy as np
from nltk.corpus import stopwords
import plotly

from lib import plot_formatters as pf

stoplist = stopwords.words("english")
stoplist = stoplist + ['nan']
translator = str.maketrans("", "", string.punctuation)

date_col = "Project Posted Date"
id_col = "Project ID"

def format_text(df, text_col):
    """Turning text into list of (unique) words."""
    print("Reducing strings to list of unique words...")
    # Faster to cast to list
    temp_list = df[text_col].tolist()
    temp_list = [set(x) for x in temp_list]
    df["cleaned"] = temp_list
    
    # Delete original for memory
    del df[text_col], temp_list

    return df

def get_freq_dict(df):
    """Get frequency table of all words."""
    print("Building frequency dictionary...")
    corpus = list(itertools.chain.from_iterable(df["cleaned"].tolist()))
    freq_dict = Counter(corpus)
    
    print("Frequency dictionary built!")
    return freq_dict

def subset_date_range(df, min_date, max_date):
    """Helper function to subset DataFrame by date."""
    df = df[(df[date_col] >= min_date) & (df[date_col] < max_date)]
    return df

def convert_group_to_lists(grouped, stopwords = []):
    """Convert cleaned words in grouped DataFrame to list of lists."""
    list_by_time = []
    for key_df in [key_df for key, key_df in grouped]:
        time_list = key_df["cleaned"].tolist()
        # Flatten list
        time_list = list(itertools.chain.from_iterable(time_list))
        list_by_time.append(time_list)
    
    return list_by_time

class TrendFinder:
    """Class for trend identification from text and time data."""
    def __init__(self, df, text_col = "Cleaned Item Name", cleaned = False,
                 subset_by_date = False, min_date = "2008-01-01", max_date = "2018-01-01"):
        """
        Args:
            df (pandas DataFrame): DataFrame containing at least an ID, date,
                and text column for projects.
            text (str): Name of column for detecting trending words out of.
        """
        print("Cleaning...")
        self.text_col = text_col
        # Only need subset for TrendFinder
        self.df = df[[id_col, date_col, self.text_col]]
        # Convert to datetime to enable subsetting by time
        print("Performing date operations...")
        self.df[date_col] = pd.to_datetime(self.df[date_col])
        if subset_by_date:
            self.min_date = min_date
            self.max_date = max_date
            self.df = subset_date_range(self.df, self.min_date, self.max_date)
        # Clean
        self.df.dropna(axis=0, how="any", inplace=True)
        self.df = format_text(self.df, self.text_col)
        print("Cleaning done!")
    
    def find_historical_trends(self, filter_threshold = "", time_interval = "1M"):
        """
        Find historical trends in DataFrame passed to TrendFinder (default
        range is the ten years of 2008-2018).
        """
        t0 = time.time()
        
        # Automatically set threshold at word needs to be present in 0.1% of
        # all projects in order to be considered relevant.
        if len(filter_threshold) == 0:
            filter_threshold = math.floor(.001 * len(self.df))
            
        # Get words above the filter threshold
        freq_dict = get_freq_dict(self.df)
        words_left = [k for k, v in freq_dict.items() if v >= filter_threshold]
        # Remove stopwords from consideration
        words_left = [word for word in words_left if word not in stoplist]
        # Remove numbers from considation
        words_left = [word for word in words_left if word.isdigit() is False]
        # Filter "words" that are 1 character
        words_left = [word for word in words_left if len(word) > 1]
        
        print("Total words: "+str(len(words_left)))
        print("")
        
        # Grouper time_interval options
        # http://pandas.pydata.org/pandas-docs/stable/timeseries.html#offset-aliases
        print("Creating groups for iteration...")
        # Group DataFrame by time
        grouped = self.df.groupby(pd.Grouper(key=date_col, freq=time_interval))
        # Get number of projects for each time frame (to divide later)
        projects_xox = np.array(grouped.size().fillna(0).values, dtype=float)
        # Get DataFrame values for text column by time interval for faster iteration
        list_by_time = convert_group_to_lists(grouped)

        print("Calculating word proportions...")
        # Get list of Counters for each time frame
        counter_list = []
        
        for x in list_by_time:
            counter = Counter(x)
            counter = {word: counter[word] for word in words_left}
            counter_list.append(counter)
        
        # Combine dictionaries to get list of counts by time frame per word
        all_counts_dict = defaultdict(list)

        for d in counter_list:
            for k, v in d.items():
                all_counts_dict[k].append(v)

        # Divide by projects_xox to get proportion over time
        all_props_dict = {k: (v / projects_xox) for k, v in all_counts_dict.items()}

        # Get ranges of each word and add to a master list of tuples
        range_list = []

        for word in words_left:
            props = all_props_dict[word]
            prop_range = max(props) - min(props)
            range_list.append((word, prop_range))

        word_props = pd.DataFrame(range_list)
        # Format DataFrame and sort for presentation
        word_props.columns = ["word", "prop_range"]
        word_props = word_props.sort_values("prop_range", ascending=False)
        print("Word proportion ranges calculated!")
        print("")
        
        print("Time elapsed: "+str((time.time() - t0) / 60)+" minutes.")
        return word_props

    def find_current_trends(self, current_start = "", filter_threshold = "", days_back = 14, groups = 50, sd_multiple = 2):
        """
        Find trends in the present, returning a DataFrame sorting words by
        a weighted combination of overall relevance and current trendiness.
        """
        t0 = time.time()
        
        # Automatically set current period to be 2 weeks back from the last
        # date contained in the DataFrame
        if len(current_start) == 0:
            last_day = self.df[date_col].max()
            current_start = last_day - datetime.timedelta(days_back)
            current_start = current_start.date()
        print("Looking at projects from "+str(current_start)+" to "+str(last_day.date())+".")
        
        # Save in case wanted for plots, etc.
        self.current_start = current_start.strftime("%Y-%m-%d")
        # Split into before and after
        history = self.df[self.df[date_col] <= current_start]
        current = self.df[self.df[date_col] > current_start]
        # Save as class attribute for future use
        self.current = current
        
        current_count = len(current) # Number of projects in current time frame
        print("There are "+str(current_count)+" projects in the current time frame.")

        # i.e. if this current range is too high
        if current_count / len(history) > .02:
            warnings.warn("Abnormally large number of projects in current time period. Please consider adding a manual exception or trying an alternative date range or number of days back (days_back argument). Setting groups at 30 to enable functioning trend detection.")
            groups = 30
        print("")
        
        # Automatically set threshold at word needs to be present in 0.1% of
        # all projects in order to be considered relevant.
        if len(filter_threshold) == 0:
            # At an average at 10k projects per 2 weeks (2016 onwards), this effectives makes the minimum count ~50
            filter_threshold = math.floor(.005 * current_count)

        # Get words above the filter threshold
        freq_dict = get_freq_dict(current)
        words_left = [k for k, v in freq_dict.items() if v >= filter_threshold]
        # Remove stopwords from consideration
        words_left = [word for word in words_left if word not in stoplist]
        # Remove numbers from considation
        words_left = [word for word in words_left if word.isdigit() is False]
        # Filter "words" that are 1 character
        words_left = [word for word in words_left if len(word) > 1]
        
        print("Total words: "+str(len(words_left)))
        print("")

        print("Creating groups for iteration...")
        # Group DataFrame by day (want to go day-by-day backwards)
        grouped = history.groupby(pd.Grouper(key=date_col, freq="D"))
        # Reverse these arrays because we're going backwards in time
        # Get number of projects for each time frame (to divide later)
        projects_xox = np.array(grouped.size().fillna(0).values, dtype=float)[::-1]
        # Get DataFrame values for text column by time interval for faster iteration
        list_by_time = convert_group_to_lists(grouped)[::-1]

        print("Building history...")
        # Go backwards in time, adding each day at a time until the period's count
        # is equal to or greater than the current time frame's number of projects
        history_index = 0 # Starting index of history data
        history_groups = [] # Initialize list of lists for groups of texts
        history_groups_index = 0 # To keep track of current group for while loop
        history_groups_counts = [] # Initialize list of lists for number of projects in each group

        # Build history
        while history_groups_index < groups:
            # Add new group for new period of time in the past
            history_groups.append([])
            # For number of projects in group
            group_count = 0
            # Add to group until it matches the count of the current period
            while group_count < current_count:
                # Update list of lists of text
                history_groups[history_groups_index].append(list_by_time[history_index])
                # Update group count
                group_count += projects_xox[history_index]
                # Next x from xox
                history_index += 1
            # Flatten group list
            history_groups[history_groups_index] = list(itertools.chain.from_iterable(history_groups[history_groups_index]))
            # Add size of group to another list for later divison after group is done
            history_groups_counts.append(group_count)
            # Next group
            history_groups_index += 1

        history_groups_counts = np.array(history_groups_counts)
        
        # Get use history_groups_index as number of days to comprise history for printout
        print("Looking "+str(history_index)+" days back to test against current time frame.")
        print("")
                               
        # Create list of Counters for history
        counter_list = []

        for x in history_groups:
            counter = Counter(x)
            counter = {word: counter[word] for word in words_left}
            counter_list.append(counter)

        # Combine dictionaries to get list of counts by time frame per word
        all_counts_dict = defaultdict(list)

        for d in counter_list:
            for k, v in d.items():
                all_counts_dict[k].append(v)

        # Divide by projects_xox to get proportion over time
        all_props_dict = {k: (v / history_groups_counts) for k, v in all_counts_dict.items()}

        # Find mean, standard deviation of props for each word
        mean_sd_dict = {}

        for word in words_left:
            props = all_props_dict[word]
            mean_sd_dict[word] = (props.mean(), props.std())

        # Calculate proportion in current period
        current_text = list(itertools.chain.from_iterable(current["cleaned"].tolist()))
        current_counter = Counter(current_text)

        current_props_dict = {word: current_counter[word] / current_count for word in words_left}

        # Find deviation from mean in current period
        deviation_dict = {word: abs(current_props_dict[word] - mean_sd_dict[word][0]) for word in words_left}
        
        # Return sorted DataFrame of outliers
        rows = []

        for word in words_left:
            # Define outlier based on mean + number of SDs
            if deviation_dict[word] > sd_multiple * mean_sd_dict[word][1]:
                rows.append((word, current_props_dict[word], mean_sd_dict[word][0], mean_sd_dict[word][1], deviation_dict[word]))

        # Create DataFrame and sort by ratio difference of current deviation
        # (i.e. how many times larger is the current deviation)
        outlier_df = pd.DataFrame(rows, columns = ["word", "prop", "historical_mean", "historical_sd", "deviation"])
        # outlier_df["sd_difference"] = outlier_df["deviation"] - outlier_df["historical_sd"]
        outlier_df["sd_difference_ratio"] = outlier_df["deviation"] / outlier_df["historical_sd"]
        # Weighting scheme for sorting...
        # Current mean (i.e. how big it is, for relevance) * SD difference ratio (i.e. how abnormal is this right now)
        outlier_df["weight"] = outlier_df["prop"] * outlier_df["sd_difference_ratio"]
        outlier_df = outlier_df.sort_values("weight", ascending=False).reset_index(drop=True).reset_index().rename(columns={"index":"Rank"})
        # (Add 1 to index to start at 1)
        outlier_df["Rank"] = outlier_df["Rank"] + 1

        print(str(len(rows)) + " keywords deviate more than 2 SDs above their normal mean.")
        print("")

        print("Time elapsed: "+str((time.time() - t0) / 60)+" minutes.")
        return outlier_df

    def plot_xox(self, word, time_interval = "1M", prop = True, plot = True):
        """Simple plotter function for seeing change in word over time."""
        # Get total number of projects per time period
        projects_xox = self.df.groupby(pd.Grouper(key=date_col, freq=time_interval)).size()
        # Get subset of word to operate on
        word_subset = self.df[self.df["cleaned"].apply(lambda x: word in x)]
        word_xox = word_subset.groupby(pd.Grouper(key=date_col, freq=time_interval)).size()

        to_plot = pd.DataFrame()
        to_plot['prop'] = word_xox / projects_xox
        to_plot['counts'] = word_xox

        plot_config = {'kwargs': {'prop': prop}, 'df': to_plot}
        if not plot:
            return plot_config

        fig = pf.plot_xox(df=to_plot, trend=word, prop=prop)
        plotly.offline.iplot(fig, filename='xox')
            
    def subset_resources_by_query(self, query, current = False):
        """
        Get subset of resources DataFrame based on query.
        
        Designed to accept single keyword queries by default to remain consistent
        with the output of find_{}_trends() results, but could check string for any
        match by specifying from_list = False.
        """                    
        if current:
            return self.current[self.current["cleaned"].apply(lambda x: query in x)]
        else:
            return self.df[self.df["cleaned"].apply(lambda x: query in x)]
        
    def find_co_occurrences(self, query, top_n = 10, remove_stopwords = True, current = True):
        """Get top co-occurring words with a query from resources."""
        subset = self.subset_resources_by_query(query, current = current)
        flattened_resources = itertools.chain.from_iterable(subset["cleaned"].tolist())
        counter = Counter(flattened_resources)
        # Remove numbers
        counter = Counter({word: counter[word] for word in counter.keys() if not word.isdigit()})
        if remove_stopwords:
            counter = Counter({word: counter[word] for word in counter.keys() if word not in stoplist})
        
        return counter.most_common(top_n)
