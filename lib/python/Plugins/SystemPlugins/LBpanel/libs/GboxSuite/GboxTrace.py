# 2014.10.12 15:52:22 CEST
from Imports import *
from GboxSuiteUtils import *
import threading
from socket import *
from TraceLabel import *
threadRunning = 1

class GboxTrace(Screen):
    skin = '\n\t\t<screen position="center,center" size="580,420" title="Gbox Trace" >\n\t\t\t<widget name="text" position="10,10" size="560,400" font="Regular;17" />\n\t\t</screen>'

    def __init__(self, session):
        Screen.__init__(self, session)
        self['text'] = TraceLabel('Gbox Trace started, waiting for messages...')
        self['actions'] = NumberActionMap(['WizardActions', 'DirectionActions'], {'ok': self.myClose,
         'back': self.myClose,
         'up': self['text'].pageUp,
         'left': self['text'].pageUp,
         'down': self['text'].pageDown,
         'right': self['text'].pageDown}, -1)
        self.t = PrintThread(self)
        self.t.start()



    def myClose(self):
        threadRunning = 0
        self.close()




class PrintThread(threading.Thread):

    def __init__(self, args):
        self.args = args
        self.finaloutput = ''
        threading.Thread.__init__(self)



    def run(self):
        s = socket(AF_INET, SOCK_DGRAM)
        s.bind(('', 8024))
        while threadRunning == 1:
            data = ''
            (data, (client_ip, client_port,),) = s.recvfrom(512)
            if data == '':
                break
            else:
                output = data.split('\x00')
                out = output[0]
                self.finaloutput += out
                self.args['text'].setText(self.finaloutput)
                self.args['text'].pageDown()



