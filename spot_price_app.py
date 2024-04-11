#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import pandas as pd
from datetime import date
import plotly.express as px

from dash import Dash, dcc, html
from dash.dependencies import Output, Input


# In[ ]:


#from dash import jupyter_dash
#jupyter_dash.default_mode = 'external'


# In[ ]:


import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
dbc_css = 'https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.2/dbc.min.css'


# In[ ]:


load_figure_template('flatly')


# # Spot price dashboard V2
# 
# ENTSO-E, the European Network of Transmission System Operators, represents 40 electricity transmission system operators from 36 countries across Europe. ENSTO-E maintains the Transparency Platform, which offers free access to real-time data on electricity generation, transportation, and consumption.
# 
# The Transparency Platform has a [dashboard](https://transparency.entsoe.eu/transmission-domain/r2/dayAheadPrices/show?name=&defaultValue=false&viewType=GRAPH&areaType=BZN&atch=false&dateTime.dateTime=08.03.2024+00:00|CET|DAY&biddingZone.values=CTY|10YSE-1--------K!BZN|10Y1001A1001A44P&resolution.values=PT15M&resolution.values=PT30M&resolution.values=PT60M&dateTime.timezone=CET_CEST&dateTime.timezone_input=CET+(UTC+1)+/+CEST+(UTC+2)) that allows users to monitor the spot electricity price in real-time as well as exploring historical prices. This notebook replicates some of the functionalities in the dashboard by developing an *interactive* `Dash` application. The application will display the hourly spot price for all of the bidding zones in Norway (NO1-NO5) for any day in January 2023.

# ### Data
# 
# The data file 2023_01_DayAheadPrices_12.1.D.csv has been downloaded from ENTSO-E, and it contains the electricity price from the day-ahead market (i.e., the spot price) in January 2023 for all member countries of ENTSO-E. The file contains the following columns:
# 
# - **DateTime**: timestamp in Universal Time Central (UTC), e.g., 1st of January 2023 00:30am.
# - **ResolutionCode**: resolution of timestamp, e.g., 15 minutes intervals
# - **AreaCode**: unique area code
# - **AreaTypeCode**: indicates area type, e.g., bidding zone or country
# - **AreaName**: name of area 
# - **MapCode**: unique map code for area
# - **Price**: electricity price in day-ahead market (per MWh), i.e., spot price
# - **Currency**: currency of spot price
# - **UpdateTime**: timestamp to indicate when the observation was last updated

# #### Import and explore data

# In[ ]:


# Import data
df = pd.read_csv('2023_01_DayAheadPrices_12.1.D.csv', sep = '\t')

#df


# In[ ]:


# Check: only one type of area in the data (bidding zones)
#df['AreaTypeCode'].unique()


# In[ ]:


# Check: same number of unique values in AreaCode, AreaName and MapCode
#df['AreaCode'].nunique() == df['AreaName'].nunique() == df['MapCode'].nunique()


# In[ ]:


# Check: number of unique currencies
#df['Currency'].unique()


# In[ ]:


# Note: All countries/bidding zones use EUR, except Ukraine
#df[df['Currency'] == 'UAH']


# In[ ]:


# Check: number of unique resolution codes
#df['ResolutionCode'].unique()


# In[ ]:


# Note: only Austria and Germany offers 15 min resolution (but they also have 60 min resolution)
#df[df['ResolutionCode'] == 'PT15M']['MapCode'].unique()


# #### Clean and visualize data

# In[ ]:


# Convert to datetime
df['DateTime'] = pd.to_datetime(df['DateTime'])

# Extract Norwegian bidding zones
df = df[df['MapCode'].isin(['NO1', 'NO2', 'NO3', 'NO4', 'NO5'])].copy()

# Create date column as string
df['Day'] = df['DateTime'].dt.date.astype(str)

#print(df['MapCode'].nunique())
#print(df['DateTime'].nunique())
#df


# The function `plot_price` takes a day (as a string) and the map code of a bidding zone, and returns a line plot that replicates as close as possible the step chart in the ENTSO-E dashboard. 

# In[ ]:


def plot_price(day, area, data = df):
    
    # Extract subset
    subset = data[(data['MapCode'] == area) & (data['Day'] == day)].copy()  

    # Sort on time and set as index 
    subset.sort_values('DateTime', inplace = True)
    subset.set_index('DateTime', inplace = True)
    
    # Create the desired time range and resample with forward fill
    t_index = pd.DatetimeIndex(pd.date_range(start = subset.index.min(), end = subset.index.max() + pd.Timedelta(minutes = 59), freq = '15min'))
    subset = subset.reindex(t_index, method = 'ffill')

    fig = px.line(
        subset,
        y = 'Price',
        line_shape = 'hv'
    ) 

    fig.update_layout(
        title = 'Day-ahead prices', 
        title_x = 0.5,
        xaxis_title = 'Time [Hours]',
        yaxis_title = 'Price per MTU [EUR / MWh]',
        xaxis_tickformat = '%H:%M',
        hovermode = 'x unified',
    )
    
    fig.update_traces(hovertemplate = 'PT60M: %{y}') 
    
    return fig

#plot_price('2023-01-31', 'NO3')


# ### Application
# 
# The application will allow users to select a (Norwegian) bidding zone and a day, and it will display the hourly spot price in for that day in both a table and graph. The layout of the application will be based on a tab structure, in which the table and graphs are displayed in individual tabs.

# In[ ]:


# Single date picker to select day
datepicker = dcc.DatePickerSingle(
    id = 'my_date',
    min_date_allowed = df['DateTime'].min().date(),       
    max_date_allowed = df['DateTime'].max().date(),       
    date = date(2023, 1, 1)
)

# Radio buttons to select bidding zone
areapicker = dcc.RadioItems(
    id = 'my_area',
    options = [
        {'label' : 'East coast', 'value' : 'NO1'},
        {'label' : 'South coast', 'value' : 'NO2'},
        {'label' : 'Central Norway', 'value' : 'NO3'},
        {'label' : 'Northern Norway', 'value' : 'NO4'},
        {'label' : 'West coast', 'value' : 'NO5'}
    ],
    value = 'NO1'
)


# In[ ]:


tabs = dbc.Tabs(
    children = [
        dbc.Tab([html.Br(), dbc.Container(id = 'my_table')], label = 'Table'),
        dbc.Tab(dcc.Graph(id = 'my_plot'), label = 'Plot')
    ]
)


# In[ ]:


app = Dash(__name__, external_stylesheets = [dbc.themes.FLATLY, dbc_css])
server = app.server

text = """
This dashboard shows the hourly spot electricity price in Norway in January, 2023.

Data is extracted from the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)."""

app.layout = dbc.Container(
    children = [
        
        # Header
        html.H1('Spot price dashboard'),
        dcc.Markdown(text),
                
        html.Br(),
        
        # Row with two columns for selectors and tab structure
        dbc.Row(
            children = [
                dbc.Col([html.Label('Select day:'), datepicker, html.Br(), html.Br(), html.Label('Select area:'), areapicker], width = 2),
                dbc.Col(tabs, width = 10)
            ]
        
        )
        
    ],
    className = 'dbc'
)


@app.callback(
    Output('my_plot', 'figure'),
    Input('my_date', 'date'),
    Input('my_area', 'value')
)
def update_plot(day, area):
    
    return plot_price(day, area)


@app.callback(
    Output('my_table', 'children'),
    Input('my_date', 'date'),
    Input('my_area', 'value')
)
def update_table(day, area, data = df):

    # Extract subset
    subset = data[(data['MapCode'] == area) & (data['Day'] == day)].copy() 
    
    # Sort on date
    subset.sort_values('DateTime', inplace = True)
    
    # Reset index and rename columns
    subset = subset.reset_index().rename(columns = {'Price' : 'Day-ahead price'})

    # Drop date from timestamp
    subset['DateTime'] = subset['DateTime'].dt.strftime('%H:%M')

    # Create the same "MTU" column as in the ENTSO-E dashboard
    subset['temp'] = subset['DateTime'].shift(-1)
    subset.fillna('00:00', inplace = True)
    subset['MTU'] = subset['DateTime'] + ' - ' + subset['temp']

    # Keep only MTU and price column
    subset = subset[['MTU', 'Day-ahead price']].copy()

    return dbc.Table.from_dataframe(subset, striped = True, bordered = True, hover = True)


if __name__ == '__main__':
    app.run(debug = True)


# In[ ]:





# In[ ]:




