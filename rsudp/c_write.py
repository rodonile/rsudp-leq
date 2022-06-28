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

class Write(rs.ConsumerThread):
	"""
	A simple routine to write daily miniSEED data to :code:`output_dir/data`.

	:param cha: channel(s) to forward. others will be ignored.
	:type cha: str or list
	:param queue.Queue q: queue of data and messages sent by :class:`rsudp.c_consumer.Consumer`
	:param bool debug: whether or not to display messages when writing data to disk.
	"""
	def __init__(self, q, data_dir, database_URL, database_PORT, testing=False, debug=False, cha='all',csv_output=False,
					database_push=True):
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
		self.db_PORT = database_PORT 

		self.queue = q

		self.stream = rs.Stream()
		self.outdir = os.path.join(data_dir, 'data').replace('\\', '/')
		
		# Define outfile
		current_timestamp = UTCDateTime.now().timestamp
		current_time_ZH = datetime.fromtimestamp(current_timestamp, tz=pytz.timezone("Europe/Zurich"))
		self.outfile = self.outdir + '/RS-meas-%s.csv' % (current_time_ZH.strftime('%Y-%m-%d-%H.%M.%S'))
		
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
		# Add timestamps to data
		#timestamps = np.ones(len(t.data))
		starttime = np.datetime64(t.stats.starttime)
		endtime = np.datetime64(t.stats.endtime)
		timestamps = np.arange(starttime, endtime, np.timedelta64(10, 'ms'))        # 100sps <--> 1 sample every 10ms						
		data = t.data[1:len(t.data)]		# remove first measurement because it was on last chunk already

		# DEBUG LINES
		#printM("Starttime = %s" % starttime, self.sender)
		#printM("Endtime = %s" % endtime, self.sender)
		#printM("Len data = %s" % len(data), self.sender)
		#printM("Len timestamp = %s" % len(timestamps), self.sender)

		if self.csv_output:
			with open(self.outfile, 'a') as csvfile:
				df = pd.DataFrame(timestamps, columns = ['timestamp'])
				df['voltage_counts'] = data
				df.to_csv(csvfile, header=False, index=False, line_terminator='\n')
				if self.debug:
					printM('%s records to %s'
							% (len(t.data), self.outfile), self.sender)

		if self.db_push:
			printM("TODO: pushing into influxdb, URL=%s, PORT=%s" % (db_URL, db_PORT) ,self.sender)


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
		# TODO: print to csv file only if self.csv (csv setting in config file) is true
		printM('CSV output directory: %s' % (self.outdir.replace('\\', '/')), self.sender)
		printM('Beginning output.', self.sender)
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
