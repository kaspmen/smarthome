def process_data(topic, payload):
    # Parse the payload and extract the required data
    # Modify this section based on the format of your payload
    data = payload.split("\t")
    temperature = ""
    humidity = ""
    voltage = ""
    wakeup_reason = ""
    motion = ""
    state = ""
    sleep_state = ""

    for item in data:
        if ": " not in item:
            continue

        key, value = item.split(": ")
        key = key.strip()
        value = value.strip()

        if key == "Temperature":
            temperature = value.replace("°C", "")
        elif key == "Humidity":
            humidity = value.replace("%", "")
        elif key == "Voltage":
            voltage = value
        elif key == "Wakeup_Reason":
            wakeup_reason = value
        elif key == "Motion":
            motion = value
        elif key == "State":
            state = value
        elif key == "Sleep_State":
            sleep_state = value

    # Store the data in the SQLite database
    conn = sqlite3.connect(database_file)
    cursor = conn.cursor()

    # Modify the table name and column names based on your database structure
    cursor.execute(
        "INSERT INTO sensor_data (topic, temperature, humidity, voltage, wakeup_reason, motion, state, sleep_state) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (topic, temperature, humidity, voltage, wakeup_reason, motion, state, sleep_state))

    conn.commit()
    conn.close()
