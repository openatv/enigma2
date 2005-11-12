from enigma import *

class NumericalTextInput:
    mapping = []
    mapping.append ("abcABC") # 0
    mapping.append ("abcABC") # 1
    mapping.append ("abcABC") # 2
    mapping.append ("defDEF") # 3
    mapping.append ("ghiGHI") # 4
    mapping.append ("jklJKL") # 5
    mapping.append ("mnoMNO") # 6
    mapping.append ("pqrsPQRS") # 7
    mapping.append ("tuvTUV") # 8
    mapping.append ("wxyzWXYZ") # 9


    
                                
    def __init__(self, nextFunction):
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
        self.nextFunction()
        