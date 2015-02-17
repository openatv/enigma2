#!/usr/bin/env python
# -*- coding: utf-8 -*-
import socket
import sys
import re
import os
import io
import telnetlib
from datetime import datetime
import smtplib


# Deactivate insecure lines
def disable_line(file):
   try:
        filenew = file + ".new"
        fpnew = io.open(filenew,'w' , encoding='utf_8_sig')
        with io.open(file, 'r', encoding='utf_8_sig') as fp:
                print "Procesing: ", file
                for line in fp:
                        linetest = line.lstrip()
                        linenew = line
                        if linetest[0:1] != "#":
                                for peer in insecure:
                                            if line.find(peer) >= 0:
                                                if file.find('oscam') >= 0:
                                                        linenew = "# Insecure line, protected by LBpanel \n" + line
                                                        peer2 = peer + ".disabled"
                                                        linenew = linenew.replace(peer,peer2)
                                                else:
                                                        linenew = "# Insecure line, protected by LBpanel \n#" + line
                                                print "DISABLE  LINE: ", peer 
                                                log.write("DISABLE  LINE: " + peer + "\n")
                                                break
                        fpnew.write(linenew)
                fp.close
                fpnew.close
                os.remove(file)
                os.rename(filenew,file)
                
   except: 
        print "*Notice*: " + file + " not found!"


# Check what time the scan started
t1 = datetime.now()

# Insecure peers
insecure = []

# Open log file
log = io.open('/tmp/.lbscan.log', 'wb')
log.write("******** LBpanel - Scan host tool %s ********\n\n" % (t1))
log.close

log = io.open('/tmp/.lbscan.log', 'ab')      
pid = io.open('/tmp/lbscan.pid', 'wb')
pid.write(" ")
pid.close 
#main function
#if __name__ == "__main__":
if(len(sys.argv) < 4) :
        print 'Usage : lbscan.py <scan full|fast> <autocheck yes|no>  <disable_lines yes|no>  <warnonlyemail yes|no>'
        sys.exit(1)
                     
fullmode=0
warnonlyemail=0
if sys.argv[1]=="full":
        fullmode=1
if sys.argv[2] == "yes":
        autocheck = 1
else:
        autocheck = 0
if sys.argv[4] == "yes":
        warnonlyemail=1
if sys.argv[3] == "yes":
        line_disable = 1
else:
        line_disable = 0
# Print a nice banner with information about app
print "-" * 66
print "|                                                                |"
print "| lbscan is a lbpanel module for test multiple cams config files |"
print "| to search open ports and insecure conections.                  |"
print "|                                                                |"
print "|   Supported files:                                             |"
print "|                   oscam.server                                 |"
print "|                   oscam.user                                   |"
print "|                   newcamd.list                                 |"
print "|                   ccamd.list                                   |"
print "|                   users.sbox                                   |"
print "|                   CCcam.cfg                                    |"
print "|                   cwshare.cfg                                  |"
print "|                   peer.cfg                                     |"
print "|                                                                |"
print "| Usage: lbscan full|fast yes|no  yes|no  yes|no                 |"
print "|        with full option scan all ports (very slow)             |"
print "|                                                                |"
print "| LICENSE: GPLV3+                                                |"
print "| http://linux-box.es                                            |"
print "| by iqas27                                                      |"
print "|                                                                |"
print "-" * 66


# Passwords
passwd = []
try:
         with io.open('/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/lbpanel.passwd', 'rb') as fp:
                print "Reading password file"
                for line in fp:
                        passwd.append(line)
                fp.close
except:
        print "-" * 60
        print "** ERROR Reading password file lbpanel.passwd"
        print "-" * 60
        sys.exit(1)
#debug: local test
#passwd = ["root", "toor", "", "pepe", "pkteam", "dreambox" ]
pid = io.open('/tmp/.lbscan', 'wb')
pid.write("Reading config files")
pid.close

array = []

# Autocheck
if sys.argv[2]=="yes":
        array.append("127.0.0.1")
        # Check wget and /var/run/mipsel
        if os.path.isfile("/usr/bin/wget"):
                print "Virus test - Test pass"
        else:
                print "WGET FILE DELETED SUSPECTED OF VIRUS!!!"                
                log.write("WGET FILE DELETED SUSPECTED OF VIRUS - SECURITY WARNING!!!\n")
                
        if os.path.isfile("/var/run/mipsel"):
                print "SECURITY WARNING!!! - FILE SUSPECTED TO BE VIRUS!!!"
                log.write("FILE SUSPECTED TO BE VIRUS - SECURITY WARNING!!!\n")
                
                
# Load oscam settings        
try:
        with io.open('/var/keys/oscam.server', 'r', encoding='utf_8_sig') as fp:
                print "Procesing: oscam.server"
                for line in fp:
                        line = line.lstrip()
                        if line[0:1] != "#":
                                if line.find("device") >=0 :
                                        if line.find(",") >=0 :
                                                r = re.compile('=(.*?),')
                                                m = r.search(line)
                                                # Save the data in a array
                                                if m:        
                                                        array.append(m.group(1))
                fp.close
except: 
        print "*Notice*: oscam.server not found!"

try:
        with io.open('/var/keys/oscam.user', 'r', encoding='utf_8_sig') as fp:
                print "Procesing: oscam.user"
                for line in fp:
                        line = line.lstrip()
                        if line[0:1] != "#":
                                if line.find("hostname") >=0 :
                                        line = re.sub(" ", "",line)
                                        r = re.compile('=(.*)')
                                        m = r.search(line)
                                        # Save the data in a array
                                        if m:        
                                                array.append(m.group(1))
                fp.close
except: 
        print "*Notice*: oscam.user not found!"

#Load newcamd settings
try:
        with io.open('/var/keys/newcamd.list', 'r', encoding='utf_8_sig') as fp:
                print "Procesing: newcamd.list"
                for line in fp:
                        line = line.lstrip()
                        if line[0:1] != "#":
                                if line.find("wan") >=0 :
                                        r = re.compile('(.?)=(.*)')
                                        m = r.search(line)
                                        data = []
                                        data = m.group(2).split()
                                        # Save the data in a array
                                        if m:        
                                                array.append(data[0])
                fp.close
except: 
        print "*Notice*: newcamd.list not found!"

        
try:
        with io.open('/var/keys/cccamd.list', 'r', encoding='utf_8_sig') as fp:
                print "Procesing: ccamd.list"
                for line in fp:
                        line = line.lstrip()
                        if line[0:1] != "#":
                                if line.find("C:") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])
                fp.close
except: 
        print "*Notice*: cccamd.list not found!"

        
#Load CCcam settings
try:
        with io.open('/etc/CCcam.cfg', 'r', encoding='utf_8_sig') as fp:
                print "Procesing: CCcam.cfg"
                for line in fp:
                        line = line.lstrip()
                        if line[0:1] != "#":
                                if line.find("C:") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])
                                if line.find("N:") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])
                                if line.find("R:") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])
                                if line.find("L:") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])
                                if line.find("G:") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[2])

                fp.close
except: 
        print "*Notice*: CCcam.cfg not found!"
        
#Load sbox settings
try:
        with io.open('/var/keys/users.sbox', 'r', encoding='utf_8_sig') as fp:
                print "Procesing: users.sbox"
                for line in fp:
                        line = line.lstrip()
                        if line[0:1] != "#":        
                                line = line.replace('=',' ')
                                if line.find("RS") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])
                                if line.find("NS") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])
                                if line.find("CS") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])
                                if line.find("NC") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        if len(data) > 6:
                                                array.append(data[6])
                                if line.find("CC") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        if len(data) > 9:
                                                array.append(data[6])

                fp.close
except: 
        print "*Notice*: users.sbox not found!"

#Load cwshare.cfg settings
try:
        with io.open('/var/keys/cwshare.cfg', 'r', encoding='utf_8_sig') as fp:
                print "Procesing: cwshare.cfg"
                for line in fp:
                        line = line.lstrip()
                        if line[0:1] != "#":        
                                line = line.replace('{','')
                                if line.find("C:") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])
                                if line.find("D:") >=0 :
                                        data = []
                                        data = line.split()
                                        # Save the data in a array
                                        array.append(data[1])

                fp.close
except: 
        print "*Notice*: users.sbox not found!"
        


# Test array ips
print "-" * 60
for remoteServer in array:
        try:
           if (autocheck == 1 or (remoteServer != "127.0.0.1" and remoteServer != "localhost")): 
                remoteServerIP = socket.gethostbyname(remoteServer)
                print "Check: ",remoteServer, " - ", remoteServerIP
                pid = io.open('/tmp/.lbscan', 'wb')
                pid.write( "Check: "+ remoteServer + " - " + remoteServerIP)
                pid.close
                # Testing ports of remote server
                #  and save in array
                if fullmode == 0 :
                        portList = [21,22,23,35,43,80,558,795,12000,16000,16001]
                else:
                        portList = range(1,65535)
                # Check ports
                for port in portList:
                        timeout=.1        
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        error = -1
                        while (timeout < 1 and error != 0):
                                try:
                                        sock.settimeout(timeout)
                                        result = sock.connect_ex((remoteServerIP, port))
                                        error = 0
                                except socket.error:
                                        print("socket error occured: ")
                                except socket.timeout:
                                        timeout = timeout + .1
                                
                        if result == 0:
                                print "       ", remoteServer, ": Port:", port, " Open"
                                log.write( remoteServer + ": Port:" + str(port) + " Open\n")
                                # ssh testing
                                if port == 22:
                                        print "        Checking ssh passwords -|",
                                        for login in passwd:
                                                try:
                                                        if (os.system('/usr/lib/enigma2/python/Plugins/SystemPlugins/LBpanel/sshpass -p "' + login.rstrip('\n') + '" ssh -y root@' + remoteServerIP + ' exit > /dev/null 2>&1')) == 0:
                                                                print "SSH PORT INSECURE PASSWORD - SECURITY WARNING!!!",
                                                                log.write(remoteServer + ": SSH PORT INSECURE PASSWORD - SECURITY WARNING!!!\n")
                                                                insecure.append(remoteServer)
                                                                break 
                                                        else:
                                                                print ".",
                                                except: 
                                                        print ".",
                                        print "|"
                                # telnet testing
                                if port == 23:
                                        print "        Checking telnet passwords -|",
                                        for login in passwd:
                                               try:
                                                        s = telnetlib.Telnet(remoteServerIP)
                                                        response = s.read_until("login: ",5)
                                                        s.write("root\n")
                                                        if login:
                                                                response = s.read_until("Password: ",5)
                                                                s.write(login + "\n")
                                                        try:
                                                                response = s.read_until("# ",5)
                                                                if response.find("#") >= 0:
                                                                        s.write("exit\n")
                                                                        s.close
                                                                        print "TELNET PORT INSECURE PASSWORD - SECURITY WARNING!!!",
                                                                        log.write( remoteServer + ": TELNET PORT INSECURE PASSWORD - SECURITY WARNING!!!\n")
                                                                        insecure.append(remoteServer)
                                                                        break
                                                        except:
                                                                print "Invalid passwd"
                                               except: 
                                                        print ".",
                                                        s.close
                                        print "|"
                                # e1 bug testing
                                if port == 80:
                                        print "        Checking e1 bug webif -|",
                                        for login in passwd:
                                                try:
                                                        if (os.system('wget -s http://' + remoteServerIP + '//%2f..%2f..%2f..%2f..%2f..%2f..%2fvar/tuxbox/config/enigma/config > /dev/null 2>&1')) == 0:
                                                                print "E1 INSECURE CONFIG FILES - SECURITY WARNING!!!",
                                                                log.write(remoteServer + ": E1 INSECURE CONFIG FILES - SECURITY WARNING!!!\n")
                                                                insecure.append(remoteServer)
                                                                break 
                                                        else:
                                                                print ".",
                                                except: 
                                                        print ".",
                                        print "|"

                        sock.close()
        
        except socket.gaierror, err:
                print "Cannot resolve hostname: ", remoteServer, err

print "-" * 60

# By default not send email
email = 0
# Deactivate insecure lines
if (len(insecure) > 0 and line_disable == 1):
        print "Check Config files for insecure lines"
        if os.path.isfile("/etc/CCcam.cfg"): disable_line("/etc/CCcam.cfg")
        if os.path.isfile("/var/keys/oscam.server"): disable_line("/var/keys/oscam.server")
        if os.path.isfile("/var/keys/oscam.user"): disable_line("/var/keys/oscam.user")
        if os.path.isfile("/var/keys/newcamd.list"): disable_line("/var/keys/newcamd.list")
        if os.path.isfile("/var/keys/ccamd.list"): disable_line("/var/keys/ccamd.list")
        if os.path.isfile("/var/keys/users.sbox"): disable_line("/var/keys/users.sbox")
        if os.path.isfile("/var/keys/cwshare.cfg"): disable_line("/var/keys/cwshare.cfg")
        if os.path.isfile("/var/keys/peer.cfg"): disable_line("/var/keys/peer.cfg")
# Checking the time again
t2 = datetime.now()

# Calculates the difference of time, to see how long it took to run the script
total =  t2 - t1

# Printing the information to screen
print 'Scanning Completed in: ', total
log.close
os.remove("/tmp/lbscan.pid")

## Send email
if warnonlyemail:
        f = io.open('/tmp/.lbscan.end', 'wb')
        f.write(" ")
        f.close()