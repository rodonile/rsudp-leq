# Description:
# - input: mseed file (e.g. as outputted from write module of rsudp)
# - output 1: csv file with timestamp, velocity[m/s] and intensity[dB], all samples @100Hz
# - output 2: csv file with timestamp and Leq over 1s intervals

from datetime import datetime,timezone, timedelta
from obspy import read, read_inventory, UTCDateTime, Stream
from obspy.io.mseed.util import get_record_information
import sys
import os
import numpy as np
import pandas as pd
import csv

import random
def probability(prob):
    return random.random() < prob

# Parse inventory file
inventory = read_inventory("R6833_response.xml")
date_time = UTCDateTime(datetime.now(timezone.utc))
response = inventory.get_response("AM.R6833.00.EHZ", date_time)
print(response)

# Open mseed file
print("-----------------------")
print("Files in current folder:")
print(os.listdir())
print("-----------------------")
user_input_path = input("Enter the path of the mseed file: ")
#user_input_path = "AM.R6833.00.EHZ.D.2022.123"      # for now always use the same file
assert os.path.exists(user_input_path), "I did not find the file at, "+str(user_input_path)
f = open(user_input_path,'r+')
print("Mseed file found!")
print("-----------------------")
f.close()

# Deconvolve stream
st = read(user_input_path)
nr_traces = len(st)
print(st)
st.attach_response(inventory)
deconv_st = st.remove_response(output="VEL")

# Create timestamps-array and fix size 
deconv_arr = deconv_st[0].data
deconv_arr = deconv_arr[0:len(deconv_arr)-1]
nr_samples = deconv_st[0].stats.npts - 1
starttime = np.datetime64(deconv_st[0].stats.starttime)
endtime = np.datetime64(deconv_st[0].stats.endtime)
seconds = (endtime - starttime).item().total_seconds()
r = np.arange(starttime, endtime, np.timedelta64(10, 'ms'))           # 100sps means 1 sample every 10ms

for i in range(1, nr_traces):
    starttime = np.datetime64(deconv_st[i].stats.starttime)
    endtime = np.datetime64(deconv_st[i].stats.endtime)
    r_new = np.arange(starttime, endtime, np.timedelta64(10, 'ms'))
    r = np.concatenate((r, r_new)) 
    deconv_new = deconv_st[i].data
    deconv_new = deconv_new[0:len(deconv_new)-1]
    deconv_arr = np.concatenate((deconv_arr, deconv_new), axis=None) 
    nr_samples = nr_samples + deconv_st[i].stats.npts - 1


# Create pandas dataframe with timestamp and values to output as csv 
print("-----------------------")
print("Nr_samples: ", nr_samples)
df = pd.DataFrame(r, columns = ['timestamp'])
df['velocity[m/s]'] = deconv_arr
df['intensity[dB]'] = 20 * np.log10(np.abs(deconv_arr) / (1e-9))
#df.to_csv(user_input_path + '.csv', index=False)

# Create reduced dataframe with Leq data over 1s (dLeq/dt)
hour_start = df.timestamp.dt.hour[0]
minute_start = df.timestamp.dt.minute[0]
second_start = df.timestamp.dt.second[0]
hour_current = hour_start
minute_current = minute_start
second_current = second_start
hour_end = df.timestamp.dt.hour[nr_samples-1]
minute_end = df.timestamp.dt.minute[nr_samples-1]
second_end = df.timestamp.dt.second[nr_samples-1]
print("Start hour, min, sec: ", hour_start, minute_start, second_start)
print("End hour, min, sec: ",hour_end, minute_end, second_end)

reduced_df = pd.DataFrame(columns = ['timestamp', 'Leq_dt[dB]'])
timestamp = df['timestamp'].iloc[0]
end_timestamp = df['timestamp'].iloc[nr_samples-1]
end_timestamp = end_timestamp.replace(microsecond=0)

# First 1s interval
df_interval_1s = df[(df["timestamp"].dt.hour == hour_current) & (df["timestamp"].dt.minute == minute_current) & (df["timestamp"].dt.second == second_current)]
timestamp = df_interval_1s['timestamp'].iloc[0]
reduced_df.loc[0] = [timestamp, 10 * np.log10(np.power(df_interval_1s['velocity[m/s]'], 2).mean() / (1e-9)**2)]

# All other intervals (100 samples)
starting_location = len(df_interval_1s)
reduced_df_index = 1
while timestamp < end_timestamp:
    df_interval_1s = df.loc[starting_location:starting_location + 99]
    timestamp = df_interval_1s['timestamp'].iloc[0]
    reduced_df.loc[reduced_df_index] = [timestamp, 10 * np.log10(np.power(df_interval_1s['velocity[m/s]'], 2).mean() / (1e-9)**2)]
    reduced_df_index = reduced_df_index + 1
    starting_location = starting_location + 100
    if probability(0.001):
        print("Current timestamp: ", timestamp)


#print("-----------------------")
print("Resulting reduced dataframe:")
print(reduced_df)
reduced_df.to_csv(user_input_path + '_REDUCED' + '.csv', index=False)