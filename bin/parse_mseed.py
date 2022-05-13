# Description:
# - input: mseed file (e.g. as outputted from write module of rsudp)
# - output: csv file with norm_timestamp[s], timestamp[UTC], acceleration

from datetime import datetime,timezone, timedelta
from obspy import read, read_inventory, UTCDateTime, Stream
from obspy.io.mseed.util import get_record_information
import sys
import os
import numpy as np
import pandas as pd
import csv
import glob

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
assert os.path.exists(user_input_path), "I did not find the file at, "+str(user_input_path)
f = open(user_input_path,'r+')
print("Mseed file found!")
print("-----------------------")
f.close()

########################################
# Save voltage count samples
########################################
st = read(user_input_path)
nr_traces = len(st)
#print(st)

starttime = np.datetime64(st[0].stats.starttime)
endtime = np.datetime64(st[0].stats.endtime)
seconds = (endtime - starttime).item().total_seconds()
r = np.arange(starttime, endtime, np.timedelta64(10, 'ms'))           # 100sps means 1 sample every 10ms
arr = st[0].data
arr = arr[0:len(arr)-1]
nr_samples = st[0].stats.npts - 1

for i in range(1, nr_traces):
    starttime = np.datetime64(st[i].stats.starttime)
    endtime = np.datetime64(st[i].stats.endtime)
    r_new = np.arange(starttime, endtime, np.timedelta64(10, 'ms'))
    r = np.concatenate((r, r_new)) 
    arr_new = st[i].data
    arr_new = arr_new[0:len(arr_new)-1]
    arr = np.concatenate((arr, arr_new), axis=None) 
    # Update nr_samples
    nr_samples = nr_samples + st[i].stats.npts - 1

########################################
# Deconvolve stream to velocity samples
########################################
st.attach_response(inventory)
deconv_st = st.remove_response(output="VEL")

# Create timestamps-array and fix size 
deconv_arr = deconv_st[0].data
deconv_arr = deconv_arr[0:len(deconv_arr)-1]

for i in range(1, nr_traces):
    deconv_new = deconv_st[i].data
    deconv_new = deconv_new[0:len(deconv_new)-1]
    deconv_arr = np.concatenate((deconv_arr, deconv_new), axis=None) 

########################################
# Compute normalized time interval (for matlab processing)
########################################
r_norm = np.zeros(np.size(r))
starttime = r[0]
for i in range(0, len(r)):
    r_norm[i] = (r[i] - starttime).item().total_seconds()

# Create pandas dataframe with timestamp and values to output as csv 
print("-----------------------")
print("Writing samples to .csv file...")
df_final = pd.DataFrame(r_norm, columns = ['time'])
df_final['time_UTC'] = r
df_final['V_counts'] = arr
df_final['vel'] = deconv_arr
df_final['dB_vel'] = 20 * np.log10(np.abs(deconv_arr) / (1e-9))


# Write to .csv file
#df_final.to_csv(user_input_path + '.csv', index=False)
df_final.to_csv("RS-measurement.csv", index=False)