# -*- coding: utf-8 -*-
# =======================================
#					iMACRT communication
# =======================================
import os
import socket

from instrument import Instrument
from time import sleep
import types
import logging


class iMACRT(Instrument):
	'''
		None
	'''
	def __init__(self, name, host='192.168.1.6', numcards=3, ch_names=None):
		'''
		   None
		'''
		logging.info(__name__ + ' : Initializing instrument iMACRT')
		Instrument.__init__(self, name, tags=['physical','Temperature'])

		self._numcards = int(numcards)

		self._localhost = ''
		self._localport = 12000 # messages are received by client at this port

		self._host = host
		self._remoteport = self._localport+int(self._host.split('.')[-1])		# messages are send by client to this port
		
		# # --- set the name of the channels 
		# if ch_names:
			# if type(ch_names)==types.StringType:
				# self._names_len = 1
			# else:
				# self._names_len = len(ch_names)
				
		# if (ch_names) and (self._names_len==self._numcards):
			# self._names=ch_names
		# else:
			# self._names=('','','')
			
		### FUNCTION 
		self.add_function('get_all')
	
		### PARAMETERS 
		self.add_parameter('IP_address',type=types.StringType, flags=Instrument.FLAG_GET)
		self.add_parameter('Head_Name',type=types.StringType, flags=Instrument.FLAG_GET)
		self.add_parameter('Date',type=types.StringType, flags=Instrument.FLAG_GET)
		self.add_parameter('Time',type=types.StringType, flags=Instrument.FLAG_GET)

		self.get_IP_address()
		self._type=self.get_Head_Name()[:3]
		if self._type == 'MMR':
			self.add_parameter('Temperature',type=types.FloatType,flags=Instrument.FLAG_GET,units='K')
			self.add_parameter('Name',type=types.StringType,flags=Instrument.FLAG_GETSET)
			self.add_parameter('Resistance',type=types.FloatType,flags=Instrument.FLAG_GET,units='Ω')
			self._param_period = 3
			
			self._param_dict = {'R':1,'T':2}
			
		elif self._type == 'MGC':
			self.add_parameter('on',type=types.BooleanType,flags=Instrument.FLAG_GETSET,)
			self.add_parameter('setpoint',type=types.FloatType,flags=Instrument.FLAG_GETSET,units='K')
			self.add_parameter('P',type=types.FloatType,flags=Instrument.FLAG_GETSET,units='W/K')
			self.add_parameter('I',type=types.FloatType,flags=Instrument.FLAG_GETSET,units='Hz')
			self.add_parameter('D',type=types.FloatType,flags=Instrument.FLAG_GETSET,units='s')
			self.add_parameter('max_power',type=types.FloatType,flags=Instrument.FLAG_GETSET,units='W')
			self.add_parameter('Resistance',type=types.FloatType,flags=Instrument.FLAG_GETSET,units='Ω')
			self.add_parameter('mmr3_Unit',type=types.StringType,flags=Instrument.FLAG_GETSET)
			self.add_parameter('mmr3_Channel',type=types.IntType,flags=Instrument.FLAG_GETSET)

			self._param_period = 12
			self._param_dict = {'ON':1,'setpoint':2,'P':4,'I':5,'D':6,'Pmax':7,'R':8,'name':11,'ch':12}
			

		elif self._type == 'iMA':
			print 'this iMACRT unit is disconnected'
			return
		else:
			print 'unknown device'
			return
		self.get_all()
		self._interrogation = False

# --- Get all the parameters when qtlab start 

	def get_all(self):
		'''
		readout values

		Input:
			None

		Output:
			None
		'''
		if self._type != self.get_Head_Name()[:3]:
			self.remove()
		self._interrogation = True
		_param_list = self.get_parameter_names()
		_param_list.sort()
		
		
		for param in _param_list[2:]:
				sleep(0.001)
				self.get(param)
		self._interrogation = False

		
# --- Function to send messages

	def _send(self, message, recv=False,verbose=False):
		sout = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sout.connect((self._host, self._remoteport))
		if verbose:
			print 'sending: %s' % message
		sout.sendall(message)
		sout.close()
		if recv:
			sn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			sn.bind((self._localhost, self._localport))
			sn.settimeout(1) # may have to change 1 into 1000
			try:
				reply = sn.recvfrom(548)
				if verbose:
					print 'received: %r' % reply[0]
			except:
				print 'timeout'
				reply = ['0']
			finally:
				sn.close()
			return reply[0]		
			
# --- get one parameter depending on the index 

	def choose_param(self,k):
		message = 'MACRTGET %d' % (k)
		return self._send(message,recv = True)

# --- get parameters depending the the type 		
# --- Note that ch is the channel number which is equal to (0,1,2)
		
	def interrogate(self, ch, param):
		if param not in self._param_dict:
			return 'parameter not defined'
		if self._type == 'MMR' : 
			message = 'MACRTGET %d' % (3*self._param_dict[param]+ch)
		elif self._type == 'MGC' : 
			message = 'MACRTGET %d' % (12*ch + self._param_dict[param])
		return self._send(message, recv=True)
		
# --- set parameters depending the the type 

	def submit(self, ch, param, val):
		if param not in self._param_dict:
			return 'parameter not defined'
		if self._type == 'MMR' : 
			message = 'MACRTSET %d' % (3*self._param_dict[param]+ch)
		elif self._type == 'MGC' : 
			message = 'MACRTSET %d' % (12*ch + self._param_dict[param])
		return self._send(message, recv=True)

###
#General parameters
###
	def do_get_IP_address(self):
		return self._host

	def do_get_Head_Name(self):
		return self._send('*IDN',recv=True)
		
	def do_get_Date(self):
		return self._send('DATE ?',recv = True)
		
		
	def do_set_Date(self,mm_dd_yy):
		self._send('DATE '+ mm_dd_yy,recv = True)
		
	def do_get_Time(self):
		return self._send('TIME ?',recv = True)
	
	def do_set_Time(self,hh_mm_ss):
		self._send('TIME '+ hh_mm_ss,recv = True)

#Parameters for MMR
	def do_get_Temperature(self, channel):
		# if not self._interrogation:
			# self._interrogation = True
			# self.get('ch%d_Resistance'%(channel))
			# self._interrogation = False
		return float(self.interrogate(channel,'T'))

	def do_get_Resistance(self, channel):
		# if not self._interrogation:
			# self._interrogation = True
			# self.get('ch%d_Temperature'%(channel))
			# self._interrogation = False
		return float(self.interrogate(channel,'R'))
		
# test 



	# def do_get_Name(self, channel):
		# return self._names[channel-1]

	# def do_set_Name(self,  value, channel):
		# self._names[channel-1] = value

#Parameters for MGC
	def do_get_on(self, channel):
		return int(float(self.interrogate(channel,'ON')))
	def do_get_setpoint(self, channel):
		return float(self.interrogate(channel,'setpoint'))
	def do_get_P(self, channel):
		return float(self.interrogate(channel,'P'))
	def do_get_I(self, channel):
		return float(self.interrogate(channel,'I'))
	def do_get_D(self, channel):
		return float(self.interrogate(channel,'D'))
	def do_get_max_power(self, channel):
		return float(self.interrogate(channel,'Pmax'))
	def do_get_Resistance(self, channel):
		return float(self.interrogate(channel,'R'))
	def do_get_mmr3_Unit(self, channel):
		return self.interrogate(channel,'name')
	def do_get_mmr3_Channel(self, channel):
		return int(float(self.interrogate(channel,'ch')))+1
	def do_set_on(self,val,channel):
		self.submit(channel,'ON',int(val))
	def do_set_setpoint(self,val,channel):
		self.submit(channel,'setpoint',val)
	def do_set_P(self,val,channel):
		self.submit(channel,'P',val)
	def do_set_I(self,val,channel):
		self.submit(channel,'I',val)
	def do_set_D(self,val,channel):
	   self.submit(channel,'D',val)
	def do_set_max_power(self,val,channel):
		self.submit(channel,'Pmax',val)
	def do_set_Resistance(self,val,channel):
		self.submit(channel,'R',val)
	def do_set_mmr3_Unit(self,val,channel):
		self.submit(channel,'name','"'+val[:13]+'"')
	def do_set_mmr3_Channel(self,val,channel):
		self.submit(channel,'ch',val-1)
