# RasPipBoy: A Pip-Boy 3000 implementation for Raspberry Pi
#	Neal D Corbett, 2013
# Main file

import pygame, os, time, random, math, datetime
from pygame.locals import *
import config

from pipboy_gps import *
from pipboy_tab_stats import *
from pipboy_tab_items import *
from pipboy_tab_data import *
from pipboy_cmdline import *

# Load optional libraries: (these will have been tested by config.py)
if config.USE_SERIAL:
	global serial
	import serial
if config.USE_CAMERA:
	from pipboy_camera import *

def getTimeStr():
	curTime = time.localtime(time.time())
	curTimeStr = "%s.%s.%s, %s:%s" %(curTime.tm_mday, curTime.tm_mon, curTime.tm_year, curTime.tm_hour, '%02d' % curTime.tm_min, )
	return curTimeStr

class Engine:
	
	# Default page-settings:
	torchMode = False
	tabNum = 0
	modeNum = 0
	serBuffer = ""
	
	background = None
	
	def __init__(self, *args, **kwargs):
		
		if(config.USE_SERIAL):
			self.ser = config.ser
			True#self.ser.write("gaugeMode=2")
		
		print "Init pygame:"
		pygame.init()
		pygame.display.init()
		print "(done)"
		
		self.rootParent = self
		self.screenSize = (pygame.display.Info().current_w, pygame.display.Info().current_h)
		self.canvasSize = (config.WIDTH, config.HEIGHT)
		
		print 'Resolution: {0}x{1}'.format(self.screenSize[0], self.screenSize[1])
		print 'Canvas Size: {0}x{1}'.format(self.canvasSize[0], self.canvasSize[1])
		
		# Don't show mouse-pointer:
		pygame.mouse.set_visible(0)
		pygame.display.set_mode(self.screenSize, pygame.FULLSCREEN)
		
		# Block queuing for unused events:
		pygame.event.set_blocked(None)
		for ev in (QUIT,KEYDOWN,MOUSEMOTION,MOUSEBUTTONDOWN):
			pygame.event.set_allowed(ev)
		
		# Set up gps, clock, tab-list:
		self.gpsModule = GpsModuleClass()
		self.clock = pygame.time.Clock()
		
		if config.USE_CAMERA:
			self.tabs = (Tab_Stats(self), VATS(self), Tab_Data(self))
		else:
			self.tabs = (Tab_Stats(self), Tab_Items(self), Tab_Data(self))
		
		self.currentTab = self.tabs[self.tabNum]
		
		self.screen = pygame.display.set_mode(self.screenSize)
		
		self.background = config.IMAGES["background"]
		self.background = pygame.transform.smoothscale(self.background, self.canvasSize)
		
		# Lighten background:
		backAdd = 30
		self.background.fill((backAdd, backAdd, backAdd),None,pygame.BLEND_RGB_ADD)
		'''
		# Untextured background:
		self.background = pygame.Surface(self.canvasSize)
		greyback = 100
		self.background.fill((greyback,greyback,greyback))
		'''
		
		self.background = self.background.convert()
		
		# Scanlines:
		scanline = config.IMAGES["scanline"]
		lineCount = 60 # 48 60 80
		lineHeight = config.HEIGHT / lineCount
		scanline = pygame.transform.smoothscale (scanline, (config.WIDTH, lineHeight))
		
		self.scanLines = pygame.Surface(self.canvasSize)
		yPos = 0
		while yPos < config.HEIGHT:
			self.scanLines.blit (scanline, (0, yPos))
			yPos += lineHeight
		
		# Increase contrast, darken:
		self.scanLines.blit(self.scanLines, (0, 0), None, pygame.BLEND_RGB_MULT)
		
		#scanMult = 0.5
		scanMult = 0.7
		scanMultColour = (scanMult * 255, scanMult * 255, scanMult * 255)
		self.scanLines.fill(scanMultColour, None, pygame.BLEND_RGB_MULT)
		self.scanLines = self.scanLines.convert()
		
		# Start humming sound:
		if config.USE_SOUND:
			config.SOUNDS["start"].play()
			self.humSound = config.SOUNDS["hum"]
			self.humSound.play(loops=-1)
			self.humVolume = self.humSound.get_volume()
		
		# Set up data for generating overlay frames
		distortLine = config.IMAGES["distort"]
		distortLineHeight = (config.HEIGHT / 4)
		distortLine = pygame.transform.smoothscale (distortLine, (config.WIDTH, distortLineHeight))
		distortLine = distortLine.convert()
		distortY = -distortLineHeight
		distortSpeed = (config.HEIGHT / 40)
		self.overlayFrames = []
		
		print "START"
		
		cmdLine = CmdLineClass(self)
	
		bootPrintQueue = [
			"WELCOME TO ROBCO INDUSTRIES (TM) TERMLINK",
			">SET TERMINAL/INQUIRE",
			"",
			"RIT-V300",
			"",
			">SET FILE/PROTECTION=OWNER:RWED ACCOUNTS.F",
			">SET HALT RESTART/MAINT",
			"",
			"Initializing Robco Industries(TM) MF Boot Agent v2.3.0",
			"RETROS BIOS",
			"RBIOS-4.02.08.00 52EE5.E7.E8",
			"Copyright 2201-2203 Robco Ind.",
			"Uppermem: 64 KB",
			"Root (5A8)",
			"Maintenance Mode",
			"",
			">RUN DEBUG/ACCOUNTS.F",
			"**cls",
			"ROBCO INDUSTRIES UNIFIED OPERATING SYSTEM",
			"COPYRIGHT 2075-2077 ROBCO INDUSTRIES",
			"",
		]
		
		# Print Robco boot-up text, interleaving lines with overlay-frame generation:
		lineNum = 0
		canPrint = True
		genOverlays = True
		while (canPrint or genOverlays):
			willPrint = (lineNum < len(bootPrintQueue))
			if canPrint:
				thisLine = bootPrintQueue[lineNum]
				cmdLine.printText(thisLine)
				
				lineNum += 1
				canPrint = (lineNum < len(bootPrintQueue))
				
			# Generate overlays until all required frames are done:
			if genOverlays:
				if (distortY < config.HEIGHT):
					# Use scanlines as base:
					thisFrame = self.scanLines.convert()
					
					# Add animated distortion-line:
					thisFrame.blit(distortLine, (0, distortY), None, pygame.BLEND_RGB_ADD)
					
					# Tint screen:
					thisFrame.fill(config.TINTCOLOUR,None,pygame.BLEND_RGB_MULT)
		
					thisFrame = thisFrame.convert()
					self.overlayFrames.append(thisFrame)
					
					distortY += distortSpeed
				else:
					genOverlays = False
					
		self.animDelayFrames = len(self.overlayFrames)
		self.overlayFramesCount = (2 * self.animDelayFrames)
		self.frameNum = 0
		
		print "END GENERATE"
		
		# Get coordinates:
		self.gpsModule.getCoords(cmdLine)
		
		# Initial map-downloads:
		cmdLine.printText(">MAPS.DOWNLOAD")
		cmdLine.printText("\tDownloading Local map...")
		if config.USE_SOUND:
			config.SOUNDS["tapestart"].play()
		self.rootParent.localMapPage.drawPage()
		cmdLine.printText("\tDownloading World map...")
		if config.USE_SOUND:
			config.SOUNDS["tapestart"].play()
		self.rootParent.worldMapPage.drawPage()
		if config.USE_SOUND:
			config.SOUNDS["tapestop"].play()
		
		cmdLine.printText(">PIP-BOY.INIT")
		
		# Show Pip-Boy logo!
		if (not config.QUICKLOAD):
			self.showBootLogo()
		
		if config.USE_SOUND:
			config.SOUNDS["start"].play()
		print "END INIT PROCESS"
		
		self.currentTab.resetPage(self.modeNum)
		tabCanvas, tabChanged = self.drawTab()
		self.screenCanvas = tabCanvas.convert()
		self.updateCanvas("changetab")

	# Show bootup-logo, play sound:
	def showBootLogo(self):

		bootLogo = pygame.image.load('images/bootupLogo.png')
		self.focusInDraw(bootLogo)
		
		if config.USE_SOUND:
			bootSound = pygame.mixer.Sound('sounds/falloutBootup.wav')
			bootSound.play()
		
		pygame.display.update()
		pygame.time.wait(4200)

	# Do focus-in effect on a page:
	def focusInDraw(self, canvas):
		
		# Reset to first animation-frame:
		self.frameNum = 0
		
		def divRange(val):
			while val >= 1:
				yield val
				val /= 2
		
		# Do focusing-in effect by scaling canvas down/up:
		maxDiv = 4
		hicolCanvas = canvas.convert(24)
		for resDiv in divRange(maxDiv):

			blurImage = pygame.transform.smoothscale(hicolCanvas, (self.canvasSize[0] / resDiv, self.canvasSize[1] / resDiv))
			blurImage = pygame.transform.smoothscale(blurImage, self.canvasSize)
			
			# Add faded sharp image:
			multVal = (255 / (1 * maxDiv))
			drawImage = canvas.convert()
			drawImage.fill((multVal, multVal, multVal), None, pygame.BLEND_RGB_MULT)

			# Add blurred image:
			drawImage.blit(blurImage, (0,0), None, pygame.BLEND_RGB_ADD)
			
			#Add background:
			if (self.background != None):
				drawImage.blit(self.background, (0,0), None, pygame.BLEND_RGB_ADD)

			# Add scanlines:
			drawImage.blit(self.overlayFrames[0], (0,0), None, pygame.BLEND_RGB_MULT)
			
			# Scale up and draw:
			drawImage = pygame.transform.scale(drawImage, self.screenSize)
			self.screen.blit (drawImage, (0,0))
			pygame.display.update()


	# Generate black&white outline-image:
	def updateCanvas(self, updateSound = None):
		
		if config.USE_SOUND and (updateSound != None):
			config.SOUNDS[updateSound].play()
		
		# Do focus-in effect when changing tab (i.e. the lit buttons)
		if (updateSound == "changetab"):
			self.focusInDraw(self.screenCanvas)
		
		# Bake the background into the canvas-image:
		if (self.background != None):
			self.screenCanvas.blit(self.background, (0,0), None, pygame.BLEND_RGB_ADD)
	
	def drawAll(self):
		
		# Start with copy of display-stuff:
		#	(generated by updateCanvas)
		drawImage = self.screenCanvas.convert()
		
		# Don't tint camera-output if VATS mode is set to untinted:
		isVats = (self.currentTab.name == 'V.A.T.S.')
		if (not isVats) or (self.currentTab.showTint):
			
			# Add scanlines/tint:
			useFrame = 0
			if (not isVats):
				useFrame = (self.frameNum - self.animDelayFrames)
				if (useFrame < 0):
					useFrame = 0
			drawImage.blit(self.overlayFrames[useFrame], (0, 0), None, pygame.BLEND_RGB_MULT)
			
		# Make screen extra-bright in torch-mode:
		if(self.torchMode):
			drawImage.fill((0, 128, 0), None, pygame.BLEND_ADD)
		
		drawImage = pygame.transform.scale(drawImage, self.screenSize)
		self.screen.blit (drawImage, (0,0))
		pygame.display.update()
		
		# Vary hum-volume:
		if config.USE_SOUND:
			self.humVolume += (random.uniform(-0.05,0.05))
			if (self.humVolume > config.MAXHUMVOL):
				self.humVolume = config.MAXHUMVOL
			else:
				if (self.humVolume < config.MINHUMVOL):
					self.humVolume = config.MINHUMVOL
			#print self.humVolume
			self.humSound.set_volume(self.humVolume)
		
		self.frameNum += 1
		if (self.frameNum >= self.overlayFramesCount):
			self.frameNum = 0
			
			# Only print FPS every so often, to avoid slowing us down:
			print ("FPS: " + str(self.clock.get_fps()))
	
	drawnPage = []
	def drawTab(self):
		
		pageNums = [self.tabNum,self.modeNum]
		tab = self.currentTab
		
		pageCanvas, pageChanged = tab.drawPage(self.modeNum)
		headerCanvas, headerChanged = tab.header.getHeader()
		differentPage = (self.drawnPage != pageNums)
		
		canvasChange = (pageChanged or headerChanged or differentPage)
		
		if(canvasChange):
			#print ("%s tabChanged: Page:%s Head:%s Different:%s %s" %(tab.name, pageChanged, headerChanged, differentPage, str(pageNums)))
			tab.canvas = pageCanvas.convert()
			tab.canvas.blit(headerCanvas, (0,0), None, pygame.BLEND_ADD)
			tab.canvas.blit(tab.footerImgs[self.modeNum], (0,0), None, pygame.BLEND_ADD)
		
		self.drawnPage = pageNums
		
		return tab.canvas, canvasChange

	def run(self):
		# Main Loop
		running = True
		while running:
			
			tabWas = self.tabNum
			modeWas = self.modeNum
			torchWas = self.torchMode
			moveVals = [0,0,0]
			
			pageEvents = []
			
			doUpdate = False
			updateSound = None
			
			if(config.USE_SERIAL):
				# Run through serial-buffer characters, converting to pygame events if required:
				ser = self.ser
				serMouseDist = 10
				try:
					while ser.inWaiting():
						char = ser.read(1)
						
						if ((char != '\n') and (char != '\r')):
							self.serBuffer = (self.serBuffer + char)
							#print char
						else:
							serBuffer = self.serBuffer
							#print serBuffer
							
							if (serBuffer == 'lighton'): # Torch On
								self.torchMode = True
							elif (serBuffer == 'lightoff'): # Torch Off
								self.torchMode = False
							elif (serBuffer == '1'):
								self.tabNum = 0
							elif (serBuffer == '2'):
								self.tabNum = 1
							elif (serBuffer == '3'):
								self.tabNum = 2
							elif (serBuffer == 'q'):
								self.modeNum = 0
							elif (serBuffer == 'w'):
								self.modeNum = 1
							elif (serBuffer == 'e'):
								self.modeNum = 2
							elif (serBuffer == 'r'):
								self.modeNum = 3
							elif (serBuffer == 't'):
								self.modeNum = 4
							elif (serBuffer == 'select'): # Select
								pageEvents.append('sel')
							elif (serBuffer == 'cursorup'): # List up
								moveVals[2] += 1
							elif (serBuffer == 'cursordown'): # List down
								moveVals[2] -= 1
							elif (serBuffer == 'left'): # Mouse left
								moveVals[0] -= serMouseDist
							elif (serBuffer == 'right'):	# Mouse right
								moveVals[0] += serMouseDist
							elif (serBuffer == 'up'):	# Mouse up
								moveVals[1] += serMouseDist
							elif (serBuffer == 'down'):	# Mouse down
								moveVals[1] -= serMouseDist
							elif (serBuffer.startswith('volts')):	# Battery Voltage
								pageEvents.append(serBuffer)
							elif (serBuffer.startswith('temp')):	# Temperature
								pageEvents.append(serBuffer)
							
							# Clear serial buffer:
							self.serBuffer = ""
				except:
					print ("Serial-port failure!")
					config.USE_SERIAL = False
			
			# Run through Pygame's keyboard/mouse event-queue:
			for event in pygame.event.get():
				#print event
				if event.type == pygame.QUIT:
					running = False
				elif event.type == pygame.MOUSEBUTTONDOWN:
					pageEvents.append('sel')
				elif event.type == pygame.MOUSEMOTION:
					mx, my = pygame.mouse.get_rel()
					moveVals[0] += mx
					moveVals[1] += my
				elif event.type == pygame.KEYDOWN:
					if event.key == pygame.K_ESCAPE:
						running = False
					elif event.key == pygame.K_o: # Torch On
						self.torchMode = True
					elif event.key == pygame.K_p: # Torch Off
						self.torchMode = False
					elif event.key == pygame.K_1:
						self.tabNum = 0
					elif event.key == pygame.K_2:
						self.tabNum = 1
					elif event.key == pygame.K_3:
						self.tabNum = 2
					elif event.key == pygame.K_q:
						self.modeNum = 0
					elif event.key == pygame.K_w:
						self.modeNum = 1
					elif event.key == pygame.K_e:
						self.modeNum = 2
					elif event.key == pygame.K_r:
						self.modeNum = 3
					elif event.key == pygame.K_t:
						self.modeNum = 4
					elif event.key == pygame.K_RETURN:
						pageEvents.append('sel')
					elif event.key == pygame.K_UP: # List up
						moveVals[2] += 1
					elif event.key == pygame.K_DOWN: # List down
						moveVals[2] -= 1
						
			if (moveVals != [0,0,0]):
				pageEvents.append(moveVals)
			
			changedTab = (self.tabNum != tabWas)
			changedMode = (self.modeNum != modeWas)
			changedTorch = (self.torchMode != torchWas)
			
			if(changedTorch):
				if(self.torchMode):
					updateSound = "lighton"
				else:
					updateSound = "lightoff"
			
			if(changedTab):
				updateSound = "changetab"
				
			doUpdate = (changedTorch or changedTab or changedMode)
			
			if(doUpdate):
				self.currentTab = self.tabs[self.tabNum]
				self.currentTab.resetPage(self.modeNum)
			
			# Update current tab, see if it's changed:
			tabCanvas, tabChanged = self.drawTab()
			if doUpdate or tabChanged:
				# updateCanvas will add background to this:
				self.screenCanvas = tabCanvas.convert()
				doUpdate = True
			
			if(doUpdate or (updateSound != None)):
				self.updateCanvas(updateSound)
				
			if (len(pageEvents) != 0):
				self.currentTab.ctrlEvents(pageEvents,self.modeNum)
			
			self.drawAll()

			self.clock.tick(config.FPS)
		
		if(config.USE_SERIAL):
			self.ser.close()
		
		pygame.quit()
		
if __name__ == '__main__': 
	engine = Engine()
	engine.run()

