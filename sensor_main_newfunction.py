import adafruit_dht
import board
import time
import datetime
import csv
import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from gpiozero import Button
from gpiozero.pins.rpigpio import RPiGPIOFactory
from signal import pause
import delete_old_files
import digitalio


class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    


def initialize_sensors(sensor_pins_D):
    global sensors
    sensors = [] 
    pin_success = []
    print("")
    for pin_str in sensor_pins_D:
        pin_number = getattr(board, pin_str)
        #print(type(pin_number))
        try:
            sensor = adafruit_dht.DHT22(pin_number)
            sensor._trig_wait = 1300
            sensor._use_pulseio = True
            sensors.append(sensor)
            pin_success.append(pin_str)
        except Exception as e:
            print(f"{Color.RED}Failed to initialize DHT22 sensor with pin {pin_number}: {e}{Color.END}")
    
    print(f"{Color.GREEN}DHT22 sensor initialized successfully with pin\n{pin_success}{Color.END}")
    return pin_success

def read_temperature(sensor):
    temperature, runtimeerror = None, None

    try:
        temperature = sensor.temperature
    except Exception as e:
        runtimeerror = str(e)
        #print(runtimeerror)
        time.sleep(0.5)
                
    if temperature is not None:
        time.sleep(0.5)
        return temperature, None 
        
    return 'None', runtimeerror

def Aread_temperature(sensor):
    read_retries = 3  # Maximum retries per reading attempt
    temperature, runtimeerror = None, None
    

    while read_retries != 0 and temperature is None :
        read_retries -= 1

        try:
            temperature = sensor.temperature
        except Exception as e:
            runtimeerror = str(e)
            print(str(read_retries) + runtimeerror)
            time.sleep(1)
            
        if runtimeerror == 'Checksum did not validate. Try again.' or runtimeerror == 'A full buffer was not returned. Try again.' or runtimeerror == 'DHT sensor not found, check wiring' : 
            print('A')
            temperature = None
                
        if temperature is not None:
            return temperature, None 
        
    return 'None', runtimeerror


def read_all_temperatures(sensor_error ,upper_bound, lower_bound):
    temperature_data = []
    global temperature_his
    global sensors
    print(f'Temp_his | {temperature_his}')

    for i in range(len(sensor_error)):
        temperature, runtimeerror = read_temperature(sensors[i])

        if temperature != 'None' and ( temperature >=100 or temperature <= 0 ):
            print(f'Sensor {i+1} | Temperature: {temperature}°C')
            runtimeerror = 'Temperature anomaly detected'
            temperature =  temperature_his[i]
        
        if temperature != 'None' :
            if temperature_his[i] != 'None' :
                if abs(temperature - temperature_his[i]) >= 10:
                    #print(f'{Color.RED}Sensor {i+1} | Temperature anomaly detected: {temperature}°C => {Color.END}{temperature_his[i]}°C')
                    print(f'Sensor {i+1} | Temperature: {temperature}°C')
                    runtimeerror = 'Temperature anomaly detected'
                    temperature = temperature_his[i] 
                else :
                    temperature += sensor_error[i]
                    temperature = round(temperature,1)
                    temperature_his[i] = temperature
            else:
                temperature += sensor_error[i]
                temperature = round(temperature,1)
                temperature_his[i] = temperature
        else :
            temperature = temperature_his[i]

        if runtimeerror == 'DHT sensor not found, check wiring':
            temperature = 'None'

        temperature_data.append(temperature)

        if temperature != 'None':
            if runtimeerror is None:
                if temperature < lower_bound:
                    print(f'Sensor {i+1} | Temperature: {Color.BLUE}{temperature}°C{Color.END}')
                elif temperature < upper_bound:
                    print(f'Sensor {i+1} | Temperature: {Color.YELLOW}{temperature}°C{Color.END}')
                else:
                    print(f'Sensor {i+1} | Temperature: {Color.RED}{temperature}°C{Color.END}')
            else :
                print(f'{Color.RED}Sensor {i+1} | {runtimeerror} | {Color.END}Temperature: {temperature_his[i]}°C')                
        else:
            print(f"Sensor {i+1} | {Color.RED}{runtimeerror}{Color.END}")

    return temperature_data

def write_to_csv(path, data, sensor_count=1 , sensor = 'temp'):
    timestamp = data[0]
    current_date = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').date()
    filename = f"Temperature_{current_date}.csv" if sensor == 'temp' else f"Door_status_{current_date}.csv"
    filename = os.path.join(path, filename)
    header_row = ['y-m-d time'] + [f'Sensor{i}' for i in range(1, sensor_count + 1)] if sensor == 'temp' else ['y-m-d time', 'Door_status']

    os.makedirs(path, exist_ok=True)

    if os.path.exists(filename):
        with open(filename, 'r', newline='') as file:
            reader = csv.reader(file)
            first_row = next(reader, [])
            header_count = len(first_row)
            lines = list(reader)

        if header_count < (sensor_count + 1):  # Add 1 for the timestamp column
            lines.insert(0, header_row)  # Insert header row
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerows(lines)
    
    # Write the temperature data   
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        if os.stat(filename).st_size == 0:
            writer.writerow(header_row)
        writer.writerow(data)

def send_email( sub , message , email_config):
    sender_email = email_config['sender_email']
    sender_password = email_config['sender_password']
    recipient_email = email_config['recipient_email']
    smtp_server = email_config['smtp_server']
    smtp_port = email_config['smtp_port']

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ', '.join(recipient_email)
    msg['Subject'] = sub

    msg.attach(MIMEText(message, 'plain'))

    try:
        print(f"{Color.YELLOW}\nSending email to {recipient_email}{Color.END}")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        print(f"{Color.GREEN}Email sent successfully.{Color.END}")
    except Exception as e:
        print(f"{Color.RED}An error occurred while sending email:\n{str(e)}{Color.END}")

def delete_old_files_():
    global last_delete_date
    #print(last_delete_date)
    try:
        now = datetime.datetime.now()  

        if last_delete_date != now.date():
            if now.hour == 0 and now.minute == 1:  # 00:01 AM
                delete_old_files.delete_old_files(sensor='temp')
                delete_old_files.delete_old_files(sensor='door')
                last_delete_date = now.date()
                #print(last_delete_date) 
    except Exception as e:
        print(f"An error occurred while deleting files: {e}")

def door_open():
    global door_path
    global email_config
    print("Door is opened.")
    door_status = 'Open'
    write_to_csv(door_path, [time.strftime('%Y-%m-%d %H:%M:%S'), door_status],sensor='door')
    send_email("Door",f"The door is open.\n {time.strftime('%Y-%m-%d %H:%M:%S')}", email_config)

def door_close():
    global door_path
    print("Door is closed.")
    door_status = 'Close'
    write_to_csv(door_path, [time.strftime('%Y-%m-%d %H:%M:%S'), door_status],sensor='door')

def main():
    global door_path
    global email_config
    global sensors
    global temperature_his
    global last_delete_date

    last_delete_date = None    
    
    config_path = os.getenv("CONFIG_PATH", "config.json")
    with open(config_path) as f:
        config = json.load(f)

    path = config['temperature_folder_path']
    door_path = config['limit_switch_folder_path']
    sensor_pins = [data['pin'] for data in config['sensor_data']]
    sensors_error = [data['error'] for data in config['sensor_data']]
    sensors_update_interval = config['sensors_update_interval']
    email_config = config['email_config']
    upper_bound = email_config['upper_bound']
    lower_bound = email_config['lower_bound']
    email_sent = 0
    last_email_time = time.time()

    factory = RPiGPIOFactory()
    door_switch_pin = config['limit_switch_pin']
    door_switch = Button(door_switch_pin, pin_factory=factory)
    door_switch.when_pressed = door_close
    door_switch.when_released = door_open

    print('time.sleep(10)')
    time.sleep(10)

    sensors = []
    pin_success = initialize_sensors(sensor_pins)
    if len(pin_success) == len(sensor_pins):
        send_email("Auto start" , "Auto start Temperature Monitoring System" , email_config)
        run = True
    else :
        send_email("Auto start" , "Temperature Monitoring System Initialization Failed", email_config)
        run = False

    temperature_his = ['None' for _ in range(len(sensor_pins))]

    while run:
        print(f'{Color.YELLOW}\nReading data from {len(sensors)} sensors...{Color.END}')
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        temperatures = read_all_temperatures(sensors_error ,upper_bound, lower_bound )

        print(f'{Color.GREEN}Writing data to {path}{Color.END}')
        write_to_csv(path, [timestamp] + temperatures, sensor_count=len(sensors) , sensor = 'temp')

        # Check for temperature_his exceeding the upper bound
        high_temperature_sensors = []
        for index, temperature in enumerate(temperature_his, start=1):
            if temperature != 'None' and temperature >= upper_bound:
                high_temperature_sensors.append((index, temperature))

        if high_temperature_sensors:

            current_time = time.time()
            warning_message = '\nWarning: The following Sensors have detected high temperatures'

            if email_sent ==  0 :
                high_time = time.time()
                warning_message += '.'
            else :
                warning_message += f' for {int((current_time - high_time)/60)} minutes.'

            for index, temperature in high_temperature_sensors:
                warning_message += f"\nSensor {index}: {temperature}°C"
            warning_message += f'\n\nTemperature :{temperatures}\nImmediate action is recommended.\nPlease investigate and take necessary measures to address the issue.'
            print(f"{Color.RED}{warning_message}{Color.END}")

            if current_time - last_email_time >= email_sent * 600:  # 10, 20, 30, 40.. ++  minutes
                send_email("Temperature" , warning_message, email_config)
                last_email_time = current_time
                email_sent += 1

        if all(temperature < lower_bound if temperature != 'None' else True for temperature in temperature_his):
            print(f'{Color.GREEN}\nThe temperature is within normal range.{Color.END}')
            email_sent = 0  # Reset email counter if temperatures go back to normal


        delete_old_files_()
        time.sleep(sensors_update_interval)

if __name__ == "__main__":
    main()

