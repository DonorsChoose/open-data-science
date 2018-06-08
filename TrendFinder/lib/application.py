import glob
import re
import json
from datetime import date
from datetime import datetime as dt
import io

from flask import Flask
import pandas as pd
import dash
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import boto3

import plot_formatters as pf

app = dash.Dash(__name__)
application = app.server
app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})
app.css.append_css({"external_url": "https://codepen.io/anon/pen/gzXjjB.css"})
app.css.append_css({"external_url": "https://codepen.io/anon/pen/QraBjB.css"})

app.scripts.append_script({ "external_url": "https://ajax.googleapis.com/ajax/libs/jquery/3.3.1/jquery.min.js"})
app.scripts.append_script({"external_url": "https://codepen.io/anon/pen/QraBjB.js"})

client = boto3.client("s3")
bucket = "donorschoose-trends"

DATES = []
PLOT_DATA = {}

# directory structure:

# donorschoose-trends/ (bucket)
#   2018-03-14/
#   2018-03-28/
#       df.csv
#       trend_1/
#       trend_2/
#       ...
#       trend_n/
#           plot_1/
#           plot_2/
#           ...
#           plot_n/
#               df.csv
#               kwargs.json (exclude for tables)
debug = False

if not debug:
    resp = client.list_objects(Bucket=bucket, Prefix="", Delimiter="/")
    resp['CommonPrefixes'].reverse()
    for prefix in resp['CommonPrefixes']:
        # parse and store date
        prefix = prefix['Prefix']
        date = prefix[:-1]
        DATES.append(date)
        PLOT_DATA[date] = {}
        print("reading {}".format(prefix))
        # read trend table for date
        trends_table = client.get_object(Bucket=bucket, Key='{}{}'.format(prefix, 'df.csv'))['Body'].read()
        PLOT_DATA[date]['trends'] = pd.read_csv(io.BytesIO(trends_table), index_col=0)

        # iterate through trend prefixes for date/
        resp = client.list_objects(Bucket=bucket, Prefix=prefix, Delimiter="/")
        for trend_prefix in resp['CommonPrefixes']:
            # parse and store trend
            print("trend {}".format(trend_prefix))
            trend_prefix = trend_prefix['Prefix']
            trend = trend_prefix[len(prefix):-1]
            PLOT_DATA[date][trend] = {}

            # iterate through plot prefixes for date/trend/
            resp = client.list_objects(Bucket=bucket, Prefix=trend_prefix, Delimiter="/")
            for plot_prefix in resp['CommonPrefixes']:
                # parse and store plot name
                plot_prefix = plot_prefix['Prefix']
                print("plot {}".format(plot_prefix))
                plot = plot_prefix[len(trend_prefix):-1]
                PLOT_DATA[date][trend][plot] = {}

                # read plot df data
                plot_data = client.get_object(Bucket=bucket, Key='{}{}'.format(plot_prefix, 'df.csv'))['Body'].read()
                PLOT_DATA[date][trend][plot]['data'] = pd.read_csv(io.BytesIO(plot_data), index_col=0)

                # read plot kwargs data, if exists
                try:
                    kwargs_resp = client.get_object(Bucket=bucket, Key='{}{}'.format(plot_prefix, 'kwargs.json'))
                    plot_kwargs = kwargs_resp['Body'].read()
                    PLOT_DATA[date][trend][plot]['kwargs'] = json.loads(plot_kwargs)
                except client.exceptions.NoSuchKey:
                    pass # kwargs.json doesn't exist for tables

else:
    data_path = './dashboard/test_data'
    dir_pattern = re.compile("/([^/]*)/$")
    print("reading local test data")
    ### SETUP BLOCK ###
    # TODO: format csv - column order
    dirs = glob.glob('{}/*/'.format(data_path))
    dirs.reverse()
    for directory in dirs:
        date = dir_pattern.search(directory)[1]
        print("reading {}".format(date))
        DATES.append(date)
        PLOT_DATA[date] = {}
        PLOT_DATA[date]['trends'] = pd.read_csv('{}/{}/df.csv'.format(data_path, date))

        trend_dirs = glob.glob('{}/{}/*/'.format(data_path, date))
        for word in trend_dirs:
            word = dir_pattern.search(word)[1]
            PLOT_DATA[date][word] = {}
            plots = glob.glob('{}/{}/{}/*/'.format(data_path, date, word))
            for plot in plots:
                plot = dir_pattern.search(plot)[1]
                PLOT_DATA[date][word][plot] = {}
                # load in kwargs
                plot_path = '{}/{}/{}/{}'.format(data_path, date, word, plot)
                try:
                    kwargs = json.load(open('{}/kwargs.json'.format(plot_path)))
                    PLOT_DATA[date][word][plot]['kwargs'] = kwargs
                except FileNotFoundError:
                    pass # reading in table
                # load in data
                plot_df = pd.read_csv('{}/df.csv'.format(plot_path), index_col=0)
                PLOT_DATA[date][word][plot]['data'] = plot_df 

print("done reading data!")

def generate_trend_table(df, elem_id): # max_rows=10
	return dcc.Graph(
		id=elem_id,
		figure={
			'data': [
				go.Table(
					header=dict(values=df.columns,
                                fill=dict(color='#065331'),
                                font=dict(family="Futura", color="white")
                               ),
					cells=dict(values=[df[col] for col in df.columns],
                               font=dict(family="Futura")
                              )
				)
			],
            'layout': go.Layout(
                autosize=True,
                margin=go.Margin(
                    l=0,
                    r=0,
                    b=0,
                    t=10,
                    pad=0
                )
            )
		},
        # style={'margin': 0, 'padding': 0}
	)

def generate_dropdown(df, elem_id, col="Keyword"):
    if not df.empty:
        return dcc.Dropdown(
            id=elem_id,
            options=[{'label': value, 'value': value} for value in df[col]],
            value=df[col][0]
        )
    return dcc.Dropdown(
        id=elem_id,
        options=[],
        value=None)

def overview_toggle(elem_id):
	options = ['Counts', 'Percentages']
	return dcc.RadioItems(
        id=elem_id,
        options=[{'label': option, 'value': option} for option in options],
        value='Counts',
        labelStyle={'font-family':'Futura'}
        # labelStyle={'display': 'inline-block'}
    )

def window_toggle(elem_id):
	options = [
        {"value":2, "label": "1 month"},
        {"value":6, "label": "3 months"},
        {"value":13, "label": "6 months"},
        {"value":26, "label": "1 year"}
    ]
	return dcc.RadioItems(
        id=elem_id,
        options=options,
        value=6,
        labelStyle={'display': 'inline-block', 'padding-right':5, 'font-family':'Futura'}
    )

def generate_plot(date, trend, plot_name, **kwargs):
    if trend in PLOT_DATA[date]:
        if plot_name in PLOT_DATA[date][trend]:
            plot_kwargs = PLOT_DATA[date][trend][plot_name]['kwargs']
            df = PLOT_DATA[date][trend][plot_name]['data']
            plotter = getattr(pf, plot_name)
            kwargs = {**kwargs, **plot_kwargs}
            fig = plotter(df, trend, **kwargs)
            
            return dcc.Graph(
                id=plot_name,
                figure=fig
            )
        else:
            return 'No "{}" data for {}; date: {}'.format(trend, plot_name, date)
    else:
        return 'No "{}" data for {}'.format(trend, date)

def generate_table(date, trend, table_name, graph=True):
    if trend in PLOT_DATA[date]:
        if table_name in PLOT_DATA[date][trend]:
            df = PLOT_DATA[date][trend][table_name]['data']
            if graph:
                return dcc.Graph(
                    id=table_name,
                    figure={
                        'data': [
                            go.Table(
                                header=dict(values=df.columns,
                                            fill=dict(color='#065331'),
                                            font=dict(family="Futura", color="white")
                                           ),
                                cells=dict(values=[df[col] for col in df.columns],
                                           font=dict(family="Futura"))
                            )
                        ],
                        'layout': go.Layout(
                            # autosize=False,
                            margin=go.Margin(
                                l=0,
                                r=0,
                                b=0,
                                t=10,
                                pad=0
                            )
                        )
                    })

            return df
        else:
            if graph:
                return None
            return pd.DataFrame()
    else:
        if graph:
            return None
        return pd.DataFrame()

app.layout = html.Div(children=[
    
    html.Div(style={'background-color': 'white'}, className='stickytoc', children=[
        html.Ul(children=[
            html.Li(children=[
                html.A(href='#geographic', children='Geographic Breakdown')
            ]),

             html.Li(children=[
                html.A(href='#demographic', children='Demographic Breakdown')
            ]),
 
            html.Li(children=[
                html.A(href='#overview', children='Overview')
            ]),

            html.Li(children=[
                html.A(href='#trendhistory', children='Trend History')
            ]),

            html.Li(children=[
                html.A(href='#top', children='Top')
            ])



        ])
    ]),    
    
    html.H1(children='TrendFinder', style={'text-align':'center'}, id='top'),

    html.Div(children=[
            html.Label('Trends as of:'),
            dcc.Dropdown(
                id='date-dropdown',
                options=[{'label': value, 'value': value} for value in DATES],
                value=DATES[0]
            )
        ]),
    
    html.Div(className='row', children=[
        html.Div(children=[
            html.H4(children='Top Trends by Weight'),
            html.Div(id='trend-table-container',
                     children=generate_trend_table(PLOT_DATA[DATES[0]]['trends'], elem_id='trend-table')),
        ], className='six columns', style={'text-align':'center'}),
    
        html.Div(children=[
            html.Label('Choose trend to inspect:', style={'padding-top':'10%'}),
            html.Div(id='trend-dropdown-container', 
                     children=generate_dropdown(PLOT_DATA[DATES[0]]['trends'], elem_id='trend-dropdown')),
            # co-occurrences
            html.Div(id='co-occurrences')
        ], className='six columns')
    ]),

    html.Hr(style={'border-top':'1px solid'}),
    
	html.H3(children='Trend History', style={'text-align':'center'}, id='trendhistory'),
    # html.Label('Plot xox'),
	html.Div(id='plot-xox'),
    
    html.Hr(),
    
    # html.Label('Plot Google trends'),
    html.Div(id='plot-ggl-trends'),

    html.Hr(style={'border-top':'1px solid'}),
    
	html.H3(children='Overview', id='overview', style={'text-align':'center'}),
    html.Div(className='row', children=[
        html.Div([
            # html.Label('Plot by income'),
            overview_toggle(elem_id='income-toggle'),
            html.Div(id='plot-by-income')
        ], className='six columns'),
        
        html.Div([
            # html.Label('Plot by grade'),
            overview_toggle('grade_toggle'),
            html.Div(id='plot-by-grade')
        ], className='six columns')
    ]),
    
    html.Div(className='row', children=[
        html.Div([
            # html.Label('Plot by subject'),
            overview_toggle('subject_toggle'),
            html.Div(id='plot-by-subject')
        ], className='six columns'),
        
        html.Div([
            # html.Label('Plot by metro'),
            overview_toggle('metro_toggle'),
            html.Div(id='plot-by-metro')
        ], className='six columns')
    ]),
    
    html.Hr(style={'border-top':'1px solid'}),

	html.H3(children='Demographic Breakdown', style={'text-align':'center'}, id='demographic'),
    # html.Label('Plot diffs'),
    html.Div(id='plot-diffs'),
    
    html.Hr(),
    
    html.Div(className='row', children=[
        # top_corrs table here
        html.Div([
            html.Label('Most correlated factors:'),
            html.Div(id='top-corrs')
        ], className='three columns', style={'margin-left':0,'padding-left':'1%'}),
        
        html.Div([
            # html.Label('Plot trend features'),
            html.Div(id='plot-trend-features')
        ], className='nine columns')
    ]),

    html.Hr(style={'border-top':'1px solid'}),
    
	html.H3(children='Geographic Breakdown', style={'text-align':'center'}, id='geographic'),
    html.Label('Choose geographic split:'),
    html.Div(id='geo-splits', children=[
    generate_dropdown(pd.DataFrame(), elem_id='geo-dropdown', col='split')]),

	# html.Label('Plot splits'),
	html.Div(id='plot-splits'),

    html.Hr(),
    
	# html.Label('Plot cumulative splits'),
    html.Div(id='plot-cumulative-splits'),

    html.Hr(),
    
    #html.Label('Plot rolling splits'),
	window_toggle('window_toggle'),
    html.Div(id='plot-rolling-splits'),
    
    html.Hr(),
    
    html.Div(children=[
        html.P(children='Made with ❤ by Pranav Badami, Lorena De La Parra Landa, Elya Pardes, Lex Spirtes, and Michael Zhang from the CKM Advisors Pro Bono Team',
              style={'text-align':'center'}),
        
#         html.Img(src='https://media.glassdoor.com/sql/695553/ckm-advisors-squarelogo-1447451905744.png', 
#                  style={'display':'inline-block','bottom':5,'right':5}),
    ])
])

@app.callback(
    Output(component_id='trend-dropdown-container', component_property='children'),
    [Input(component_id='date-dropdown', component_property='value')]
)
def trend_dropdown(date):
    return generate_dropdown(PLOT_DATA[date]['trends'], elem_id='trend-dropdown')

@app.callback(
    Output(component_id='trend-table-container', component_property='children'),
    [Input(component_id='date-dropdown', component_property='value')]
)
def trend_table(date):
    return generate_trend_table(PLOT_DATA[date]['trends'], elem_id='trend-table')


@app.callback(
	Output(component_id='co-occurrences', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value')]
)
def co_occurrences(date, trend):
	table_name = 'co_occurrences'
	return generate_table(date, trend, table_name)

@app.callback(
	Output(component_id='plot-xox', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value')]
)
def plot_xox(date, trend):
	plot_name = 'plot_xox'
	return generate_plot(date, trend, plot_name)
	

@app.callback(
	Output(component_id='plot-trend-features', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value')]
)
def plot_trend_features(date, trend):
	plot_name = 'plot_trend_features'
	return generate_plot(date, trend, plot_name)

@app.callback(
	Output(component_id='top-corrs', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value')]
)
def top_corrs(date, trend):
	table_name = 'top_corrs'
	return generate_table(date, trend, table_name)

@app.callback(
	Output(component_id='plot-diffs', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value')]
)
def plot_diffs(date, trend):
	plot_name = 'plot_diffs'
	return generate_plot(date, trend, plot_name)

@app.callback(
	Output(component_id='plot-ggl-trends', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value')]
)
def plot_ggl_trends(date, trend):
	plot_name = 'plot_ggl_trends'
	return generate_plot(date, trend, plot_name)

## OVERVIEW
@app.callback(
	Output(component_id='plot-by-income', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value'), 
	 Input(component_id='income-toggle', component_property='value')]
)
def plot_by_income(date, trend, toggle):
	plot_name_counts = 'plot_by_income'
	plot_name_percents = 'percent_by_income'
	if toggle == 'Counts':
		return generate_plot(date, trend, plot_name_counts)
	else:
		return generate_plot(date, trend, plot_name_percents)

@app.callback(
	Output(component_id='plot-by-grade', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value'), 
	 Input(component_id='grade_toggle', component_property='value')]
)
def plot_by_grade(date, trend, toggle):
	plot_name_counts = 'plot_by_grade'
	plot_name_percents = 'percent_by_grade'
	if toggle == 'Counts':
		return generate_plot(date, trend, plot_name_counts)
	else:
		return generate_plot(date, trend, plot_name_percents)

@app.callback(
	Output(component_id='plot-by-subject', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value'),
	 Input(component_id='subject_toggle', component_property='value')]
)
def plot_by_subject(date, trend, toggle):
	plot_name_counts = 'plot_by_subject'
	plot_name_percents = 'percent_by_subject'
	if toggle == 'Counts':
		return generate_plot(date, trend, plot_name_counts)
	else:
		return generate_plot(date, trend, plot_name_percents)

@app.callback(
	Output(component_id='plot-by-metro', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value'),
	 Input(component_id='metro_toggle', component_property='value')]
)
def plot_by_metro(date, trend, toggle):
	plot_name_counts = 'plot_by_metro'
	plot_name_percents = 'percent_by_metro'
	if toggle == 'Counts':
		return generate_plot(date, trend, plot_name_counts)
	else:
		return generate_plot(date, trend, plot_name_percents)

@app.callback(
    Output(component_id='geo-splits', component_property='children'),
    [Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value')]
)
def geo_splits(date, trend):
    table_name = 'geo_splits'
    geo_splits_df = generate_table(date, trend, table_name, graph=False)
    return generate_dropdown(geo_splits_df, elem_id='geo-dropdown', col='split')


@app.callback(
    Output(component_id='plot-splits', component_property='children'),
    [Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value'), 
     Input(component_id='geo-dropdown', component_property='value')]
)
def plot_splits(date, trend, split):
    plot_name = 'plot_splits'
    return generate_plot(date, trend, plot_name, solo_split=split)

@app.callback(
    Output(component_id='plot-cumulative-splits', component_property='children'),
    [Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value'), 
     Input(component_id='geo-dropdown', component_property='value')]
)
def plot_cumulative_splits(date, trend, split):
    plot_name = 'plot_cumulative_splits'
    return generate_plot(date, trend, plot_name, solo_split=split)

@app.callback(
    Output(component_id='plot-rolling-splits', component_property='children'),
    [Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value'),
     Input(component_id='window_toggle', component_property='value'),
     Input(component_id='geo-dropdown', component_property='value')]
)
def plot_rolling_splits(date, trend, window, split):
    plot_name_base = 'plot_rolling_splits'
    plot_name = '{}_{}'.format(plot_name_base, window)
    if trend in PLOT_DATA[date]:
        if plot_name in PLOT_DATA[date][trend]:
            kwargs = PLOT_DATA[date][trend][plot_name]['kwargs']
            kwargs['solo_split'] = split
            df = PLOT_DATA[date][trend][plot_name]['data']
            plotter = getattr(pf, plot_name_base)
            fig = plotter(df, trend, **kwargs)

            return dcc.Graph(
                id=plot_name_base,
                figure=fig
            )
        else:
            return 'No "{}" data for {}, date: {}'.format(trend, plot_name, date)
    else:
        return 'No "{}" data for {}, date: {}'.format(trend, plot_name, date)

if __name__ == '__main__':
	# app.run_server(host='10.39.41.13', port=8100) #host='10.39.41.13', 
	#app.run_server()
    application.run(debug=debug)
