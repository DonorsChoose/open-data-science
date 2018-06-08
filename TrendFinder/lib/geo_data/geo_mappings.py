REGION_MAP = {"Connecticut": "New England", 
              "Maine": "New England", 
              "Massachusetts": "New England", 
              "New Hampshire": "New England", 
              "Rhode Island": "New England", 
              "Vermont": "New England",
              "New Jersey": "Mid-Atlantic", 
              "New York": "Mid-Atlantic", 
              "Pennsylvania": "Mid-Atlantic",
              "Illinois": "East North Central", 
              "Indiana": "East North Central", 
              "Michigan": "East North Central", 
              "Ohio": "East North Central", 
              "Wisconsin": "East North Central",
              "Iowa": "West North Central", 
              "Kansas": "West North Central", 
              "Minnesota": "West North Central", 
              "Missouri": "West North Central", 
              "Nebraska": "West North Central", 
              "North Dakota": "West North Central",
              "South Dakota": "West North Central",
              "Delaware": "South Atlantic", 
              "Florida": "South Atlantic", 
              "Georgia": "South Atlantic", 
              "Maryland": "South Atlantic", 
              "North Carolina": "South Atlantic", 
              "South Carolina": "South Atlantic",
              "Virginia": "South Atlantic",
              "District of Columbia": "South Atlantic",
              "West Virginia": "South Atlantic",
              "Alabama": "East South Central", 
              "Kentucky": "East South Central", 
              "Mississippi": "East South Central", 
              "Tennessee": "East South Central",
              "Arkansas": "West South Central", 
              "Louisiana": "West South Central", 
              "Oklahoma": "West South Central",  
              "Texas": "West South Central", 
              "Arizona": "Mountain", 
              "Colorado": "Mountain", 
              "Idaho": "Mountain", 
              "Montana": "Mountain", 
              "Nevada": "Mountain", 
              "New Mexico": "Mountain", 
              "Utah": "Mountain", 
              "Wyoming": "Mountain",
              "Alaska": "Pacific", 
              "California": "Pacific", 
              "Hawaii": "Pacific", 
              "Oregon": "Pacific", 
              "Washington": "Pacific"
             }

NORTH_LIST  = ['California', 'Washington', 'Oregon', 'Idaho', 'Montana', 'Wyoming', 
               'Colorado', 'Utah', 'North Dakota', 'South Dakota', 'Minnesota', 'Iowa',
               'Wisconsin', 'Illinois', 'Michigan', 'Indiana', 'Ohio', 'Pennsylvania',
               'New York', 'Vermont', 'New Hampshire', 'Massachusetts', 'Connecticut', 
               'Rhode Island', 'Maine']

# Coastal Regions
COASTAL_LIST = ['South Atlantic', 'Pacific', 'Mid-Atlantic', 'New England']

# Counties in New York City
NYC_LIST = ['Queens County, New York', 'Kings County, New York', 'New York County, New York',
            'Bronx County, New York', 'Richmond County, New York', 'Westchester County, New York',
            'Nassau County, New York']

# Counties in Chicago
CHI_LIST = ['Cook County, Illinois']

# Counties in Los Angeles
LA_LIST = ['Los Angeles County, California']

# Counties in San Francisco
SF_LIST = ['Alameda County, California', 'Contra Costa County, California', 'Marin County, California',
           'Napa County, California', 'San Francisco County, California', 'San Mateo County, California',
           'Santa Clara County, California', 'Solano County, California', 'Sonoma County, California']

# Counties in Houston
HOU_LIST = ['Harris County, Texas', 'Fort Bend County, Texas', 'Montgomery County, Texas', 
			'Brazoria County, Texas', 'Galveston County, Texas', 'Liberty County, Texas', 
			'Waller County, Texas', 'Chambers County, Texas', 'Austin County, Texas']

# Counties in Phoenix
PHX_LIST = ['Maricopa County, Arizona', 'Pinal County, Arizona']

# Counties in Philadelphia
PHI_LIST = ['Philadelphia County, Pennsylvania']

# Counties in San Antonia
SA_LIST = ['Atascosa County, Texas', 'Bandera County, Texas', 'Bexar County, Texas', 'Comal County, Texas', 
           'Guadalupe County, Texas', 'Kendall County, Texas', 'Medina County, Texas', 'Wilson County, Texas']

# Counties in San Diego
SD_LIST = ['San Diego County, California']

DAL_LIST = ['Dallas County, Texas', 'Tarrant County, Texas']

AUS_LIST = [ 'Bastrop County, Texas', 'Caldwell County, Texas', 'Hays County, Texas', 
             'Travis County, Texas', 'Williamson County, Texas']

# JAX_LIST = []

# COL_LIST = []

# IND_LIST = []

# CHA_LIST = []

# SEA_LIST = []

# DEN_LIST = []

# DC_LIST = []

# BOS_LIST = []

# NSH_LIST = []

# DET_LIST = []

# ATL_LIST = []

NON_URBAN_LIST = ['suburban', 'rural']

ALL_SPLITS = {
  'coastal': {
    'column': 'region', 
    'list': COASTAL_LIST
  }, 
  'north': {
    'column': 'School State', 
    'list': NORTH_LIST
  }, 
  'NYC': {
    'column': 'county_full', 
    'list': NYC_LIST
  }, 
  'Chicago': {
    'column': 'county_full', 
    'list': CHI_LIST
  }, 
  'LA': {
    'column': 'county_full', 
    'list': LA_LIST
  }, 
  'SF': {
    'column': 'county_full', 
    'list': SF_LIST
  }, 
  'Houston': {
    'column': 'county_full', 
    'list': HOU_LIST
  }, 
  'Phoenix': {
    'column': 'county_full', 
    'list': PHX_LIST
  }, 
  'Phildelphia': {
    'column': 'county_full', 
    'list': PHI_LIST
  }, 
  'San Antonio': {
    'column': 'county_full', 
    'list': SA_LIST
  }, 
  'San Diego': {
    'column': 'county_full', 
    'list': SD_LIST
  }, 
  'Dallas': {
    'column': 'county_full', 
    'list': DAL_LIST
  }, 
  'Austin': {
    'column': 'county_full', 
    'list': AUS_LIST
  },
  'non-urban': {
    'column': 'School Metro Area',
    'list': NON_URBAN_LIST
  } 
}
