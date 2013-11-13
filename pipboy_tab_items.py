# RasPipBoy: A Pip-Boy 3000 implementation for Raspberry Pi
#	Neal D Corbett, 2013
# Class for 'Items' tab

import pygame

import config
import pipboy_headFoot as headFoot

class Tab_Items:
	
	name = "ITEMS"
	modeNames = ["Weapons","Apparel","Aid","Misc","Ammo"]
	
	class Mode_Items:
		
		changed = True
		
		def __init__(self, *args, **kwargs):
			self.parent = args[0]
			self.rootParent = self.parent.rootParent
			self.pageCanvas = pygame.Surface((config.WIDTH, config.HEIGHT))

		def drawPage(self):
			pageChanged = self.changed
			self.changed = False
			if(pageChanged):
				True
			return self.pageCanvas, pageChanged

		# Called every view changes to this page:
		def resetPage(self):
			True
		# Consume events passed to this page:
		def ctrlEvents(self,events):
			True
	
	# Generate text for header:
	def getHeaderText(self):
		return [self.name, "Wg 180/200", "HP 210/210", "DT 19.0", "Caps 3014",]
	
	# Trigger page-functions
	def drawPage(self,modeNum):
		pageCanvas, pageChanged = self.modes[modeNum].drawPage()
		return pageCanvas, pageChanged
	def resetPage(self,modeNum):
		self.modes[modeNum].resetPage()
	def ctrlEvents(self,pageEvents,modeNum):
		self.modes[modeNum].ctrlEvents(pageEvents)
	
	# Tab init:
	def __init__(self, *args, **kwargs):
		self.parent = args[0]
		self.rootParent = self.parent.rootParent
		self.canvas = pygame.Surface((config.WIDTH, config.HEIGHT))
		self.drawnPageNum = -1
		
		# Item-pages all use the same class instance:
		self.itemPage = self.Mode_Items(self)
		self.modes = [self.itemPage,self.itemPage,self.itemPage,self.itemPage,self.itemPage]
		
		for n in range(0,5):
			self.modes[n].pageNum = n
		
		self.header = headFoot.Header(self)
		
		# Generate footers for mode-pages:
		self.footerImgs = headFoot.genFooterImgs(self.modeNames)