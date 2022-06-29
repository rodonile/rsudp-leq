import sys
from datetime import timedelta, datetime
from dateutil import tz
import rsudp.raspberryshake as rs
from rsudp import printM, printW, printE
from rsudp import COLOR, helpers
from rsudp.test import TEST
import numpy as np

import random
def probability(prob):
    return random.random() < prob

# set the terminal text color to green
COLOR['current'] = COLOR['green']


class Alert_Leq_IIR(rs.ConsumerThread):
	"""
	A data consumer class that listens to a specific incoming data channel
	and calculates a recursive STA/LTA (short term average over long term 
	average). If a threshold of STA/LTA ratio is exceeded, the class
	sets the :py:data:`alarm` flag to the alarm time as a
	:py:class:`obspy.core.utcdatetime.UTCDateTime` object.
	The :py:class:`rsudp.p_producer.Producer` will see this flag
	and send an :code:`ALARM` message to the queues with the time set here.
	Likewise, when the :py:data:`alarm_reset` flag is set with a
	:py:class:`obspy.core.utcdatetime.UTCDateTime`,
	the Producer will send a :code:`RESET` message to the queues.

	:param float sta: short term average (STA) duration in seconds.
	:param float lta: long term average (LTA) duration in seconds.
	:param float thresh: threshold for STA/LTA trigger.
	:param bool debug: whether or not to display max STA/LTA calculation live to the console.
	:param str cha: listening channel (defaults to [S,E]HZ)
	:param queue.Queue q: queue of data and messages sent by :class:`rsudp.c_consumer.Consumer`

	"""


	def _find_chn(self):
		'''
		Finds channel match in list of channels.
		'''
		for chn in rs.chns:
			if self.cha in chn:
				self.cha = chn


	def _set_channel(self, cha):
		'''
		This function sets the channel to listen to. Allowed values are as follows:

		- "SHZ"``, ``"EHZ"``, ``"EHN"`` or ``"EHE"`` - velocity channels
		- ``"ENZ"``, ``"ENN"``, ``"ENE"`` - acceleration channels
		- ``"HDF"`` - pressure transducer channel
		- ``"all"`` - resolves to either ``"EHZ"`` or ``"SHZ"`` if available

		:param cha: the channel to listen to
		:type cha: str
		'''
		cha = self.default_ch if (cha == 'all') else cha
		self.cha = cha if isinstance(cha, str) else cha[0]

		if self.cha in str(rs.chns):
			self._find_chn()
		else:
			printE('Could not find channel %s in list of channels! Please correct and restart.' % self.cha, self.sender)
			sys.exit(2)


	def __init__(self, q, a_sta=0.91, a_lta=0.99999, thresh=7, reset=5,
				 debug=True, cha='HZ', db_reference=1e-6, scaling=True,
				 sensitivity=250000000, static_lta=False, lta=10, testing=False, *args, **kwargs):
		"""
		Initializing the alert thread with parameters to set up the recursive
		STA-LTA trigger, filtering, and the channel used for listening.
		"""
		super().__init__()
		self.sender = 'Alert_Leq_IIR'
		self.alive = True
		self.testing = testing

		self.queue = q

		self.init = False

		self.default_ch = 'HZ'
		self.db_reference = db_reference
		self.a_sta = a_sta
		self.a_lta = a_lta
		self.static_lta = static_lta
		self.lta = lta
		self.thresh = thresh
		self.reset = reset
		self.debug = debug
		self.args = args
		self.kwargs = kwargs
		self.raw = rs.Stream()
		self.stream = rs.Stream()
		self.stream_data = np.zeros((0,0))

		self._set_channel(cha)

		self.sps = rs.sps
		self.inv = rs.inv
		self.stalta = 0
		self.v_2_mean_lta = 0
		self.leq_lta = 0
		self.v_2_mean_sta = 0
		self.leq_sta = 0
		self.stalta_trigger_time = 0
		self.maxstalta = 0
		self.exceed = False
		self.scaling = scaling
		self.sensitivity = sensitivity
		
		# Specify stream units
		self.units_raw = rs.UNITS['CHAN'][1]
		printM('Raw stream units are %s' % (self.units_raw.strip(' ')), self.sender)
		if self.scaling:
			self.units = rs.UNITS['VEL'][0]
			printM('Stream scaling from %s to %s' % (self.units_raw.strip(' '), self.units.strip(' ')), self.sender)
		else: 
			self.units = self.units_raw
		printM('Alarm units are %s' % (self.units.strip(' ')), self.sender)


	def _getq(self):
		'''
		Reads data from the queue and updates the stream.

		:rtype: bool
		:return: Returns ``True`` if stream is updated, otherwise ``False``.
		'''
		d = self.queue.get(True, timeout=None)
		self.queue.task_done()
		if self.cha in str(d):
			self.raw = rs.update_stream(stream=self.raw, d=d, fill_value='latest')
			return True
		elif 'TERM' in str(d):
			self.alive = False
			printM('Exiting.', self.sender)
			sys.exit()
		else:
			return False



	def _subloop(self):
		'''
		Gets the queue and figures out whether or not the specified channel is in the packet.
		'''
		while True:
			if self.queue.qsize() > 0:
				self._getq()			# get recent packets
			else:
				if self._getq():		# is this the specified channel? if so break
					break


	def _filter(self):
		'''
		Compute STA and LTA Leq with IIR filter
		Hint: since UDP packets arrive every 250ms, every chunk contains 25 samples
		'''
		# Here we could filter the stream with obspy (e.g. lowpass, bandpass), if required..

		# LTA 
		if self.static_lta:
			# Static LTA as Leq for reference noise level
			self.leq_lta = self.lta
		else:
			# LTA as Leq with IIR filter
			self.v_2_mean_lta = self.a_lta * self.v_2_mean_lta + (1-self.a_lta) * np.power(self.stream_data, 2).mean()
			self.leq_lta = 10 * np.log10(self.v_2_mean_lta / (self.db_reference)**2)

		# STA with IIR filter
		self.v_2_mean_sta = self.a_sta * self.v_2_mean_sta + (1-self.a_sta) * np.power(self.stream_data, 2).mean()
		self.leq_sta = 10 * np.log10(self.v_2_mean_sta / (self.db_reference)**2)

		# STA/LTA
		self.stalta = self.leq_sta - self.leq_lta
		self.stalta_trigger_time = self.stream[0].stats.endtime


	def _is_trigger(self):
		'''
		Figures out it there's a trigger active.
		'''
		if self.stalta > self.thresh:
			if not self.exceed:
				# raise a flag that the Producer can read and modify 
				self.alarm = helpers.fsec(self.stalta_trigger_time)
				self.exceed = True	# the state machine; this one should not be touched from the outside, otherwise bad things will happen
				print()
				printM('Trigger threshold of %s exceeded at %s'
						% (self.thresh, self.alarm.strftime('%Y-%m-%d %H:%M:%S.%f')[:22]), self.sender)
				printM('Trigger will reset when STA/LTA goes below %s...' % self.reset, sender=self.sender)
				COLOR['current'] = COLOR['purple']
				if self.testing:
					TEST['c_alerton'][1] = True
			else:
				pass

			if self.stalta > self.maxstalta:
				self.maxstalta = self.stalta
		else:
			if self.exceed:
				if self.stalta < self.reset:
					self.alarm_reset = helpers.fsec(self.stream[0].stats.endtime)	# lazy; effective
					self.exceed = False
					print()
					printM('Max STA/LTA ratio reached in alarm state: %s' % (round(self.maxstalta, 3)),
							self.sender)
					printM('Leq trigger reset and active again at %s' % (
							self.alarm_reset.strftime('%Y-%m-%d %H:%M:%S.%f')[:22]),
							self.sender)
					self.maxstalta = 0
					COLOR['current'] = COLOR['green']
				if self.testing:
					TEST['c_alertoff'][1] = True

			else:
				pass


	def _print_stalta(self):
		'''
		Print the current max STA/LTA of the stream.
		'''
		if self.debug:
			msg = '\r%s [%s] Threshold: %s; Current max STA/LTA: %.4f; STA: %.4f; LTA: %.4f' % (
					(self.stream[0].stats.starttime + timedelta(seconds=
					 len(self.stream[0].data) * self.stream[0].stats.delta)).strftime('%Y-%m-%d %H:%M:%S'),
					self.sender,
					self.thresh,
					self.stalta,
					self.leq_sta,
					self.leq_lta
					)
			print(COLOR['current'] + COLOR['bold'] + msg + COLOR['white'], end='', flush=True)


	def run(self):
		"""
		Reads data from the queue into a :class:`obspy.core.stream.Stream` object,
		then runs a :func:`obspy.signal.trigger.recursive_sta_lta` function to
		determine whether to raise an alert flag (:py:data:`rsudp.c_alert.Alert.alarm`).
		The producer reads this flag and uses it to notify other consumers.
		"""
		n = 0

		while n > 3:
			self.getq()
			n += 1

		n = 0
		while True:
			self._subloop()

			self.raw = rs.copy(self.raw)	# necessary to avoid memory leak
			self.stream = self.raw.copy()

			if self.scaling:
				# Manually perform the scaling instead of using the deconvolution function
				mean_raw = int(round(np.mean(self.raw[0].data)))
				self.stream_data = (self.raw[0].data - mean_raw) / self.sensitivity
			else:
				mean = int(round(np.mean(self.stream[0].data)))
				self.stream_data = self.stream[0].data - mean


			if n > 3 and self.init == False:
				# Initialize sta and lta values based on first sensor data
				self.v_2_mean_lta = np.power(self.stream_data, 2).mean()
				self.leq_lta = 10 * np.log10(self.v_2_mean_lta / (self.db_reference)**2)
				self.v_2_mean_sta = np.power(self.stream_data, 2).mean()
				self.leq_sta = 10 * np.log10(self.v_2_mean_sta / (self.db_reference)**2)
				self.init = True 

				# print the current STA/LTA calculation
				self._print_stalta()

				# Reset the stream
				self.raw = rs.Stream()
				self.stream = self.raw.copy()


			elif n > 3 and self.init == True:		# With IIR we don't need to wait for the LTA interval for the alert module to start
				# filter
				self._filter()
				# figure out if the trigger has gone off
				self._is_trigger()

				# print the current STA/LTA calculation
				self._print_stalta()

				# Reset the stream
				self.raw = rs.Stream()
				self.stream = self.raw.copy()

			elif n == 0:
				if self.static_lta:
					printM('Starting Alert_Leq_IIR trigger with a_STA=%s, LTA=%s dB, and TRESHOLD=%s dB'
							% (self.a_sta, self.lta, self.thresh), self.sender)
				else:
					printM('Starting Alert_Leq_IIR trigger with a_STA=%s, a_LTA=%s, and TRESHOLD=%s dB'
					   		% (self.a_sta, self.a_lta, self.thresh), self.sender)

			elif n == 3:
				printM('Leq trigger up and running normally.',
					   self.sender)
			else:
				pass

			n += 1
			sys.stdout.flush()