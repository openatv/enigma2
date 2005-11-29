from enigma import *

class NumericalTextInput:
    mapping = []
    mapping.append (".,?'\"0-()@/:_") # 0
    mapping.append (" 1") # 1
    mapping.append ("abc2ABC") # 2
    mapping.append ("def3DEF") # 3
    mapping.append ("ghi4GHI") # 4
    mapping.append ("jkl5JKL") # 5
    mapping.append ("mno6MNO") # 6
    mapping.append ("pqrs7PQRS") # 7
    mapping.append ("tuv8TUV") # 8
    mapping.append ("wxyz9WXYZ") # 9
                                
    def __init__(self, nextFunction = None):
        self.nextFunction = nextFunction
        self.Timer = eTimer()
        self.Timer.timeout.get().append(self.nextChar)
        self.lastKey = -1
        self.pos = 0
    
    def getKey(self, num):
        self.Timer.stop()
        self.Timer.start(1000)
        if (self.lastKey != num):
            self.lastKey = num
            self.pos = 0
        else:
            self.pos += 1
            if (len(self.mapping[num]) <= self.pos):
                self.pos = 0
        return self.mapping[num][self.pos]
    
    def nextKey(self):
        self.Timer.stop()
        self.lastKey = -1
    
    def nextChar(self):
        self.Timer.stop()
        print "Timer done"
        self.nextKey()
        if (self.nextFunction != None):
        	self.nextFunction()
        