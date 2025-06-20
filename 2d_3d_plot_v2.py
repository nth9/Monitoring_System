import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objs as go
import json
import numpy as np
import os

def readdata_fromfile(file_path , printerror = True):
    try:
        temperature_data = pd.read_csv(file_path)
        return temperature_data
    except FileNotFoundError:
        if printerror:
            print(f"Error: File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_file_path(folder_path , fielname):
    current_date = datetime.now().strftime('%Y-%m-%d')
    file_name = f'{fielname+current_date}.csv'
    file_path = os.path.join(folder_path, file_name)
    return file_path

def create_2d_plot(df):
    if df is None:
        return None
    
    global last_time_str
    # Read the last line and extract the timestamp
    last_line = df.iloc[-1]
    last_time_str = last_line['y-m-d time']
    last_time = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S')
    sensor_count = len(last_line) - 1  # Number of sensors excluding timestamp
    df = df.iloc[:, :sensor_count + 1]

    # Filter data for the last xxx seconds
    start_time = last_time - timedelta(seconds=last_seconds)
    df['y-m-d time'] = pd.to_datetime(df['y-m-d time'])
    df = df[(df['y-m-d time'] >= start_time) & (df['y-m-d time'] <= last_time)]

    # Create traces for each sensor
    data = []
    for sensor in df.columns[1:]:
        trace = go.Scatter(x=df['y-m-d time'], y=df[sensor], mode='lines',line_shape='linear', name=f"{sensor}: <b>{df[sensor].iloc[-1]}°C</b>")
        data.append(trace)

    # Add horizontal lines at
    data.append(go.Scatter(x=df['y-m-d time'], y=[lower_bound] * len(df), mode='lines', name='Lower bound', line=dict(color='red', dash='dash'),showlegend=False))
    data.append(go.Scatter(x=df['y-m-d time'], y=[upper_bound] * len(df), mode='lines', name='Upper bound', line=dict(color='red', dash='dash'),showlegend=False))

    # Calculate y-axis range
    y_min = df.select_dtypes(include=np.number).min().min() - 0.5
    y_max = df.select_dtypes(include=np.number).max().max() + 1

    deltaminmax = int((last_seconds)*0.02)

    x_min = df['y-m-d time'].min()
    x_max = df['y-m-d time'].max() + timedelta(seconds=deltaminmax) 

    # Create layout
    layout = go.Layout(title='Temperature Over Time',
                       legend=dict(traceorder='normal', bgcolor='rgba(230, 236, 245, 0.7)', tracegroupgap=10, x=0.01, y=0.99),  # Position legend
                       xaxis=dict(title='Time',range=[x_min, x_max] ),
                       yaxis=dict(title='Temperature', range=[y_min, y_max], dtick = 2 ))

    # Create figure
    fig = go.Figure(data=data, layout=layout)
    return fig

# Create 3D map
def create_3d_map(df,doorOpen):
    if df is None:
        return None

    # Get the last row (excluding timestamp) from the DataFrame
    last_row = df.iloc[-1].drop('y-m-d time')

    data = []
    annotations = []
    for index, pos in enumerate(sensor_pos):
        x, y, z = pos
        temperature = last_row.get(f"Sensor{index+1}")

        if temperature is not None:  # Check if temperature data exists for this sensor
            trace = go.Scatter3d(
                x=[x],
                y=[y],
                z=[z],
                mode='markers',
                marker=dict(
                    size=15,
                    color=[temperature],
                    colorscale=[[0, 'royalblue'],[0.5, 'deepskyblue'],[0.8, 'gold'],[1, 'red']],
                    cmin=Tminmax[0],
                    cmax=Tminmax[1],
                    opacity=1,
                    colorbar=dict(title='Temperature (°C)')  # Add color bar
                ),
                name=f"Sensor{index+1}: {temperature}°C",
                showlegend=False #
            )
            data.append(trace)

            # Add annotation for this sensor
            annotations.append(
                dict(
                    showarrow=False,
                    x=x,
                    y=y,
                    z=z,
                    text=f"Sensor{index+1}:<b>{temperature}°C</b>",
                    xanchor="center",
                    yanchor="top",
                    xshift=0,
                    yshift=-15,
                    opacity=1
                )
            )

    # Create box traces
    for box in boxes:
        dimensions = box["dimensions"]
        position = box["position"]
        color = box["color"]
        opacity = box["opacity"]
        name = box["name"]
        if name == "door" and doorOpen == True:
            color = 'red'

        # Define vertices of the box
        x, y, z = position
        dx, dy, dz = dimensions
        vertices = [
            [x, y, z], [x + dx, y, z], [x + dx, y + dy, z], [x, y + dy, z],
            [x, y, z + dz], [x + dx, y, z + dz], [x + dx, y + dy, z + dz], [x, y + dy, z + dz]
        ]
        
        i= [7, 0, 0, 0, 4, 4, 6, 1, 4, 0, 3, 6]
        j= [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
        k= [0, 7, 2, 3, 6, 7, 1, 6, 5, 5, 7, 2]
  
        # Add mesh to the figure
        box_trace = go.Mesh3d(
            x=[vertex[0] for vertex in vertices],
            y=[vertex[1] for vertex in vertices],
            z=[vertex[2] for vertex in vertices],
            i=i, j=j, k=k,
            opacity=opacity,
            color=color,
            flatshading = True
        )
        data.append(box_trace)

        # Define edges of the box
        edges = [
        [0, 1], [1, 2], [2, 3], [3, 0],
        [4, 5], [5, 6], [6, 7], [7, 4],
        [0, 4], [1, 5], [2, 6], [3, 7]
        ]
        for edge in edges:
            edge_x = [vertices[edge[0]][0], vertices[edge[1]][0]]
            edge_y = [vertices[edge[0]][1], vertices[edge[1]][1]]
            edge_z = [vertices[edge[0]][2], vertices[edge[1]][2]]

            edge_trace= (go.Scatter3d(
                x=edge_x,
                y=edge_y,
                z=edge_z,
                mode='lines',
                line=dict(color=color, width=2 ),
                opacity=0.3,
                showlegend=False #
                )
            )
            data.append(edge_trace)
        
    # Create layout
    layout = go.Layout(
        title='3D Temperature Map',
        scene=dict(
            xaxis=dict(title='', range=[0, room_dims[0]], dtick=1 , showticklabels=False),
            yaxis=dict(title='', range=[0, room_dims[1]], dtick=1 , showticklabels=False ),
            zaxis=dict(title='', range=[0, room_dims[2]], dtick=1 , showticklabels=False ),
            aspectmode='manual',
            aspectratio=dict(x=room_dims[0]/dim_min, y=room_dims[1]/dim_min, z=room_dims[2]/dim_min),
            camera=dict(
                up=dict(x=0, y=0, z=1),
                center=dict(x=0, y=0, z=0),
                eye=dict(x=-0.9, y=-1.9, z=1.1)
            ),
            annotations=annotations
        ),
        margin=dict(l=0, r=0, b=40, t=40),
        #legend=dict(traceorder='normal', tracegroupgap=10, x=0.02, y=0.98),  # Position legend
        #coloraxis=dict(colorbar=dict(title='Temperature (°C)'))  # Position color bar
    )

    # Create figure
    fig = go.Figure(data=data, layout=layout)
    return fig

#####################################################################################

# Load configuration from config.json
with open('test07/config.json') as f:
    config = json.load(f)
temp_folder_path = config["temperature_folder_path"]
door_folder_path = config["limit_switch_folder_path"]
last_seconds = config['last_minutes']*60
temperature_update_interval = config['temperature_update_interval']*1000
sensor_pos = [(data['position'][0], data['position'][1], data['position'][2]) for data in config['sensor_data']]
Tminmax = config["colorbar"]
room_dims = config['room_dimensions']
dim_min = min(room_dims)
boxes = config['boxes']
upper_bound = config['email_config']['upper_bound']
lower_bound = config['email_config']['lower_bound']
last_time_str = ''

#####################################################################################

# Define Dash app
app = dash.Dash(__name__, title='Temperature Data Visualization')

# Define layout
app.layout = html.Div([
    html.H1("Temperature Data Visualization", style={'marginLeft': '50px'}),
    html.Div(id='last-measurement', style={'marginLeft': '50px'}),
    html.Div([
        dcc.Graph(id='2d-plot', style={'width': '46%', 'height': '88vh', 'display': 'inline-block'}),
        dcc.Graph(id='3d-plot', style={'width': '46%', 'height': '88vh', 'display': 'inline-block'}),
        html.Div([
            html.H2("Door Status", style={'text-align': 'center', 'font-size': '20px'}),
            html.Div(id='door-status-list', style={'height': '70vh', 'overflowY': 'auto', 'padding': '10px','text-align': 'center'})
        ], style={'width': '8%', 'display': 'inline-block', 'verticalAlign': 'top'})
    ]),
    dcc.Interval(
        id='interval-component',
        interval=temperature_update_interval,
        n_intervals=0
    )
])

'''
        html.Div(children=[
            html.H2("Door Status", style={'text-align': 'center', 'font-size': '24px'}),
            html.Div(id='door-status', style={'height': '88vh', 'overflowY': 'auto', 'padding': '10px', 'border': '1px solid'})
        ], style={'width': '10%', 'display': 'inline-block', 'verticalAlign': 'top'})
'''

# Define callback to update "Last Measurement" annotation
@app.callback(
    Output('last-measurement', 'children'),
    [Input('interval-component', 'n_intervals')]
)
def update_last_measurement(n):
    global last_time_str
    return html.Div(f'Last Measurement: {last_time_str}')

## Define callback to update graphs and door status
# Define callback to update graphs and door status
@app.callback(
    [Output('2d-plot', 'figure'),
     Output('3d-plot', 'figure'),
     Output('door-status-list', 'children')],
    [Input('interval-component', 'n_intervals')]
)

def update_graph(n):
    temp_file_path = get_file_path(temp_folder_path , 'Temperature_')
    temp_df = readdata_fromfile(temp_file_path, printerror = True)

    door_file_path = get_file_path(door_folder_path , 'Door_status_')
    door_df = readdata_fromfile(door_file_path, printerror = False)

    doorOpen = False
    door_status_list = []

    if door_df is not None:
        status = door_df.iloc[-1].get('Door_status')
        if status == 'Open': doorOpen = True

        for _, row in door_df.iterrows():
            status = row.get('Door_status')
            timestamp_str = row.get('y-m-d time')

            timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            time_str = timestamp.strftime('%H:%M:%S')

            color = 'red' if status == 'Open' else 'black'
            door_status_list.append(html.P(f"{time_str} - {status}", style={'font-size': '16px', 'color': color}))
            #door_status_list.append(f"{time_str} - {status}")
    
    if temp_df is None:
        # Return a blank graph with an error message
        fig =  go.Figure(data=[], layout=go.Layout(title="Temperature Data Visualization", annotations=[
            dict(
                x=0.5,
                y=0.5,
                xref='paper',
                yref='paper',
                text=f"Error: File '{temp_file_path}' not found.",
                showarrow=False,
                font=dict(size=16)
            )
        ]))
        return fig , fig, door_status_list
    else:
        fig2d = create_2d_plot(temp_df)
        fig3d = create_3d_map(temp_df,doorOpen)
    
    return fig2d, fig3d, door_status_list


# Run the app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050 ,debug=True)
    #app.run_server(debug=True)