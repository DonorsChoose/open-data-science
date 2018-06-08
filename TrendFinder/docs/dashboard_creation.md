# Dashboard creation (plot_formatters, dashboard)

To create a user-interactive dashboard, we used [Dash](https://plot.ly/products/dash/), porting all of our graphs into [Plotly](https://plot.ly/python/getting-started/) in the process. Dash is a framework written on top of Flask, Plotly, and React to enable data visualization applications rendered in-browser written solely in Python, with most web deployment-related mechanisms abstracted out. Each component on the dashboard represents an individual Plotly plot, and each plot consists of traces, which comprise of the data and configuration for any single plot element. 

We recommend reading Plotly's own documentation on their plotting system to better understand the vocabulary before diving into any plot specifics, as this documentation will not go over how to edit specific plots or traces.

## Overview

To give a high-level overview of how this pipeline contributes to the end-user dashboard, the [main.py](../main.py) script basically runs through all of the modules' plotting functions, outputting all the data and configuration necessary to rebuild each plot with as little information as possible (to keep the data storage lightweight and re-rendering inexpensive) using [plot_formatters.py](../lib/plot_formatters.py). Then, to actually serve the dashboard, [dashboard.py](../lib/dashboard.py) needs to be executed, which performs all of the rendering and formatting for the final dashboard view and serves it.

## Storing data

Within S3, the data and configuration needed for each plot is organized using a few layers of string formatting. Generally, data will be stored under `prefix`/`trend`/`plot_name`/`df.csv`, and configuration as `prefix`/`trend`/`plot_name`/`kwargs.json`. Here, the `prefix` refers to the date, for storing past real-time trends, `trend` refers to a specific keyword, and `plot_name` refers to whatever the internal name for a specific plot is. For example, for the distribution of proportions by subject for the insect trend found on March 28th, 2018, the folder would be `2018-03-28`/`insect`/`percent_by_subject`/. 

In `prefix`/, there is also a `df.csv` that contains the overall trends for that time period.

To give a more complete example, this is what a directory might look like.

```python
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
```

To automatically store everything, there are a couple of helper functions that organize everything appropriately. Remember, plots require both a `df.csv` and a `kwargs.json` file.

```python
def output_plot_data(trend, plot_out, plot_name, prefix, bucket, s3_client):
    prefix = '{}/{}/{}'.format(prefix, trend, plot_name)
    kwargs = plot_out['kwargs']
    df = plot_out['df']
    
    kwargs_key = '{}/kwargs.json'.format(prefix)
    data_key = '{}/df.csv'.format(prefix)

    # Output kwargs
    s3_client.put_object(Body=json.dumps(kwargs), Bucket=bucket, Key=kwargs_key)
    
    # Output data
    s3_client.put_object(Body=df.to_csv(), Bucket=bucket, Key=data_key)
```

For tables, it is similar to plots, but there are no kwargs necessary since the tables are ultimately rendered and customized in [dashboard.py](../lib/dashboard.py).

```python
def output_table_data(trend, df, table_name, prefix, bucket, s3_client, index=False):
    if trend is not None:
        prefix = '{}/{}/{}'.format(prefix, trend, table_name)
    table_key = '{}/df.csv'.format(prefix)
    # Output data
    s3_client.put_object(Body=df.to_csv(), Bucket=bucket, Key=table_key)
```

In [main.py](../main.py), one of these two functions is called after any plot or table is created, with all the relevant data passed to it.

## Rendering the output

Within [plot_formatters.py](../lib/plot_formatters.py), each unique Plotly plot is defined in terms of its creation, accepting a dataframe (`df`), keyword (`trend`), and whatever additional arguments are necessary to regenerate the plot, so that it can be called during the dashboard creation process. The dashboard uses the same function to render all plots.

```python
import plot_formatters as pf

def generate_plot(date, trend, plot_name, **kwargs):
    # PLOT_DATA has already read through the bucket here
    if trend in PLOT_DATA[date]: 
        if plot_name in PLOT_DATA[date][trend]:
            plot_kwargs = PLOT_DATA[date][trend][plot_name]['kwargs']
            df = PLOT_DATA[date][trend][plot_name]['data']
            # Define what plot function should be used to create the figure
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
```

For tables, there are a couple of different functions, as the tables have different formatting options applied. For the big master list of trends, `generate_trend_table()` is used, and for all other tables, a generic `generate_table()` is used.

These functions are called via callbacks defined per component, where HTML component IDs connect plot rendering to specific HTML elements. As a basic example, here is how `plot_xox()` is called in the backend.

```python
@app.callback(
	Output(component_id='plot-xox', component_property='children'),
	[Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value')]
)
def plot_xox(date, trend):
	plot_name = 'plot_xox'
	return generate_plot(date, trend, plot_name)
```

When HTML elements are defined later on, including a div with the appropriate ID (`html.Div(id='plot-xox')`) is all that is needed for rendering the specific figure.

### Dropdowns and toggles

To keep the dashboard responsive to different options, such as date or specific trends, a series of dropdown and toggle chains are defined under-the-hood in [dashboard.py](../lib/dashboard.py). Dash contains both types of elements under its `dash-core-components` (dcc) module, and these can be defined as functions that get called during HTML element creation.

```python
def overview_toggle(elem_id):
	options = ['Counts', 'Percentages']
	return dcc.RadioItems(
        id=elem_id,
        options=[{'label': option, 'value': option} for option in options],
        value='Counts',
        labelStyle={'font-family':'Futura'}
        # labelStyle={'display': 'inline-block'}
    )

# ...

app.layout = # ...
    html.Div(className='row', children=[
        html.Div([
            # html.Label('Plot by subject'),
            overview_toggle('subject_toggle'),
            html.Div(id='plot-by-subject')
        ], className='six columns'),
```


Whenever appropriate, additional inputs from dropdowns or toggles must be included in the callback, so that it can be passed to the function. As a complicated example, `plot_rolling_splits()` requires not only the date and trend dropdown selections (these 2 are necessary for nearly all components), but also a `window_toggle` selection for the number of months to include in its rolling window, as well a `geo_dropdown` selection that specifics the present geographic split of concern. These all get passed into the function call whenever it updates.

```python
@app.callback(
    Output(component_id='plot-rolling-splits', component_property='children'),
    [Input(component_id='date-dropdown', component_property='value'),
     Input(component_id='trend-dropdown', component_property='value'),
     # Months to include
     Input(component_id='window_toggle', component_property='value'),
     # Specific geographic split
     Input(component_id='geo-dropdown', component_property='value')]
)

def plot_rolling_splits(date, trend, window, split):
    # ...
```

## Customizing the dashboard layout

For customizing specific plots, the specific graph object for layout must be changed, as Dash is simply arranging the generated figure on the frontend. For this, we recommend referring to Plotly's documentation on [layout](https://plot.ly/python/reference/#layout). Remember, this is done in [dashboard.py](../lib/dashboard.py) for tables, and [plot_formatters.py](../lib/plot_formatters.py) for plots. Note, customizing plots can be tedious, as each plot is defined separately.

As for customizing the Dash dashboard, the sequence of component appearance and specific HTML elements are all defined in the `app.layout` variable in [dashboard.py](../lib/dashboard.py). As a brief example, here is how the top part of the dashboard is defined, from the TrendFinder title to the horizontal rule before the "Overview" section begins.

```python
app.layout = html.Div(children=[
    # Sticky ToC defined here...  
    
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
```

Currently, CSS can only be appended from an external link, and this dashboard is using a basic default [Codepen](https://codepen.io/chriddyp/pen/bWLwgP.css) from the creator of Plotly/Dash to do some of the high-level formatting, such as the `className='six columns'` notation. Other styling is also linked at the top of the file.

In any case, customizing the layout primarily consists of moving different components around in the layout and applying the appropriate styling to them. There is a tremendous (and potentially confusing) amount of flexibility in defining styling by component and the overall dashboard, so we recommend keeping categories of components (sections, tables, etc.) consistent whenever possible.