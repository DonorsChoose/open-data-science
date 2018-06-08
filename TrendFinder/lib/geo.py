import itertools

import pandas as pd
import plotly
import plotly.graph_objs as go
from fuzzywuzzy import fuzz, process

from lib import plot_formatters as pf
from .geo_data.geo_mappings import REGION_MAP, ALL_SPLITS

COUNTIES_PATH = './geo_data/PEP_2016_PEPANNRES_with_ann.csv'
COUNTIES = pd.read_csv(COUNTIES_PATH, skiprows=1, encoding = 'ISO-8859-1')[['Geography', 'Population Estimate (as of July 1) - 2016']].copy()
COUNTIES['rank'] = COUNTIES['Population Estimate (as of July 1) - 2016'].sort_values(ascending=False).rank(ascending=False)
COUNTIES['state'] = COUNTIES['Geography'].str.split(', ', expand=True)[1]

class GeoSplitter:
	
	min_projects = 5
	grouper = pd.Grouper(key='Project Posted Date', freq='2W')

	def __init__(self, df):
		self.df = df.copy() # initialize with merged tech_df
		self.df['Project Posted Date'] = pd.to_datetime(self.df['Project Posted Date'])
		self.df_county_merge()

	def apply_map(self, map_on_col, map_to_col, map_def):
		self.df[map_to_col] = self.df[map_on_col].map(map_def)

	def df_county_merge(self):
		self.df['School County'] = self.df['School County'].str.replace(r"(\s\(.*?\))", '')
		self.df['county_full'] = self.df['School County'] + ' County, ' + self.df['School State']
		self.df = self.df[~self.df['county_full'].isnull()].copy()
		unmatched = ~self.df['county_full'].isin(COUNTIES['Geography'])
		def get_match(x):
			filtered = COUNTIES[COUNTIES['state'] == x['School State']]
			return process.extractOne(x['School County'], filtered['Geography'], scorer=fuzz.token_sort_ratio)[0]
		self.df.loc[unmatched, 'county_full'] = self.df[unmatched].apply(get_match, axis=1)
		self.df = self.df.merge(COUNTIES, left_on='county_full', right_on='Geography', how='left')

	# split - list
	def get_split_df(self, split, column, split_name):
		in_split = 'in_{}'.format(split_name)
		not_in_split = 'not_{}'.format(split_name)
		total_split = 'total_{}'.format(split_name)
		self.df[split_name] = self.df[column].isin(split).replace({True: in_split, False: not_in_split})
		group_split = self.df.groupby([self.grouper, split_name]).size().unstack().fillna(0)
		try:
			group_split[total_split] = group_split[in_split] + group_split[not_in_split]
		except KeyError:
			# there are no projects in this split
			group_split[in_split] = 0
			group_split[total_split] = group_split[in_split] + group_split[not_in_split]
		group_split = group_split.join(group_split.divide(group_split[total_split], axis='index'), rsuffix='_rel')
		group_split = group_split[group_split[total_split] > self.min_projects].copy()
		return group_split		

	# either rolling or cumulative
	def calc_ticker(self, split_df, split_name, shift=1, window=6, rolling=True):
		in_split = 'in_{}'.format(split_name)
		not_in_split = 'not_{}'.format(split_name)
		if rolling:
			split_over_time = self.rolling_proportion(split_df, in_split, not_in_split, window)
		else:
			split_over_time = self.cumulative_proportion(split_df, in_split, not_in_split)
		shifted = split_over_time.shift(shift)
		ticker = (split_over_time - shifted)[shift:] # change in percent 
		return ticker

	def rolling_proportion(self, split_df, in_split, not_in_split, window=6):
		return (split_df[in_split].rolling(window=window).sum()/
			   (split_df[not_in_split].rolling(window=window).sum() + 
				split_df[in_split].rolling(window=window).sum()))

	def cumulative_proportion(self, split_df, in_split, not_in_split):
		return (split_df[in_split].cumsum()/
			   (split_df[not_in_split].cumsum() + split_df[in_split].cumsum()))

	def get_trend_magnitude(self, split_df, split_name):
		in_split = 'in_{}'.format(split_name)
		not_in_split = 'not_{}'.format(split_name)
		split_over_time = self.cumulative_proportion(split_df, in_split, not_in_split)
		return (split_over_time.max() - split_over_time.min())

	def get_consecutive_directionality(self, ticker_values):
		consecutive_up = []
		consecutive_down = []
		in_up = False
		in_down = False
		current = []
		for d,v in ticker_values.iteritems():
			if ((v > 0) and (in_up)) or ((v < 0) and (in_down)):
				current.append(d.strftime("%Y-%m-%d"))
			elif (v > 0) and not (in_up):
				if len(current) > 2:
					consecutive_down.append(current)
				in_up = True
				in_down = False
				current = [d.strftime("%Y-%m-%d")]
			elif (v < 0) and not (in_down):
				if len(current) > 2:
					consecutive_up.append(current)
				in_down = True
				in_up = False
				current = [d.strftime("%Y-%m-%d")]
		return consecutive_up, consecutive_down


class GeoMeta:

	# splits --> dict with split_name: {'column': col, 
	#	 								'split':list, populate results}
	# accepted grouper values: 
	# 2w, 1m, 3m, 1y
	TWO_WEEKS = 1
	ONE_MONTH = 2
	THREE_MONTHS = 6
	SIX_MONTHS = 13
	ONE_YEAR = 26
	window_sizes = [1, 2, 6, 13, 26]
	shift_sizes = [1, 2, 6, 13, 26]


	def __init__(self, df):
		self.splitter = GeoSplitter(df)
		self.splits = {}
		self.apply_map("School State", "region", REGION_MAP)

	def apply_map(self, map_on_col, map_to_col, map_def):
		self.splitter.apply_map(map_on_col, map_to_col, map_def)

	def get_all_splits(self):
		for split_name, split_def in ALL_SPLITS.items():
			self.split_on(split_name, split_def['column'], split_def['list'])

	def get_all_tickers(self):
		for split_name in self.splits:
			self.get_all_permutations(split_name)

	def split_on(self, split_name, split_col, split_on):
		split_df =  self.splitter.get_split_df(split_on, split_col, split_name)
		self.splits[split_name] = {}
		self.splits[split_name]['split_col'] = split_col
		self.splits[split_name]['split_on'] = split_on
		self.splits[split_name]['split_df'] = split_df
		self.splits[split_name]['ticker'] = {'rolling': {},
						     'cumulative': {}}
	
	def get_split_df(self, split_name):
		try:
			return self.splits[split_name]['split_df']
		except KeyError:
			print("Split {} does not exist".format(split_name))

	def get_projects_in_split(self, split_name):
		in_split = 'in_{}'.format(split_name)
		not_in_split = 'in_{}'.format(split_name)
		return self.splitter.df[self.splitter.df[split_name]==in_split].copy()

	def plot_splits(self, trend, plot=True):
		df = None
		splits = self.find_trendiest()
		split_names = []
		line_pos_dict = {}
		for split in splits:
			split_names.append(split[1])
			if df is None:
				df, line_pos = self.plot_split(split[1], plot=False)
			else:
				tmp, line_pos = self.plot_split(split[1], plot=False)
				df = pd.concat([df, tmp])
			line_pos_dict[split[1]] = line_pos
		plot_config = {'kwargs':{'split_names':split_names, 'line_pos_dict': line_pos_dict},
					   'df':df}
		if not plot:
			return plot_config
		fig = pf.plot_splits(df, trend, split_names=split_names)
		plotly.offline.iplot(fig)

	def plot_rolling_splits(self, trend, window, plot=True):
		df = pd.DataFrame()
		splits = self.find_trendiest()
		split_names = []
		for split in splits:
			split_names.append(split[1])
			df[split[1]] = self.plot_rolling_split(split[1], window, plot=False)
		plot_config = {'kwargs':{'split_names':split_names, 'window': window},
					   'df':df}
		if not plot:
			return plot_config
		fig = pf.plot_rolling_splits(df, trend, window=window, split_names=split_names)
		plotly.offline.iplot(fig)


	def plot_cumulative_splits(self, trend, plot=True):
		df = pd.DataFrame()
		splits = self.find_trendiest()
		split_names = []
		for split in splits:
			split_names.append(split[1])
			df[split[1]] = self.plot_cumulative_split(split[1], plot=False)
		plot_config = {'kwargs':{'split_names':split_names},
					   'df':df}
		if not plot:
			return plot_config
		fig = pf.plot_cumulative_splits(df, trend, split_names=split_names)
		plotly.offline.iplot(fig)


	def plot_split(self, split_name, plot=True):
		split_df = self.splits[split_name]['split_df']
		in_split = 'in_{}'.format(split_name)
		not_in_split = 'not_{}'.format(split_name)
		total_split = 'total_{}'.format(split_name)
		bottom_split = 'bottom_{}'.format(split_name)
		split_prop = split_df[in_split].sum()/float(split_df[total_split].sum())
		temp = split_df[[in_split, not_in_split,total_split]].copy()
		temp[[in_split, not_in_split, total_split]] = temp/float(temp[total_split].max())
		temp[bottom_split] = split_prop - split_prop*temp[total_split]
		if not plot:
			return temp, split_prop
		ax = temp[[in_split, not_in_split]].plot.bar(stacked=True, figsize=(20,10), bottom=temp[bottom_split], title=split_name)
		ax.plot([0, len(temp)], [split_prop, split_prop], 'k-', lw=2)
		
	def get_split_ticker(self, split_name, shift=1, window=6, rolling=True):
		split_df = self.splits[split_name]['split_df']
		ticker = self.splitter.calc_ticker(split_df, split_name, shift, window, rolling)
		if rolling:
			if not window in self.splits[split_name]['ticker']['rolling']:
				self.splits[split_name]['ticker']['rolling'][window] = {}
			self.splits[split_name]['ticker']['rolling'][window][shift] = ticker
		else:
			self.splits[split_name]['ticker']['cumulative'][shift] = ticker
		return ticker

	def find_trendiest(self, as_df=False):
		trends = []
		for split in self.splits:
			trend_mag = self.splitter.get_trend_magnitude(self.splits[split]['split_df'], split)
			trends.append((trend_mag, split))
		trends.sort(reverse=True)
		if as_df:
			trends = pd.DataFrame(trends, columns=['trend_mag', 'split'])
		return trends

	def plot_rolling_ticker(self, split_name, shift=1, window=6):
		split = self.splits[split_name]
		split_df = split['split_df']
		try:
			over_time = self.splits[split_name]['ticker']['rolling'][window][shift]
			over_time.plot(figsize=(10,5))
		except KeyError:
			print("please generate the ticker first, or run get_all_permutations(split_name)")

	def plot_cumulative_ticker(self, split_name, shift=1):
		split = self.splits[split_name]
		split_df = split['split_df']
		try:
			over_time = self.splits[split_name]['ticker']['cumulative'][shift]
			over_time.plot(figsize=(10,5))	
		except KeyError:
			print("please generate the ticker first, or run get_all_permutations(split_name)")

	def plot_rolling_split(self, split_name, window=6, plot=True):
		in_split = 'in_{}'.format(split_name)
		not_in_split = 'not_{}'.format(split_name)
		split_df = self.splits[split_name]['split_df']
		over_time = self.splitter.rolling_proportion(split_df, in_split, not_in_split, window=window)
		if plot:
			over_time.plot(figsize=(10,5))
		return over_time

	def plot_cumulative_split(self, split_name, plot=True):
		in_split = 'in_{}'.format(split_name)
		not_in_split = 'not_{}'.format(split_name)
		split_df = self.splits[split_name]['split_df']
		over_time = self.splitter.cumulative_proportion(split_df, in_split, not_in_split)
		if plot:
			over_time.plot(figsize=(10,5))
		return over_time

	def get_all_permutations(self, split_name):
		for window_shift in itertools.product(self.window_sizes, self.shift_sizes):
			self.get_split_ticker(split_name, shift=window_shift[1], window=window_shift[0])
			self.get_split_ticker(split_name, shift=window_shift[1], rolling=False)

	def get_consecutive_rolling_ticker_values(self, split_name, shift=1, window=6):
		try:
			ticker = self.splits[split_name]['ticker']['rolling'][window][shift]
			return self.splitter.get_consecutive_directionality(ticker)
		except KeyError:
			print("please generate the ticker first")

	def get_consecutive_cumulative_ticker_values(self, split_name, shift=1):
		try:
			ticker = self.splits[split_name]['ticker']['cumulative'][shift]
			return self.splitter.get_consecutive_directionality(ticker)
		except KeyError:
			print("please generate the ticker first")
