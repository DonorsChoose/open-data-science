import re
import os

import pandas as pd
import numpy as np
import plotly.plotly as py
import plotly.graph_objs as go
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot

from lib import plot_formatters as pf

init_notebook_mode(connected=True)

def bar_switch(df):
    #function for creating percent bars, rather than volume
    df['sum_col'] = df.sum(axis=1)
    df = df.apply(lambda x: x/df['sum_col']*100, axis=0)
    df = df.drop('sum_col', axis=1)
    df = df.round(1)
    return df

def create_title(s):
    #creates titles for graphs
    y = re.sub('_', ' ', s)
    y = y.title()
    return y

def cutoff(df):
    #cuts dataframe to only include time when 3% of all projects made
    percent = df.cum_sum.iloc[-1]*.03
    threshold = df.loc[(df['cum_sum']) > percent]
    t_loc = threshold.iloc[0].name
    df_final = df.iloc[df.index.get_loc(t_loc):]
    return df_final

def grade_analyses(df):
    #does analysis for grade data
    column_grouped = df.groupby(['Project Grade Level', pd.Grouper(key = 'Project Posted Date', freq = 'M')]).size().to_frame('freq').reset_index()
    # Outputs pivot table of count by time period per grade level (grade level as columns)
    column_pivoted = column_grouped.pivot(index= 'Project Posted Date', columns='Project Grade Level', values ='freq').fillna(value = 0)
    # Calculate cumulative sum
    column_pivoted['cum_sum'] = column_pivoted.sum(axis=1).cumsum()
    return column_pivoted

def income_analyses(df):
    #does analysis for income data
    column_grouped = df.groupby(['School Poverty Level', pd.Grouper(key = 'Project Posted Date', freq = 'M')]).size().to_frame('freq').reset_index()
    column_pivoted = column_grouped.pivot(index= 'Project Posted Date', columns='School Poverty Level', values ='freq').fillna(value = 0)
    column_pivoted['cum_sum'] = column_pivoted.sum(axis=1).cumsum()
    return column_pivoted

def subject_analyses(df):
    #does analysis for subject data
    column_grouped = df.groupby(['Project Subject Category', pd.Grouper(key = 'Project Posted Date', freq = 'M')]).size().to_frame('freq').reset_index()
    column_pivoted = column_grouped.pivot(index= 'Project Posted Date', columns='Project Subject Category', values ='freq').fillna(value = 0)
    column_pivoted['cum_sum'] = column_pivoted.sum(axis=1).cumsum()
    return column_pivoted

def metro_analyses(df):
    #does analysis for metro data
    column_grouped = df.groupby(['School Metro Area', pd.Grouper(key = 'Project Posted Date', freq = 'M')]).size().to_frame('freq').reset_index()
    column_pivoted = column_grouped.pivot(index= 'Project Posted Date', columns='School Metro Area', values ='freq').fillna(value = 0)
    column_pivoted['cum_sum'] = column_pivoted.sum(axis=1).cumsum()
    return column_pivoted

def percent_by_subject(df, trend_name, plot=True):
    #generates graph for subject percentages
    analysis_df = cutoff(subject_analyses(df))
    df = edit_cols(df, analysis_df)
    df = bar_switch(df)
    colors = ['#84B9EF','#FBE4C9', '#FF5D5D', '#952E4B' , '#FFFF9D', '#F38181', '#F12D2D', '#660000' ]
    plot_config = {'kwargs': {'colors': colors}, 
                   'df': df}
    if not plot:
        return plot_config

    fig = pf.percent_by_subject(df=df, trend=trend_name, colors=colors)
    iplot(fig, filename ='stacked-bar')

def percent_by_grade(df, trend_name, plot=True):
    #generates graph for grade percentages
    df = cutoff(grade_analyses(df))
    df = df.drop('cum_sum', axis=1)
    df = bar_switch(df)
    colors = ['#FDA403','#FFD6A0', '#404B69', '#7FA99B']
    plot_config = {'kwargs': {'colors': colors}, 
                   'df': df}
    if not plot:
        return plot_config

    fig = pf.percent_by_grade(df=df, trend=trend_name, colors=colors)
    iplot(fig, filename ='stacked-bar')

def percent_by_metro(df, trend_name, plot=True):
    #generates graph for metro percentages
    df = cutoff(metro_analyses(df))
    df = df.drop('cum_sum', axis=1)
    df = bar_switch(df)
    colors = ['#194769','#A0C1B8', '#E4D183', '#F2855E']
    plot_config = {'kwargs': {'colors': colors}, 
                   'df': df}
    if not plot:
        return plot_config

    fig = pf.percent_by_metro(df=df, trend=trend_name, colors=colors)
    iplot(fig, filename ='stacked-bar')

def percent_by_income(df, trend_name, plot=True):
    #generates graph for income percentages
    df = cutoff(income_analyses(df))
    df = df.drop('cum_sum', axis=1)
    df = bar_switch(df)
    colors = ['rgb(0, 0, 102)', 'rgb(127, 166, 238)']
    plot_config = {'kwargs': {'colors': colors}, 
                   'df': df}
    if not plot:
        return plot_config

    fig = pf.percent_by_income(df=df, trend=trend_name, colors=colors)
    iplot(fig, filename ='stacked-bar')

def percent_all(df, trendname):
    #plots all percent functions
    percent_by_grade(df, trendname)
    percent_by_income(df, trendname)
    percent_by_metro(df, trendname)
    percent_by_subject(df, trendname)

def plot_by_metro(df, trend_name, plot=True):
    #generates graph for metro volume/percentages
    df = cutoff(metro_analyses(df))
    colors = ['#194769','#A0C1B8', '#E4D183', '#F2855E']
    plot_config = {'kwargs': {'colors': colors}, 
                   'df': df}
    if not plot:
        return plot_config

    fig = pf.plot_by_metro(df=df, trend=trend_name, colors=colors)
    iplot(fig, filename ='stacked-bar')

def plot_by_grade(df, trend_name, plot=True):
    #generates graph for grade volume/percentages
    df = cutoff(grade_analyses(df))
    colors = ['#FDA403','#FFD6A0', '#404B69', '#7FA99B']
    plot_config = {'kwargs': {'colors': colors}, 
                   'df': df}
    if not plot:
        return plot_config

    fig = pf.plot_by_grade(df=df, trend=trend_name, colors=colors)
    iplot(fig, filename ='stacked-bar')

def plot_by_income(df, trend_name, plot=True):
    #generates graph for income volume/percentages
    df = cutoff(income_analyses(df))
    colors = ['rgb(0, 0, 102)', 'rgb(127, 166, 238)']
    plot_config = {'kwargs': {'colors': colors}, 
                   'df': df}
    if not plot:
        return plot_config

    fig = pf.plot_by_income(df=df, trend=trend_name, colors=colors)
    iplot(fig, filename ='stacked-bar')

#returns dataframe with pertinent columns for plot_by_subject
def edit_cols(df, analysis_df):
    #calculating cumsum for each of the subjects
    subj_frame = subject_analyses(df).drop('cum_sum', axis=1).cumsum().iloc[-1].to_frame('cum_sum').reset_index().sort_values(by='cum_sum', ascending=False)
    #calculates overall sum and if a subject has more than 5 percent of the share, then it will not be grouped int other
    c_sum = subj_frame.cumsum().cum_sum.iloc[-1]*.05
    top_set = set(subj_frame.loc[subj_frame['cum_sum'] >= c_sum]["Project Subject Category"])
    #set of all subjects
    subj_set = set(subj_frame["Project Subject Category"])
    #set of not-included subjects
    other = list(subj_set - top_set)
    #dataframe that compiles all others into one column
    odf = analysis_df.filter(items=other)
    odf['Other'] = odf.sum(axis=1)
    only_other = odf.Other.to_frame()
    #dataframe of all subjects over 5%
    top_list = list(top_set)
    top_subjs = analysis_df.filter(items=top_list)
    #a join of top subjects and other
    final = top_subjs.join(only_other, how='outer')
    return final

def plot_by_subject(df, trend_name, plot=True):
    #generates graph for subject volume/percentages
    analysis_df = cutoff(subject_analyses(df))
    df = edit_cols(df, analysis_df)
    colors = ['#84B9EF','#FBE4C9', '#FF5D5D', '#952E4B' , '#FFFF9D', '#F38181', '#F12D2D', '#660000' ]

    plot_config = {'kwargs': {'colors': colors}, 
                   'df': df}
    if not plot:
        return plot_config

    fig = pf.plot_by_subject(df=df, trend=trend_name, colors=colors)
    iplot(fig, filename ='stacked-bar')

def volume_plot_all(df, trend_name):
    #volume plots all
    plot_by_income(df, trend_name)
    plot_by_grade(df, trend_name)
    plot_by_subject(df, trend_name)
    plot_by_metro(df, trend_name)
