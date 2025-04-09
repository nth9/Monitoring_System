import os
import sys
import json
import datetime

def delete_old_files(days_ago=None, sensor='temp', delete_flag=None):
    config_path = os.getenv("CONFIG_PATH", "config.json")
    with open(config_path) as f:
        config = json.load(f)


    if delete_flag is None:  # If delete_flag is not provided as argument
        delete_flag = config["delete_old_files"][1]

    if days_ago is None:  # If days_ago is not provided as argument
        days_ago = config["delete_old_files"][0]

    temperature_folder_path = config["temperature_folder_path"]
    limit_switch_folder_path = config["limit_switch_folder_path"]

    path = temperature_folder_path if sensor == 'temp' else limit_switch_folder_path

    today = datetime.datetime.now()
    target_date = today - datetime.timedelta(days=days_ago)

    if delete_flag:
        for filename in os.listdir(path):
            if filename.startswith("Temperature_" if sensor == 'temp' else "Door_status_") and filename.endswith(".csv"):
                date_str = filename.replace("Temperature_" if sensor == 'temp' else "Door_status_", "").replace(".csv", "")
                file_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < target_date:
                    file_path = os.path.join(path, filename)
                    os.remove(file_path)
                    print(f"Deleted file: {filename}")
    else:
        print("Deletion of old files is disabled in the config.")

if __name__ == "__main__":
    if len(sys.argv) > 1:  # If command line arguments are provided
        if len(sys.argv) != 3:
            print("Usage: sudo python3 delete_old_files.py <days_ago> <sensor_type: temp or door>")
            sys.exit(1)

        days_ago = int(sys.argv[1])
        sensor_type = sys.argv[2]
        delete_flag = True

        # Check if the provided sensor type is valid
        if sensor_type not in ['temp', 'door']:
            print("Error: Invalid sensor type. Supported values are 'temp' and 'door'.")
            sys.exit(1)

        delete_old_files(days_ago, sensor=sensor_type, delete_flag=delete_flag)
    else:  # If no command line arguments are provided
        delete_old_files()  # Use config file values
