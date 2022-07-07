import sys, os
import time
from datetime import datetime, timedelta
from dateutil import tz
import pytz
from obspy import UTCDateTime
import rsudp.raspberryshake as rs
from rsudp import printM, printW, printE, helpers
from rsudp.test import TEST
import csv
import numpy as np
import pandas as pd
from influxdb_client import InfluxDBClient, Point, WriteApi, WriteOptions

class Write(rs.ConsumerThread):
	"""
	A simple routine to write daily miniSEED data to :code:`output_dir/data`.

	:param cha: channel(s) to forward. others will be ignored.
	:type cha: str or list
	:param queue.Queue q: queue of data and messages sent by :class:`rsudp.c_consumer.Consumer`
	:param bool debug: whether or not to display messages when writing data to disk.
	"""
	def __init__(self, q, data_dir, testing=False, debug=False, cha='all',csv_output=False,
					database_push=True, database_URL="http://localhost:8086", database_BUCKET="rsudp", database_TOKEN="token",
					scaling=True, sensitivity=250000000, db_reference=1e-6):
		"""
		Initialize the process
		"""
		super().__init__()
		self.sender = 'Write'
		self.alive = True
		self.testing = testing
		self.debug = debug
		if self.testing:
			self.debug = True
		self.csv_output = csv_output
		self.db_push = database_push
		self.db_URL = database_URL
		self.db_BUCKET = database_BUCKET
		self.db_TOKEN = database_TOKEN
		self.scaling = scaling
		self.sensitivity = sensitivity
		self.db_reference = db_reference

		self.queue = q

		self.stream = rs.Stream()
		self.outdir = os.path.join(data_dir, 'data').replace('\\', '/')
		
		# Define outfile
		current_timestamp = UTCDateTime.now().timestamp
		current_time_ZH = datetime.fromtimestamp(current_timestamp, tz=pytz.timezone("Europe/Zurich"))
		self.outfile = self.outdir + '/RS-meas-%s.csv' % (current_time_ZH.strftime('%Y-%m-%d-%H.%M.%S'))
		self.header = True 				# flag for setting header to csv file
		
		# InfluxDB writer
		self.client = InfluxDBClient(url=self.db_URL, token=self.db_TOKEN, 
									 org="empa", debug=False)
		self.write_api = self.client.write_api(write_options=WriteOptions(batch_size=1))

		self.chans = []
		helpers.set_channels(self, cha)

		printM('Writing channels: %s' % self.chans, self.sender)
		self.numchns = rs.numchns
		self.stime = 1/rs.sps
		self.inv = rs.inv

		printM('Starting.', self.sender)


	def getq(self):
		'''
		Reads data from the queue and updates the stream.

		:rtype: bool
		:return: Returns ``True`` if stream is updated, otherwise ``False``.
		'''
		d = self.queue.get(True, timeout=None)
		self.queue.task_done()
		if 'TERM' in str(d):
			self.alive = False
			printM('Exiting.', self.sender)
			sys.exit()
		elif str(d.decode('UTF-8')).split(' ')[0] in ['ALARM', 'RESET', 'IMGPATH']:
			pass
		else:
			if rs.getCHN(d) in self.chans:
				self.stream = rs.update_stream(
					stream=self.stream, d=d, fill_value=None)
				return True
			else:
				return False
	
	def set_sps(self):
		'''
		Sets samples per second.
		'''
		self.sps = self.stream[0].stats.sampling_rate


	def slicestream(self):
		'''
		Causes the stream to slice down to the time the last write operation was made.
		'''
		self.stream.slice(starttime=self.last)

	def _tracewrite(self, t):
		'''
		Processing for the :py:func:`rsudp.c_write.Write.write` function.
		Writes an input trace to disk and/or computes 1s-Leq and pushes to influxdb.

		:type t: obspy.core.trace.Trace
		:param t: The trace segment to write to disk.

		'''
		# Datetime64 Timestamps
		starttime_64 = np.datetime64(t.stats.starttime)
		endtime_64 = np.datetime64(t.stats.endtime)
		timestamps = np.arange(starttime_64, endtime_64, np.timedelta64(10, 'ms'))        # 100sps <--> 1 sample every 10ms						

		# Ms timestamps
		starttime_ms = round(t.stats.starttime.timestamp * 1e3)
		endtime_ms = round(t.stats.endtime.timestamp * 1e3)
		timestamps_ms = np.arange(starttime_ms, endtime_ms, 10)       				# 100sps <--> 1 sample every 10ms		
		
		# DEBUG LINES
		#printM("Starttime_ms = %s" % starttime_ms, self.sender)
		#printM("Endtime_ms = %s" % endtime_ms, self.sender)
		#printM("Len timestamp_ms = %s" % len(timestamps_ms), self.sender)

		data = t.data[1:len(t.data)]		# remove first measurement because it was on last chunk already
		#printM("Len data = %s" % len(data), self.sender)
		
		# Adjust mean
		data_mean = int(round(np.mean(data)))
		data = data - data_mean 

		if self.csv_output:
			with open(self.outfile, 'a') as csvfile:
				df = pd.DataFrame(timestamps_ms, columns = ['timestamp_ms'])
				df['timestamp [UTC]'] = timestamps
				df['voltage_counts'] = data

				if self.scaling:
					df['velocity[m/s]'] = data / self.sensitivity

				if self.header:
					df.to_csv(csvfile, header=True, index=False, line_terminator='\n')
					self.header = False
				else:
					df.to_csv(csvfile, header=False, index=False, line_terminator='\n')
				
				if self.debug:
					printM('%s records to %s'
							% (len(t.data), self.outfile), self.sender)

		if self.db_push:
			data[data < self.db_reference * self.sensitivity] = self.db_reference * self.sensitivity	# set value less than dB ref to 0dB
			
			# Datetime timestamps (for influx)
			starttime = datetime.utcfromtimestamp(t.stats.starttime.timestamp)
			endtime = datetime.utcfromtimestamp(t.stats.endtime.timestamp)
			middle = starttime + (endtime-starttime)/2

			# 10s max dB intensity
			#np.seterr(divide = 'ignore') 
			#max_intensity = max(20 * np.log10(np.abs((data/self.sensitivity)/self.db_reference)))
			#np.seterr(divide = 'warn')
			#self.write_api.write(self.db_BUCKET, "empa", {"measurement": "10_seconds", "tags": {"location": "empa_lab"}, "fields": {"max_intensity": max_intensity}, "time":middle})
			## 10s Leq
			#leq = 10 * np.log10(np.power(data / self.sensitivity, 2).mean() / (self.db_reference)**2)
			#self.write_api.write(self.db_BUCKET, "empa", {"measurement": "10_seconds", "tags": {"location": "empa_lab"}, "fields": {"leq": leq}, "time":middle})

			# ~1s max dB intensity and Leq
			data_splits = np.array_split(data, 10)
			i = 0
			for split in data_splits:
				np.seterr(divide = 'ignore') 
				max_intensity = max(20 * np.log10(np.abs((split/self.sensitivity)/self.db_reference)))
				np.seterr(divide = 'warn')
				leq = 10 * np.log10(np.power(split / self.sensitivity, 2).mean() / (self.db_reference)**2)
				timestamp_split = starttime + i*(endtime-starttime)/10
				self.write_api.write(self.db_BUCKET, "empa", {"measurement": "1_second", "tags": {"location": "empa_lab"}, "fields": {"max": max_intensity}, "time":timestamp_split})
				self.write_api.write(self.db_BUCKET, "empa", {"measurement": "1_second", "tags": {"location": "empa_lab"}, "fields": {"leq": leq}, "time":timestamp_split})
				i = i + 1


	def write(self, stream=False):
		'''
		Writes a segment of the stream to disk as miniSEED, and appends it to the
		file in question. If there is no file (i.e. if the program is just starting
		or a new UTC day has just started, then this function writes to a new file).

		:type stream: obspy.core.stream.Stream or bool
		:param stream: The stream segment to write. If ``False``, the program has just started.
		'''
		if not stream:
			self.last = self.stream[0].stats.endtime - timedelta(seconds=5)
			stream = self.stream.copy().slice(endtime=self.last, nearest_sample=False)

		for t in stream:
			self._tracewrite(t)
		if self.testing:
			TEST['c_write'][1] = True

	def run(self):
		"""
		Reads packets and coordinates write operations.
		"""

		self.getq()
		self.set_sps()
		self.getq()
		if self.csv_output:
			printM('CSV output directory: %s' % (self.outdir.replace('\\', '/')), self.sender)
			printM('Beginning CSV output.', self.sender)
		if self.db_push:
			printM('Database URL: %s' % (self.db_URL), self.sender)
			printM('Beginning database push.', self.sender)
		wait_pkts = (self.numchns * 10) / (rs.tf / 1000) 	# comes out to 10 seconds (tf is in ms)

		n = 0
		while True:
			while True:
				if self.queue.qsize() > 0:
					self.getq()
					time.sleep(0.01)		# wait a few ms to see if another packet will arrive
					n += 1
				else:
					self.getq()
					n += 1
					break
			if n >= wait_pkts:
				self.write()
				self.stream = self.stream.slice(starttime=self.last, nearest_sample=False)
				self.stream = rs.copy(self.stream)
				n = 0

				self.getq()
				time.sleep(0.01)		# wait a few ms to see if another packet will arrive
			sys.stdout.flush()
			sys.stderr.flush()