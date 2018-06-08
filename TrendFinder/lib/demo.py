import re

import pandas as pd
import numpy as np

import plotly
import plotly.graph_objs as go
from statsmodels.tsa.stattools import adfuller
from pytrends.request import TrendReq

from lib import plot_formatters as pf

class Correlator(object):
    def __init__(self, df, start_date="2008-01-01", end_date="2019-01-01"):
        self.df = df
        self.clean(start_date=start_date, end_date=end_date)
        self.binarize()

    def clean(self, start_date="2008-01-01", end_date="2018-01-01"):
        self.date = "Project Posted Date"
        self.df.index = self.df['Project ID']
        # Already subsetting by date beforehand
        # self.df[self.date] = pd.to_datetime(self.df[self.date])
        # self.df = self.df[self.df[self.date] >= start_date]
        # self.df = self.df[self.df[self.date] < end_date]

    def find_trends(self, list_of_keywords=None, keywords_dict=None, field=None):
        """
        Creates a column for each with 1 where project contains kw, 0 where it doesn't.

        There are 2 ways to run this. One is by passing keywords_dict, example:
        
        keywords_dict = {
            'keyword1': ['6a489c20bf07b894506537074dcab819', 'a743d5cd4987948143909885237e17d0'],
            'keyword2': ['0b893ca4e303bff5c5a7d586ec16ac8a', 'be094cd5887b94a9a018817601f60d95']
                    }

        The second way is to pass a list_of_keywords. This will find the trends
        within this class - useful if you don't want to rely on TrendFinder.
        """
        if list_of_keywords:
            self.df = self.df.dropna(subset=[field])
            for kw in list_of_keywords:
                self.df[kw] = 0
                self.df.loc[self.df[field].str.contains(kw), kw] = 1
        else:
            for kw, id_list in keywords_dict.items():
                # Note we only take those keys that are within the time range.
                id_list = [id_key for id_key in id_list if id_key in self.df.index]
                self.df[kw] = 0
                self.df.loc[id_list, kw] = 1

    def custom_binarize_fields(self):
        """
        Together with binarize_field below, creates binary features from categorical features.
        This was done in 2 different functions because I wanted to specify which would be 1 vs. 0 
        for some of them.
        """
        self.df['Bin_Poverty(low income)'] = self.df['School Poverty Level']
        self.df['Ord_Grade_Level'] = self.df['Project Grade Level']
        self.df['Bin_Charter(Yes)'] = self.df['School Is Charter (Yes / No)']
        self.df['Bin_KIPP(Yes)'] = self.df['School Is KIPP (Yes / No)']
        self.df['Bin_NLNS(Yes)'] = self.df['School Is NLNS (Yes / No)']
        self.df['Bin_Magnet(Yes)'] = self.df['School Is Magnet (Yes / No)']
        self.df['Bin_Year_Round(Yes)'] = self.df['School Is Year Round (Yes / No)']
        
        cleanup_nums = {
                    "Bin_Poverty(low income)": {
                            "low income": 1, 
                            "upper income": 0
                            },
                    "Ord_Grade_Level": {
                            "Grades PreK-2": 1, 
                            "Grades 3-5": 2, 
                            "Grades 6-8": 3, 
                            "Grades 9-12": 4
                            },
                    "Bin_Charter(Yes)": {
                            "Yes": 1, 
                            "No": 0
                            },
                    "Bin_KIPP(Yes)": {
                            "Yes": 1, 
                            "No": 0
                            },
                    "Bin_Magnet(Yes)": {
                            "Yes": 1, 
                            "No": 0
                            },
                    "Bin_NLNS(Yes)": {
                            "Yes": 1, 
                            "No": 0
                            },
                    "Bin_Year_Round(Yes)": {
                            "Yes": 1, 
                            "No": 0
                            }
                }
        self.df.replace(cleanup_nums, inplace=True)
        return self.df

    def binarize_field(self, field):
        """
        See docstring above in custom_binarize_field
        """
        newfield = field + '_copy'
        self.df[newfield] = self.df[field]
        self.df[newfield] = self.df[field].fillna('n/a')
        options = self.df[newfield].unique()
        for option in options:
            self.df['Bin_' + field + '(' + option + ')'] = 0
            self.df.loc[self.df[newfield]==option, 'Bin_' + field + '(' + option + ')'] = 1
        return self.df

    def binarize(self):
        """
        Calls the 2 binarizing functions above, for each feature in projects dataset.
        """
        list_of_categorical_fields = ['Project Grade Level', 'School Metro Area', 'Project Subject', 'Project Subject Category']

        for field in list_of_categorical_fields:
            self.df = self.binarize_field(field)

        self.df = self.custom_binarize_fields()
        self.df = self.df.drop(columns=['Bin_Project Grade Level(n/a)', 'Bin_School Metro Area(n/a)'], errors='ignore')

    def desired_trend(self, desired_col, time_interval="1Y", prop=True, thres=0):
        """
        Currently not used, see get_categorical_trends instead
        """
        # doing this first to remove data with too few entries
        tmp_grouped = self.df.groupby(pd.Grouper(key=self.date, freq=time_interval))[desired_col].sum().astype(float).to_frame()
        tmp_grouped_index = tmp_grouped[tmp_grouped[desired_col]>thres].index
        
        if prop:
            
            nom = self.df.groupby(pd.Grouper(key=self.date, freq=time_interval))[desired_col].sum()
            denom = self.df.groupby(pd.Grouper(key=self.date, freq=time_interval)).size()
            
            grouped = pd.DataFrame((nom / denom).astype(float)).rename(columns={0: desired_col})
            grouped = grouped.loc[tmp_grouped_index]

        else:
            grouped = self.df.groupby(pd.Grouper(key=self.date, freq=time_interval))[desired_col].sum().astype(float).to_frame()
            grouped = grouped.loc[tmp_grouped_index]
            
        return grouped
    
    def get_categorical_trends(self, desired_cols, time_interval='1m', prop=False, thres=0):
        """
        Creates grouped df from original df, based on time grouper
        """
        print('Computing trends')
        bin_cols = [col for col in self.df.columns if 'Bin' in col]
        # ord_cols = [col for col in self.df.columns if 'Ord' in col]
        if prop:
            grouped = self.df.groupby(pd.Grouper(key='Project Posted Date', freq=time_interval))[desired_cols + bin_cols].mean()
        else:
            grouped = self.df.groupby(pd.Grouper(key='Project Posted Date', freq=time_interval))[desired_cols + bin_cols].sum()
                # tmp_mask = ~pd.isnull(grouped[desired_col])

        self.grouped = grouped
        print('Done!')
        return grouped
    
    def stationarize(self, yearly_seasonality=None):
        """
        Stationarizes grouped df. Takes first differences, and removes yearly seasonality if param is passed
        """
        diff_grouped = pd.DataFrame()
        for col in self.grouped.columns:
        #     diff_grouped[col] = np.log(grouped[col].dropna())
            diff_grouped[col] = self.grouped[col].diff()
            if yearly_seasonality:
                diff_grouped[col] = diff_grouped[col].diff(yearly_seasonality)
        self.diff_grouped = diff_grouped

    def stationarity_test_all(self):
        """
        Tests stationarity for all grouped features/trends, and retains only those that passed. 
        """
        passed_cols = []
        for col in self.diff_grouped.columns:
            print(col)
            res = test_stationarity(self.diff_grouped[col].fillna(0))
            if res=='Passed':
                passed_cols.append(col)
            else:
                print('\t' + res)

        self.passed_trends = [col for col in passed_cols if 'Bin' not in col]
        self.passed_features = [col for col in passed_cols if 'Bin' in col]
        return passed_cols

    def compare_corrs(self, date_cutoff='1970-01-01'):
        """
        Computes correlation for features, note that it looks at the diff_grouped (rather than the grouped)
        because we're interested in the stationarized df!
        """
        mask = self.diff_grouped.index>=date_cutoff
        self.passed_corrs = self.diff_grouped[mask].corr(method='spearman').loc[self.passed_features, self.passed_trends]
        # self.passed_corrs['Percent'] = self.diff_grouped[mask].sum().iloc[len(self.passed_trends):, :][self.passed_trends]
        print(self.passed_corrs)

    def top_corrs(self, desired_trend, thres=0.5, n=-1):
        """
        Displays the n most interesting correlations, only those greater (abs value) than thres.
        """
        sorted = self.passed_corrs[desired_trend].sort_values(ascending=False)
        sorted = sorted.to_frame()
        correlated_features = sorted[sorted[desired_trend]>=thres][:n]
        print(correlated_features)
        correlated_features.index = [re.sub('\(', ' (', item.strip('Bin_')) for item in correlated_features.index]
        correlated_features['Features'] = correlated_features.index
        correlated_features[desired_trend] = correlated_features[desired_trend].apply(lambda x: '{:.2f}'.format(x)[0:4])
        correlated_features = correlated_features.rename(columns={desired_trend:'Correlation'})
        return correlated_features


def test_stationarity(timeseries, plot_test=False, critical_val=5):
    """
    Test stationarity of df, based on adfuller test and code found online at 
    http://dacatay.com/data-science/part-3-time-series-stationarity-python/

    Passing criteria are:
    - Test Statistic must be smaller than Critical Value (default 5%)
    - p-value must be smaller than 0.05
    """
    res = 'Passed'
    #Determing rolling statistics
    rolmean = timeseries.rolling(window=12,center=False).mean()
    rolstd = timeseries.rolling(window=12,center=False).std()

    if plot_test:
        #Plot rolling statistics:
        fig = plt.figure(figsize=(12, 8))
        orig = plt.plot(timeseries, color='blue',label='Original')
        mean = plt.plot(rolmean, color='red', label='Rolling Mean')
        std = plt.plot(rolstd, color='black', label = 'Rolling Std')
        plt.legend(loc='best')
        plt.title('Rolling Mean & Standard Deviation')
        plt.show()
    
    #Perform Dickey-Fuller test:
        print('Results of Dickey-Fuller Test:')
    dftest = adfuller(timeseries, autolag='AIC')
    dfoutput = pd.Series(dftest[0:4], index=['Test Statistic','p-value','#Lags Used','Number of Observations Used'])
    for key,value in dftest[4].items():
        dfoutput['Critical Value (%s)'%key] = value
    if (dfoutput['Test Statistic']>dfoutput['Critical Value ({}%)'.format(str(critical_val))]):
        res = 'Failed!'
            
    if (dfoutput['p-value']>0.05):
        res = 'Failed!'
    
    if plot_test:
        print(dfoutput) 
    return res

def plot_trend_features(grouped, trend, passed_features, date_cutoff=False, plot=True):
    """
    Plots raw trend counts (or proportions) along with desired feature. 
    Has dropdown menu to select feature to plot against trend.

    Counts are more readable than proportions, because auto-scaling causes axes to not be aligned 
    when plotting proportions. 
    """
    plot_config = {'kwargs': {'passed_features': passed_features,
                              'date_cutoff': date_cutoff}, 
                   'df': grouped}
    if not plot:
        return plot_config

    fig = pf.plot_trend_features(df=grouped, trend=trend, passed_features=passed_features, date_cutoff=date_cutoff)
    plotly.offline.iplot(fig, filename='Correlating a trend (' + trend + ') with features')

def plot_trend_against_feature(grouped, desired_col, feature, time_interval='1m'):
    """
    Not being used currently, see plot_trend_feaures above.
    """
    data1 = grouped.groupby(pd.Grouper(freq=time_interval))[desired_col].mean()
    data2 = grouped.groupby(pd.Grouper(freq=time_interval))[feature].mean()

    fig, ax1 = plt.subplots(figsize=(15, 6))

    color = 'tab:red'
    ax1.set_xlabel('Project Posted Date')
    ax1.set_ylabel('Number of Projects', color=color)
    ln1 = ax1.plot(data1, color=color, label='Trend of interest: ' + desired_col)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

    color = 'tab:blue'
    ax2.set_ylabel(feature, color=color)  # we already handled the x-label with ax1
    ln2 = ax2.plot(data2, color=color, label=feature)
    ax2.tick_params(axis='y', labelcolor=color)
    
    lns = ln1+ln2
    labs = [l.get_label() for l in lns]
    ax2.legend(lns, labs, loc=0)
    
    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.title(desired_col + ' trend against '+ feature)
    
    plt.show()

def compare_ratios(df, grouped, trend='virtual', features=[], time_interval = "1m"):
    """
    Compare general baseline ratios of every feature with the ratios within the desired trend.
    """
    # Limit to only rows that correspond to desired trend, and get ratios:
    feat_counts = df[df[trend]==1].groupby(pd.Grouper(freq=time_interval, key='Project Posted Date'))[features].sum()
    trend_feat_ratios = feat_counts.divide(df[df[trend]==1].groupby(pd.Grouper(freq=time_interval, key='Project Posted Date')).size(), axis=0)
    
    # Get ratios for all rows:
    gen_feat_ratios = grouped.divide(df.groupby(pd.Grouper(freq=time_interval, key='Project Posted Date')).size(), axis=0)[features]
    
    # Take simple difference between the two:
    diffs = (trend_feat_ratios - gen_feat_ratios)#.divide(gen_feat_ratios, axis=0)
    return diffs

def plot_diffs(diffs, feat_type=['Subject', 'Poverty', 'Metro', 'Grade', 'Various'], thres=0.045, date_line=None, plot=True):
    """
    Plots ratio differences computed by compare_ratios. 
    Plots only those where mean of last 5 values is above thres (i.e. those that are 'interesting')

    Plot Michael's line, basically a line at any point in time with date_line param.
    Plot only certain types of features by passing list of some or all in 'Subject', 'Income' or 'Grade'.
    """
    # Limit to only 'Subject', 'Poverty', 'Metro', 'Grade', 'Various':
    if feat_type:
        if 'Various' in feat_type:
            feat_type.remove('Various')
            feat_type.extend(['Charter', 'KIPP', 'NLNS', 'Magnet', 'Year_Round'])
        desired_cols = [col for col in diffs.columns if any(x in col for x in feat_type)]
        diffs = diffs[desired_cols]
        
    # Rolling mean to make plot more readable
    to_plot = diffs.rolling(8).mean()
    to_plot.dropna(how='all', inplace=True)
    
    # Set threshold to only view meaningful ratios. Get sorted features fo easier readability, then plot
    if len(to_plot):
        to_plot_cols = [col for col in to_plot.columns if abs(to_plot[col][-5:].mean())>thres]
        to_plot_cols = list(to_plot[to_plot_cols].iloc[-1, :].sort_values(ascending=False).index.values)
    else:
        to_plot_cols = []

    plot_config = {'kwargs': {'to_plot_cols': to_plot_cols,
                              'date_line': date_line}, 
                   'df': to_plot}
    if not plot:
        return plot_config

    fig = pf.plot_diffs(df=to_plot, trend=None, to_plot_cols=to_plot_cols, date_line=date_line)

    #PICKUP HERE
    plotly.offline.iplot(fig, filename='diverging_ratios')

def ggl_trends(grouped, keyword):
    pytrends = TrendReq(hl='en-US', tz=360)
    kw_list = [keyword]
    pytrends.build_payload(kw_list, cat=0, timeframe='all', geo='US', gprop='')
    ggl_trends = pytrends.interest_over_time()
    if ggl_trends.empty:
        return pd.DataFrame() 
    grouped_ggl_trends = ggl_trends.groupby(pd.Grouper(freq='1m')).mean().rename(columns={keyword: 'Google Trends'})
    return grouped.merge(grouped_ggl_trends, left_index=True, right_index=True, how='inner')

def plot_ggl_trends(grouped, keyword, plot=True):
    plot_config = {'kwargs': {}, 
                   'df': grouped}
    if not plot:
        return plot_config

    fig = pf.plot_ggl_trends(df=grouped, trend=keyword)
    plotly.offline.iplot(fig, filename='multiple-axes-double')
