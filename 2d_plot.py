import sys
sys.path.append("/home/rpiq/.local/lib/python3.10/site-packages")
import os
import json
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import logging
import dash
from dash import dcc, html
from dash.dependencies import Input, Output

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        logging.error("Incorrect date format, should be YYYY-MM-DD")
        sys.exit(1)

def load_config(config_path):
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        logging.error(f"Failed to load config file: {e}")
        sys.exit(1)

def read_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        df['y-m-d time'] = pd.to_datetime(df['y-m-d time'])
        return df
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        sys.exit(1)

def create_plot(df, date_str):
    traces = []
    for sensor in df.columns[1:]:
        trace = go.Scatter(x=df['y-m-d time'], y=df[sensor], mode='lines', name=sensor)
        traces.append(trace)

    traces.append(go.Scatter(x=df['y-m-d time'], y=[lower_bound] * len(df), mode='lines', name='Lower bound', line=dict(color='red', dash='dash'),showlegend=False))
    traces.append(go.Scatter(x=df['y-m-d time'], y=[upper_bound] * len(df), mode='lines', name='Upper bound', line=dict(color='red', dash='dash'),showlegend=False))
    
    layout = go.Layout(
        title=f'Temperature data on {date_str}',
        xaxis=dict(title='Time'),
        yaxis=dict(title='Temperature (°C)'),
        showlegend=True,
        legend=dict(orientation="h"),
        hovermode='closest'
    )

    fig = go.Figure(data=traces, layout=layout)
    return fig

def read_door_status(file_path):
    try:
        df = pd.read_csv(file_path)
        df['y-m-d time'] = pd.to_datetime(df['y-m-d time'])
        return df
    except Exception as e:
        logging.error(f"Error reading door status CSV file: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on error

def get_door_status_html(df):
    if df.empty:
        return html.P("No door status data available for this date.")
    
    door_status_list = []
    for _, row in df.iterrows():
        status_time = row['y-m-d time'].strftime('%H:%M:%S')
        status = row['Door_status']
        color = 'red' if status == 'Open' else 'black'
        door_status_list.append(html.P(f"{status_time} - {status}", style={'font-size': '16px', 'color': color}))
    return door_status_list    

# Initialize Dash app
app = dash.Dash(__name__, title='Temperature Data History')

# Load configuration
config_path = "test07/config.json"
config = load_config(config_path)
temperature_folder_path = config['temperature_folder_path']
door_status_folder_path = config['limit_switch_folder_path']
upper_bound = config['email_config']['upper_bound']
lower_bound = config['email_config']['lower_bound']

app.layout = html.Div([
    dcc.Input(
        id='date-input',
        type='text',
        placeholder='Enter date in YYYY-MM-DD format',
        value='2024-01-01'
    ),
    html.Button('Submit', id='submit-button', n_clicks=0),
    html.Div(id='output-container', children=[
        dcc.Graph(id='temperature-graph', style={'width': '90%', 'height': '88vh', 'display': 'inline-block'}),
        html.Div(children=[
            html.H2("Door Status", style={'text-align': 'center', 'font-size': '20px'}),
            html.Div(id='door-status', style={'height': '88vh', 'overflowY': 'auto', 'padding': '10px','text-align': 'center'})
        ], style={'width': '8%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ])
])

@app.callback(
    [Output('temperature-graph', 'figure'), Output('door-status', 'children')],
    Input('submit-button', 'n_clicks'),
    Input('date-input', 'value')
)
def update_output(n_clicks, date_str):
    if n_clicks > 0:
        validate_date(date_str)
        
        # Temperature data
        temp_file_name = f'Temperature_{date_str}.csv'
        temp_file_path = os.path.join(temperature_folder_path, temp_file_name)

        if not os.path.exists(temp_file_path):
            logging.error(f"No temperature file found for the given date: {temp_file_path}")
            temp_fig = go.Figure()
        else:
            temp_df = read_csv(temp_file_path)
            temp_fig = create_plot(temp_df, date_str)
        
        # Door status data
        door_file_name = f'Door_status_{date_str}.csv'
        door_file_path = os.path.join(door_status_folder_path, door_file_name)

        if not os.path.exists(door_file_path):
            logging.error(f"No door status file found for the given date: {door_file_path}")
            door_status_html = html.P("No door status data available for this date.")
        else:
            door_df = read_door_status(door_file_path)
            door_status_html = get_door_status_html(door_df)

        return temp_fig, door_status_html
    return go.Figure(), ""

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8052)