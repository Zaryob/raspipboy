# RasPipBoy: A Pip-Boy 3000 implementation for Raspberry Pi
#    Neal D Corbett, 2013
# 'Radio' page

import pygame
import config

class Mode_Radio:
    
    changed = True
    
    def __init__(self, *args, **kwargs):
        self.parent = args[0]
        self.rootParent = self.parent.rootParent
        self.name = "Radio"
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