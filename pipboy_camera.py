# RasPipBoy: A Pip-Boy 3000 implementation for Raspberry Pi
#	Neal D Corbett, 2013
# V.A.T.S. - Shows images from Raspberry Pi Camera

import pygame, subprocess, io, Image, threading
import config, main

import picamera # From: https://pypi.python.org/pypi/picamera

import pipboy_headFoot as headFoot

class VATS:

	changed = True
	header = pygame.Surface((1,1))
	pageCanvas = pygame.Surface((config.WIDTH,config.HEIGHT))
	doInit = True
	showTint = True
	
	class ThreadClass(threading.Thread):
		
		def run(self):
			
			self.camera = picamera.PiCamera()
			self.camera.resolution = (config.WIDTH,config.HEIGHT)
			self.camera.rotation = 90
			self.camera.brightness = 75
			self.camera.contrast = 80
			
			pageVisible = False
			
			try:
				stream = io.BytesIO()
				
				# Continuously loops while camera is active...
				for foo in self.camera.capture_continuous(stream,format='jpeg'):
					
					# Truncate the stream to the current position (in case prior iterations output a longer image)
					stream.truncate()
					stream.seek(0)
					
					# Only process stream if VATS page is visible:
					if (self.rootParent.currentTab == self.parent) or (self.parent.pageCanvas == None):
						
						pageVisible = True
						
						stream_copy = io.BytesIO(stream.getvalue())
						image = pygame.image.load(stream_copy, 'jpeg')
						self.parent.pageCanvas = image.convert()
						self.parent.changed = True

					# If page is no longer visible, do something?
					elif (pageVisible):
						continue
			finally:
				self.camera.close()
		
	def __init__(self, *args, **kwargs):
		
		self.parent = args[0]
		self.rootParent = self.parent.rootParent
		self.name = "V.A.T.S."		
		
		self.header = headFoot.Header(self)
		
		# Create camera-read thread: (set as daemon, so it'll die with main process)
		camThread = self.ThreadClass()
		camThread.daemon = True
		camThread.parent = self
		camThread.rootParent = self.rootParent
		camThread.start()
		self.camThread = camThread
				
		# Generate footers for mode-pages:
		self.footerImgs = headFoot.genFooterImgs(["Light","Contrast","Exposure","Mode","Tinted",])
		
	# Generate text for header:
	def getHeaderText(self):
		return [self.name, "", main.getTimeStr(),]
	
	def drawPage(self,modeNum):
		pageChanged = self.changed
		self.changed = False
		
		if self.doInit:
			self.doInit = False
		
		return self.pageCanvas, pageChanged
	
	# Called every view changes to this page:
	def resetPage(self,modeNum):
		if config.USE_SOUND:
			config.SOUNDS["camerastart"].play()
	
	# Consume events passed to this page:
	def ctrlEvents(self,events, modeNum):
		for event in events:
			# TAKE PHOTO:
			if (event == 'sel'):
				print "Snap!"
				self.changed = True
			# SCROLL-WHEEL:
			elif (type(event) is list):
				scrollVal = event[2]
				print self.rootParent.modeNum
				if (scrollVal != 0):
					continue
