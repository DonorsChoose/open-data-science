import json
import os
import re

import pandas as pd
import plotly.graph_objs as go

# function to output plot data to s3 for use by dashboard.py
def output_plot_data(trend, plot_out, plot_name, prefix, bucket, s3_client):
    prefix = '{}/{}/{}'.format(prefix, trend, plot_name)
    kwargs = plot_out['kwargs']
    df = plot_out['df']
    
    kwargs_key = '{}/kwargs.json'.format(prefix)
    data_key = '{}/df.csv'.format(prefix)

    # output kwargs
    s3_client.put_object(Body=json.dumps(kwargs), Bucket=bucket, Key=kwargs_key)
    
    # output data
    s3_client.put_object(Body=df.to_csv(), Bucket=bucket, Key=data_key)

# function to output table data to s3 for use by dashboard.py
def output_table_data(trend, df, table_name, prefix, bucket, s3_client, index=False):
    if trend is not None:
        prefix = '{}/{}/{}'.format(prefix, trend, table_name)
    table_key = '{}/df.csv'.format(prefix)
    s3_client.put_object(Body=df.to_csv(), Bucket=bucket, Key=table_key)

# TrendFinder plot_xox resource
def plot_xox(df, trend, prop=True):
    if prop:
        y_title = 'Proportion of Projects'
        propcounts = 'prop'
        active=1
    else:
        y_title = 'Trend counts'
        propcounts = 'Number of Projects'
        active=0

    trace = go.Scatter(
        x = df.index,
        y = df[propcounts].values
    )

    data = [trace]

    updatemenus=list([
                dict(
                    active=active,
                    buttons=list([   
                        dict(label = 'Counts',
                            method = 'update', 
                            args=[ 
                                {
                                    'x':[df.index], 
                                    'y':[df['counts'].values], 
                                    'name':'Trend counts'
                                },
                                {
                                    'title':'"{}" Projects over Time'.format(trend),
                                    'yaxis': dict(title = 'Number of Projects')
                                } 
                            ]
                        ),
                        dict(label = 'Proportions',
                            method = 'update', 
                            args=[ 
                                {
                                    'x':[df.index], 
                                    'y':[df['prop'].values], 
                                    'name': 'Trend proportion'},
                                {
                                    'title':'"{}" Projects over Time'.format(trend),
                                    'yaxis': dict(title = 'Proportion of Projects')
                                } 
                            ]
                        ),
                    ]),
                    direction = 'left',
                    pad = {'r': 10, 't': 10},
                    showactive = True,
                    type = 'buttons',
                    x = 0.1,
                    xanchor = 'left',
                    y = 1.1,
                    yanchor = 'top' 
                )
            ])

    layout = dict(
        title = '"{}" Projects over Time'.format(trend),
        xaxis = dict(title = 'Project Posted Date'),
        yaxis = dict(title = y_title),
        updatemenus = updatemenus,
        font = {'family': 'Futura'}   
        )

    fig = dict(data=data, layout=layout)
    return fig

# Geo plot_trend_features resource 

def plot_trend_features(df, trend, passed_features=[], date_cutoff=False):
    """
    Plots raw trend counts (or proportions) along with desired feature. 
    Has dropdown menu to select feature to plot against trend.

    Counts are more readable than proportions, because auto-scaling causes axes to not be aligned 
    when plotting proportions. 
    """
    trace_trend = go.Scatter(x=df.index,
                            y=df[trend],
                            name=trend,
                            line=dict(color='#33CFA5'),
                            yaxis='y1'
                            )

    data = [trace_trend]
    visible_boolean = ([False] * len(passed_features))

    tmp_button_dict = dict(label = 'None',
                         method = 'update',
                         args = [{'visible': [True] + visible_boolean},
                                 {'title': 'Feature Correlator for "{}" Projects'.format(trend)},
                                #  dict(yaxis=dict(range=[3, 6]))
                                ]
                          )

    buttons_list = [tmp_button_dict]

    for i, feat in enumerate(passed_features):
        tmp_trace_feat = go.Scatter(x=df.index,
                                y=df[feat],
                                    name=feat,
                                    visible=False,
                                    line=dict(color='#F06A6A'),
                                yaxis='y2'
                                   )
        data.append(tmp_trace_feat)

        visible_boolean = ([False] * len(passed_features))
        visible_boolean[i] = True

        tmp_button_dict = dict(label = feat,
                         method = 'update',
                         args = [{'visible': [True] + visible_boolean},
                                 {'title': 'Correlating "{}" Projects with {}'.format(trend, feat)},
                                #  dict(yaxis=dict(range= [i, i+3]))
                                ]
                            )

        buttons_list.append(tmp_button_dict)

    updatemenus = list([
        dict(active=-1,
             buttons=list(buttons_list),
             direction = 'down',
                pad = {'r': 10, 't': 10},
                showactive = True,
                x = 0.,
                xanchor = 'left',
                y = 1.1,
                yanchor = 'top'          
        )
    ])
    if date_cutoff:
        shapes = [{'type': 'rect',
                # x-reference is assigned to the x-values
                'xref': 'x',
                # y-reference is assigned to the plot paper [0,1]
                'yref': 'paper',
                'x0': date_cutoff,
                'y0': 0,
                'x1': df.index[-1],
                'y1': 1,
                'fillcolor': '#d3d3d3',
                'opacity': 0.2,
                'line': {
                    'width': 0,
                }
            }]
    else:
        shapes = []
    layout = dict(title='Feature Correlator for "{}" Projects'.format(trend), 
                showlegend=False,
                updatemenus=updatemenus,
                xaxis=dict(
                    title='Project Posted Date',
                    rangeslider=dict(),
                    type='date'
                ),
                yaxis=dict(
                    title='Trend',
                    titlefont=dict(
                        color='#33CFA5'
                    ),
                    tickfont=dict(
                        color='#33CFA5'
                    ),
                ),
                yaxis2=dict(
                    title='Feature',
                    titlefont=dict(
                        color='#F06A6A'
                    ),
                    tickfont=dict(
                        color='#F06A6A'
                    ),
                    overlaying='y',
                    side='right',
                ),
                shapes = shapes,
                font = {'family': 'Futura'}     
            )

    fig = dict(data=data, layout=layout)
    return fig

# Geo plot_diffs resource 

def plot_diffs(df, trend, to_plot_cols, date_line):
    data = [{
        'x': df.index,
        'y': df[col],
        'name': col
    }  for col in to_plot_cols]

    data.append(go.Scatter(
        {
            'x': [date_line],
            'y': [df.values.max()],
            'showlegend': False,
            'text': [date_line],
            'mode': 'markers+text',
            'textposition': 'top',
            'textfont':  dict(
              color = "#FF00FF",
              size = 12
        ),
        }
    ))

    if trend is None:
        trend = "Trend"
    layout = {
        'xaxis': {'title': 'Project Posted Date'},
        'yaxis': {'title': "Ratio Difference"},
        'title': 'Most Diverging Features in "{}" Projects'.format(trend),
        'font': {'family':'Futura'}
    }

    if date_line:
        shapes=[{
            'type': 'line',
            'x0': date_line,
            'y0': df.values.min(),
            'x1': date_line,
            'y1': df.values.max(),
            'opacity': 0.6,
            'line': {
                'color': '#FF00FF',
                'width': 4,
            }
        }]
        
        layout['shapes'] = shapes
        
    fig = {'data': data,
           'layout': layout}
    return fig

def plot_ggl_trends(df, trend):
    if df.empty:
        return go.Figure(data=dict(), layout=dict(title="No Google Trends data for {}".format(trend)))
    trace1 = go.Scatter(
        x=df.index,
        y=df[trend],
        name=trend,
        line=dict(color='#33CFA5'),
        yaxis='y',
    )
    trace2 = go.Scatter(
        x=df.index,
        y=df['Google Trends'],
        name='Google',
        line=dict(color='#F06A6A'),
        yaxis='y2',
        visible='legendonly'
    )
    data = [trace1, trace2]
    layout = go.Layout(
        title='"{}" DonorsChoose.org Projects vs. Google Trends Index'.format(trend),
        yaxis=dict(
            title='Project Counts',
            rangemode='tozero',
            titlefont=dict(
                color='#33CFA5'
            ),
            tickfont=dict(
                color='#33CFA5'
            ),
        ),
        yaxis2=dict(
            title='Google Trends Index',
            titlefont=dict(
                color='#F06A6A'
            ),
            tickfont=dict(
                color='#F06A6A'
            ),
            overlaying='y',
#             rangemode='tozero',
            side='right'
        ),
        xaxis = {'title': 'Project Posted Date'},
        font = {'family': 'Futura'}              
    )
    fig = go.Figure(data=data, layout=layout)
    return fig

# overview plots
def create_title(s):
    #creates titles for graphs
    y = re.sub('_', ' ', s)
    y = y.title()
    return y


def percent_cols(s):
    """clean percent dataframe columns"""
    y = s.lower()
    y = re.sub(r'[^a-z\d]', ' ', y)
    y = re.sub(r'\s+', '_', y.strip())
    y = y + '_' + "%"
    return y


def percentages(df):
    #calculates the percentages for text in plot functions
    df['sum_col'] = df.sum(axis=1)
    df = df.apply(lambda x: x/df['sum_col']*100, axis=0)
    df = df.drop('sum_col', axis=1)
    df.columns = map(percent_cols, list(df))
    df = df.round(1)
    return df

def clean_cols(s):
    """clean dataframe columns"""
    y = s.lower()
    y = re.sub(r'[^a-z\d]', ' ', y)
    y = re.sub(r'\s+', '_', y.strip())
    return y

def create_traces(df, colorlist):
    #creates traces for plot_by functions
    df.columns = map(clean_cols, df.columns)
    df = df.drop('cum_sum', axis=1)
    df1= percentages(df)
    df = df.drop('sum_col', axis=1)
    trace_list = []
    c = 0
    for x in df.columns:
        x = go.Bar(y=df[x],
                   x=df.index,
                   text =df1[x + '_%'].apply(lambda x: str(x)+ '%'),
                   name = create_title(x),
                   marker = dict(color=colorlist[c]),
                   opacity = .6)
        trace_list.append(x)
        c = c+1
    return trace_list

def percent_traces(df, colorlist):
    #creates traces for percent_by functions
    df.columns = map(clean_cols, df.columns)
    trace_list = []
    c = 0
    for x in df.columns:
        x = go.Bar(y=(df[x].astype(str) + '%'),
                   x=df.index,
                   name = create_title(x),
                   text = df[x].astype(str) + '%',
                   hoverinfo = 'text',
                   marker = dict(color=colorlist[c]),
                   opacity = .6)
        trace_list.append(x)
        c = c+1
    return trace_list

def create_subject_traces(df, colorlist):
    #cretes subject traces for plot_by_subject function
    df.columns = map(clean_cols, df.columns)
    df1= percentages(df)
    df = df.drop('sum_col', axis=1)
    trace_list = []
    c = 0
    for x in df.columns:
        x = go.Bar(y=df[x],
                   x=df.index,
                   text =df1[x + '_%'].apply(lambda x: str(x)+ '%'),
                   name = create_title(x),
                   marker = dict(color=colorlist[c]),
                   opacity = .6)
        trace_list.append(x)
        c = c+1
    return trace_list

def plot_by_metro(df, trend, colors):
    data = create_traces(df, colors)
    layout= go.Layout(barmode='stack',
                      title= 'School Metro Areas in "{}" Projects over Time'.format(trend),
                      xaxis = {'title': 'Project Posted Date'},
                      yaxis = {'title': 'Number of Projects'},
                      font = {'family': 'Futura'}
                     )
    fig = go.Figure(data=data, layout=layout)
    return fig

def plot_by_grade(df, trend, colors):
    data = create_traces(df, colors)
    layout= go.Layout(barmode='stack',
                      title= 'Grade Levels in "{}" Projects over Time'.format(trend),
                      xaxis = {'title': 'Project Posted Date'},
                      yaxis = {'title': 'Number of Projects'},
                      font = {'family': 'Futura'} 
                     )
    fig = go.Figure(data=data, layout=layout)
    return fig

def plot_by_income(df, trend, colors):
    data = create_traces(df, colors)
    layout= go.Layout(barmode='stack',
                      title= 'School Income Levels in "{}" Projects over Time'.format(trend),
                      xaxis = {'title': 'Project Posted Date'},
                      yaxis = {'title': 'Number of Projects'},
                      font = {'family': 'Futura'} 
                     )
    fig = go.Figure(data=data, layout=layout)
    return fig

def plot_by_subject(df, trend, colors):
    data = create_subject_traces(df, colors)
    layout= go.Layout(barmode='stack',
                      title= 'Subject Distribution in "{}" Projects over Time'.format(trend),
                      xaxis = {'title': 'Project Posted Date'},
                      yaxis = {'title': 'Number of Projects'},
                      font = {'family': 'Futura'} 
                     )
    fig = go.Figure(data=data, layout=layout)
    return fig

def percent_by_grade(df, trend, colors):
    data = percent_traces(df, colors)
    layout= go.Layout(barmode='stack',
                      title= 'Grade Levels in "{}" Projects over Time'.format(trend),
                      xaxis = {'title': 'Project Posted Date'},
                      yaxis = {'title': 'Proportion of Projects'},
                      font = {'family': 'Futura'} 
                     )
    fig = go.Figure(data=data, layout=layout)
    return fig

def percent_by_income(df, trend, colors):
    data = percent_traces(df, colors)
    layout= go.Layout(barmode='stack',
                      title= 'School Income Levels in "{}" Projects over Time'.format(trend),
                      xaxis = {'title': 'Project Posted Date'},
                      yaxis = {'title': 'Proportion of Projects'},
                      font = {'family': 'Futura'} 
                     )
    fig = go.Figure(data=data, layout=layout)
    return fig

def percent_by_metro(df, trend, colors):
    data = percent_traces(df, colors)
    layout= go.Layout(barmode='stack',
                      title= 'School Metro Areas in "{}" Projects over Time'.format(trend),
                      xaxis = {'title': 'Project Posted Date'},
                      yaxis = {'title': 'Proportion of Projects'},
                      font = {'family': 'Futura'} 
                     )
    fig = go.Figure(data=data, layout=layout)
    return fig

def percent_by_subject(df, trend, colors):
    data = percent_traces(df, colors)
    layout= go.Layout(barmode='stack',
                      title= 'Subject Distribution in "{}" Projects over Time'.format(trend),
                      xaxis = {'title': 'Project Posted Date'},
                      yaxis = {'title': 'Proportion of Projects'},
                      font = {'family': 'Futura'} 
                     )
    fig = go.Figure(data=data, layout=layout)
    return fig

def plot_splits(df, trend, split_names, line_pos_dict, solo_split=None): #ADD line_pos_dict
	data = []
	active = 0
	shapes = []
	for i, split in enumerate(split_names):
		data.append(go.Bar(x=df.index,
           			   y=df['in_{}'.format(split)], 
               		   base=df['bottom_{}'.format(split)],
					   name='in {}'.format(split),
                       visible=False))
		data.append(go.Bar(x=df.index,
               y=df['not_{}'.format(split)],
               base=df['bottom_{}'.format(split)]+df['in_{}'.format(split)],
			   name='not in {}'.format(split), 
               visible=False))
		data.append(go.Scatter(mode='lines', 
					x=[df.index[0], df.index[-1]],
					y=[line_pos_dict[split], line_pos_dict[split]],
					name='historical proportion in {}'.format(split),
					visible=False,
					line=dict(color='rgb(0,0,0)',width=1)))
		if split == solo_split:
			active = i

	data[active*3].visible = True
	data[active*3 + 1].visible = True
	data[active*3 + 2].visible = True

	buttons = []
	for i, split in enumerate(split_names):
		visible = ([False] * (len(split_names) * 3))
		visible[3*i] = True
		visible[3*i+1] = True
		visible[3*i+2] = True
		# ADD line_pos line as visible
		option = dict(label=split, 
                      method='update',
                      args=[dict(visible=visible),
                            dict(title='Proportion of "{}" Projects in "{}" Split'.format(trend,split))])
		buttons.append(option)
	if solo_split is None:
		updatemenus = [dict(active=active, showactive=True,  buttons=buttons)]
	else:
		updatemenus = []
	layout = go.Layout(barmode='stack', 
                       updatemenus=updatemenus, 
                       title='Proportion of "{}" Projects in "{}" Split'.format(trend, split_names[active]),
                       xaxis = {'title':'Project Posted Date'},
                       yaxis = {'title':'Proportion of Projects'},
                       font = {'family':'Futura'}
                      )
	fig = dict(data=data, layout=layout)
	return fig

def plot_cumulative_splits(df, trend, split_names, solo_split=None):
    data = []
    active = 0
    for i, split in enumerate(split_names):
        data.append(go.Scatter(x=df.index, 
                               y=df[split], 
                               name=split, 
                               visible=False))
        if split == solo_split:
            active = i
    data[active].visible = True

    buttons = []
    for i, split in enumerate(split_names):
        visible = ([False] * len(split_names))
        visible[i] = True
        option = dict(label=split, 
                      method='update',
                      args=[dict(visible=visible),
                            dict(title='Cumulative Proportion of "{}" Projects in "{}" Split'.format(trend, split))])
        buttons.append(option)
    if solo_split is None:
        updatemenus = [dict(active=active, buttons=buttons)]
    else:
        updatemenus = []

    layout = go.Layout(title='Cumulative Proportion of "{}" Projects in "{}" Split'.format(trend, split_names[active]), 
                       updatemenus=updatemenus,
                       xaxis = {'title':'Project Posted Date'},
                       yaxis = {'title':'Proportion of Projects'},
                       font = {'family':'Futura'})
    fig = dict(data=data, layout=layout)
    return fig

def plot_rolling_splits(df, trend, window, split_names, solo_split=None):
    windows = {
        2: "1 month",
        6: "3 months",
        13: "6 months",
        26: "1 year"
    }
    
    data = []
    active = 0
    for i, split in enumerate(split_names):
        data.append(go.Scatter(x=df.index, 
                               y=df[split], 
                               name=split, 
                               visible=False))
        if split == solo_split:
            active = i
       
    data[active].visible = True

    buttons = []
    for i, split in enumerate(split_names):
        visible = ([False] * len(split_names))
        visible[i] = True
        option = dict(label=split, 
                      method='update',
                      args=[dict(visible=visible),
                            dict(title='Rolling Proportion ({}) of "{}" Projects in "{}" Split'.format(windows[window], trend,
                                                                                                    split))])
        buttons.append(option)
    if solo_split is None:
        updatemenus = [dict(active=active, buttons=buttons)]
    else:
        updatemenus = []

    layout = go.Layout(title='Rolling Proportion ({}) of "{}" Projects in "{}" Split'.format(windows[window], trend,
                                                                                          split_names[active]),
                                                                                          
                       updatemenus=updatemenus,
                       xaxis = {'title':'Project Posted Date'},
                       yaxis = {'title':'Proportion of Projects'},
                       font = {'family':'Futura'}
                      )
    fig = dict(data=data, layout=layout)
    return fig

