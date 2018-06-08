# Overview (overview_traces)

The objective of this part of the analysis is to provide general overviews for each of the trends. The overviews explored are: income level, grade level, subject, and metro area. Each feature can be viewed as both raw counts and percentages. The purpose of these graphs is to give a high level overview of a trend's behavior over time.

All of the overview formatting and plotting is contained in [overview_traces.py](../lib/overview_traces.py), 

## Filtering

A couple of filtering steps are taken into consideration before plotting to clean up the final output for neater displaying. To determine the start of each plot, a cutoff is applied such that the x-axis begins only when 3% of a trend's volume has been accounted for. This is to eliminate long tails at the beginning.

```python
def cutoff(df):
    percent = df.cum_sum.iloc[-1]*.03
    threshold = df.loc[(df['cum_sum']) > percent]
    t_loc = threshold.iloc[0].name
    df_final = df.iloc[df.index.get_loc(t_loc):]
    return df_final
```

For subject plots, the `edit_cols()` function requires that each subject group needs to have above 5% of all projects within the trend in order to be plotted as an individual category. All other subjects are consolidated into an "Other" category.

## Plotting

For income level, grade level, subject, and metro area, there is an option to see either the counts or percentages per time grouping (by default, per month) on the final dashboard. The function call for these are consistent: `percent_by_subject()` refers to percentages, and `plot_by_subject()` refers to counts, and the category name can easily be substituted for whatever the category of interest is. Custom colors schemes are defined within these plot functions as well.

Both types of plots are generated per trend in advance to enable switching. To alternate between plots, a `bar_switch()` function is called when plotting percentages, which changes counts to percentages for each category.

```python
def bar_switch(df):
    df['sum_col'] = df.sum(axis=1)
    df = df.apply(lambda x: x/df['sum_col']*100, axis=0)
    df = df.drop('sum_col', axis=1)
    df = df.round(1)
    return df
```