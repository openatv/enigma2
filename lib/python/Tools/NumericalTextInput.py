from enigma import *

class NumericalTextInput:
    mapping = []
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 0
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 1
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 2
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 3
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 4
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 5
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 6
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 7
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 8
    mapping.append (('a', 'b', 'c', 'A', 'B', 'C')) # 9
    
                                
    def __init__(self, nextFunction):
        self.nextFunction = nextFunction
        self.Timer = eTimer()
        self.Timer.timeout.get().append(self.nextChar)
    
    def getKey(self, num):
        self.Timer.start(1000)
        return self.mapping[num][0]
    
    def nextChar(self):
        self.Timer.stop()
        print "Timer done"
        self.nextFunction()
        