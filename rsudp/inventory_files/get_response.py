from datetime import datetime,timezone
from obspy import read_inventory, UTCDateTime
import sys
import os

user_input_path = input("Enter the path of the inventory file: ")
assert os.path.exists(user_input_path), "I did not find the file at, "+str(user_input_path)
f = open(user_input_path,'r+')
print("Inventory file found!")
f.close()

inventory = read_inventory(user_input_path)
datetime = UTCDateTime(datetime.now(timezone.utc))
response = inventory.get_response("AM.R6833.00.EHZ", datetime)
print("Getting channel response...")
print(response)