import pandas as pd
import numpy as np
import random
import time
from datetime import datetime

path = './DataSets/Cleaned_MergedData.csv'
df = pd.read_csv(path)

stats = {
    col: (df[col].mean(), df[col].std())
    for col in df.columns if df[col].dtype != 'object'
}

axes = ["X1", "Y1", "Z1", "S1"]


process_sequence = [
    "Starting",
    "Prep",
    "Layer 1 Up",
    "Layer 1 Down",
    "Repositioning",
    "Layer 2 Up",
    "Layer 2 Down",
    "Layer 3 Up",
    "Layer 3 Down",
    "End"
]

process_index = 0


counter = 1
state = "idle"


def base_generation():
    data = {}

    for col in stats:
        if col == "No":
            continue

        mean, std = stats[col]
        value = np.random.normal(mean, std)

        if col == "M1_sequence_number":
            data[col] = max(0, int(value))
            continue

        if col == "M1_CURRENT_PROGRAM_NUMBER":
            data[col] = max(1, int(value))
            continue

        if col == "M1_CURRENT_FEEDRATE":
            data[col] = max(0, round(value, 3))
            continue

        if col in ["tool_condition", "machining_finalized", "passed_visual_inspection"]:
            data[col] = int(np.random.choice([0, 1]))
            continue

        if (
            "Output" in col
            or "Voltage" in col
            or "Current" in col
            or "feedrate" in col
            or "pressure" in col
        ):
            value = max(0, value)

        data[col] = round(value, 3)

    return data


def update_process():
    global process_index

    if state == "running":
        if random.random() < 0.2:
            process_index = min(process_index + 1, len(process_sequence) - 1)

    return process_sequence[process_index]



def idle_state(data):
    for axis in axes:
        data[f"{axis}_ActualVelocity"] = 0
        data[f"{axis}_ActualAcceleration"] = 0
        data[f"{axis}_OutputCurrent"] = 0
        data[f"{axis}_OutputVoltage"] = 0
        data[f"{axis}_OutputPower"] = 0
        data[f"{axis}_CommandVelocity"] = 0
        data[f"{axis}_CommandAcceleration"] = 0
        data[f"{axis}_CurrentFeedback"] = 0

    data["tool_condition"] = 1
    data["machining_finalized"] = 0

    return data


def running_state(data):
    process = data["Machining_Process"]

    if "Layer" in process:
        current_mean = 320
        voltage_mean = 60
    elif process == "Prep":
        current_mean = 200
        voltage_mean = 40
    elif process == "Repositioning":
        current_mean = 150
        voltage_mean = 30
    elif process == "Starting":
        current_mean = 100
        voltage_mean = 20
    else:
        current_mean = 80
        voltage_mean = 15

    for axis in axes:
        cmd_v = data.get(f"{axis}_CommandVelocity", 0)

        data[f"{axis}_ActualVelocity"] = round(
            cmd_v + np.random.normal(0, 0.5), 3
        )

        data[f"{axis}_ActualAcceleration"] = round(
            np.random.normal(0, 5), 3
        )

        data[f"{axis}_OutputCurrent"] = round(
            abs(np.random.normal(current_mean, 20)), 3
        )

        data[f"{axis}_OutputVoltage"] = round(
            abs(np.random.normal(voltage_mean, 10)), 3
        )

    data["tool_condition"] = 1
    data["machining_finalized"] = 0

    return data


def fault_state(data):
    data["tool_condition"] = 0

    for axis in axes:
        data[f"{axis}_OutputCurrent"] = round(
            abs(np.random.normal(500, 50)), 3
        )
        data[f"{axis}_OutputVoltage"] = round(
            abs(np.random.normal(80, 15)), 3
        )

    return data


def finished_state(data):
    for axis in axes:
        data[f"{axis}_ActualVelocity"] = 0
        data[f"{axis}_ActualAcceleration"] = 0
        data[f"{axis}_OutputCurrent"] = 0
        data[f"{axis}_OutputVoltage"] = 0
        data[f"{axis}_OutputPower"] = 0

    data["machining_finalized"] = 1
    data["tool_condition"] = 1
    data["passed_visual_inspection"] = int(np.random.choice([0, 1]))

    return data


def update_state():
    global state, process_index

    if state == "idle":
        if random.random() < 0.3:
            state = "running"
            process_index = 0

    elif state == "running":
        r = random.random()
        if r < 0.1:
            state = "fault"
        elif process_index == len(process_sequence) - 1:
            state = "finished"

    elif state == "fault":
        if random.random() < 0.5:
            state = "idle"

    elif state == "finished":
        if random.random() < 0.7:
            state = "idle"


def generate_data():
    global counter, state

    update_state()

    data = base_generation()

    data["No"] = counter
    counter += 1

    if state == "running":
        data["Machining_Process"] = update_process()
    elif state == "fault":
        data["Machining_Process"] = process_sequence[process_index]
    elif state == "finished":
        data["Machining_Process"] = "End"
    else:
        data["Machining_Process"] = "None"

    if state == "idle":
        data = idle_state(data)
    elif state == "running":
        data = running_state(data)
    elif state == "fault":
        data = fault_state(data)
    elif state == "finished":
        data = finished_state(data)

    for axis in axes:
        v = data.get(f"{axis}_OutputVoltage", 0)
        c = data.get(f"{axis}_OutputCurrent", 0)
        data[f"{axis}_OutputPower"] = round(v * c, 3)

    data["timestamp"] = datetime.now().isoformat()
    data["state"] = state

    return data


while True:
    d = generate_data()
    print(d)
    time.sleep(1)