from Plugins.Plugin import PluginDescriptor
from Components.Harddisk import harddiskmanager
from Tools.Directories import fileExists

hotplugNotifier = [ ]
bdpoll = None

def processHotplugData(self, v):
	print "hotplug:", v
	action = v.get("ACTION")
	device = v.get("DEVPATH")
	physdevpath = v.get("PHYSDEVPATH")
	media_state = v.get("X_E2_MEDIA_STATUS")

	dev = device.split('/')[-1]

	if action is not None and action == "add":
		error, blacklisted, removable, is_cdrom, partitions, medium_found = harddiskmanager.addHotplugPartition(dev, physdevpath)
		if bdpoll and removable or is_cdrom:
			bdpoll.addDevice(dev, is_cdrom, medium_found)
	elif action is not None and action == "remove":
		if bdpoll:
			bdpoll.removeDevice(dev)
		harddiskmanager.removeHotplugPartition(dev)
	elif media_state is not None:
		if media_state == '1':
			harddiskmanager.removeHotplugPartition(dev)
			harddiskmanager.addHotplugPartition(dev, physdevpath)
		elif media_state == '0':
			harddiskmanager.removeHotplugPartition(dev)

	for callback in hotplugNotifier:
		try:
			callback(dev, action or media_state)
		except AttributeError:
			hotplugNotifier.remove(callback)

CDROM_DRIVE_STATUS = 0x5326
CDROM_MEDIA_CHANGED = 0x5325
CDSL_CURRENT = ((int)(~0>>1))
CDS_NO_INFO = 0
CDS_NO_DISC = 1
CDS_TRAY_OPEN = 2
CDS_DRIVE_NOT_READY = 3
CDS_DISC_OK = 4
ENOMEDIUM = 159
IOC_NRBITS = 8
IOC_NRSHIFT = 0
IOC_TYPESHIFT = (IOC_NRSHIFT+IOC_NRBITS)
BLKRRPART = ((0x12<<IOC_TYPESHIFT) | (95<<IOC_NRSHIFT))

def autostart(reason, **kwargs):
	global bdpoll
	if reason == 0:
		print "starting hotplug handler"

		if fileExists('/dev/.udev'):
			global netlink
			from enigma import eSocketNotifier, eTimer, ePythonMessagePump
			import socket
			from select import POLLIN, POLLPRI

			class Netlink:
				def __init__(self):
					self.netlink = socket.socket(socket.AF_NETLINK, socket.SOCK_DGRAM, 15)
					self.netlink.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
					self.netlink.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
					self.netlink.bind((0, 1))
					self.sn = eSocketNotifier(self.netlink.fileno(), POLLIN|POLLPRI)
					self.sn.callback.append(self.dataAvail)

				def dataAvail(self, what):
					received = self.netlink.recvfrom(16384)
#					print "HOTPLUG(%d):" %(what), received

					data = received[0].split('\0')[:-1]
					v = {}

					for x in data:
						i = x.find('=')
						var, val = x[:i], x[i+1:]
						v[var] = val

					if v['SUBSYSTEM'] == 'block' and v['ACTION'] in ('add', 'remove'):
						processHotplugData(self, v)

			from threading import Thread, Semaphore, Lock

			class ThreadQueue:
				def __init__(self):
					self.__list = [ ]
					self.__lock = Lock()

				def push(self, val):
					list = self.__list
					lock = self.__lock
					lock.acquire()
					list.append(val)
					lock.release()

				def pop(self):
					list = self.__list
					lock = self.__lock
					lock.acquire()
					ret = list[0]
					del list[0]
					lock.release()
					return ret

			import os
			import errno
			import fcntl

			class BDPoll(Thread):
				CHECK_INTERVAL = 2000
				MSG_MEDIUM_REMOVED = 1
				MSG_MEDIUM_INSERTED = 2
				MSG_POLL_FINISHED = 4
				def __init__(self):
					Thread.__init__(self)
					self.__sema = Semaphore(0)
					self.__lock = Lock()
					self.running = False
					self.devices_to_poll = { }
					self.messages = ThreadQueue()
					self.checkTimer = eTimer()
					self.checkTimer.callback.append(self.timeout)
					self.checkTimer.start(BDPoll.CHECK_INTERVAL, True)
					self.mp = ePythonMessagePump()
					self.mp.recv_msg.get().append(self.gotThreadMsg)
					self.start()

				def gotThreadMsg(self, msg):
					msg = self.messages.pop()
					if msg[0] == BDPoll.MSG_MEDIUM_REMOVED:
						print "MSG_MEDIUM_REMOVED"
						harddiskmanager.removeHotplugPartition(msg[1])
					elif msg[0] == BDPoll.MSG_MEDIUM_INSERTED:
						print "MSG_MEDIUM_INSERTED"
						harddiskmanager.addHotplugPartition(msg[1])
					elif msg[0] == BDPoll.MSG_POLL_FINISHED:
						self.checkTimer.start(BDPoll.CHECK_INTERVAL, True)

				def timeout(self):
					self.__sema.release() # start bdpoll loop in thread

				def is_mounted(self, dev):
					mounts = file('/proc/mounts').read()
					return mounts.find(dev) != -1

				def run(self):
					sema = self.__sema
					lock = self.__lock
					messages = self.messages
					mp = self.mp
					self.running = True
					while self.running:
						sema.acquire()
						self.__lock.acquire()
						devices_to_poll = self.devices_to_poll.items()
						self.__lock.release()
						devices_to_poll_processed = [ ]
						for device, state in devices_to_poll:
							got_media = False
							is_cdrom, prev_media_state = state
							if is_cdrom:
								try:
									fd = os.open("/dev/" + device, os.O_RDONLY | os.O_NONBLOCK | os.O_EXCL)
								except OSError, err:
									if err.errno == errno.EBUSY:
										print "open cdrom exclusive failed:",
										if not self.is_mounted(device):
											print "not mounted"
											continue
										try:
											print "mounted... try non exclusive"
											fd = os.open("/dev/" + device, os.O_RDONLY | os.O_NONBLOCK)
										except OSError, err:
											print "open cdrom not exclusive failed", os.strerror(err.errno)
											continue
								#here the fs must be valid!
								try:
									ret = fcntl.ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT)
								except IOError, err:
									print "ioctl CDROM_DRIVE_STATUS failed", os.strerror(err.errno)
								else:
									if ret in (CDS_NO_INFO, CDS_NO_DISC, CDS_TRAY_OPEN, CDS_DRIVE_NOT_READY):
										pass
									elif ret == CDS_DISC_OK:
										#todo new kernels support events to userspace event on media change
										#but not 2.6.18.... see hotplug-ng bdpoll.c
										got_media = True
								os.close(fd)
							else:
								try:
									fd = os.open("/dev/" + device, os.O_RDONLY)
								except OSError, err:
									if err.errno == ENOMEDIUM:
										pass
									else:
										print "open non cdrom failed", os.strerror(err.errno)
										continue
								else:
									got_media = True
									os.close(fd)
							if prev_media_state:
								if not got_media:
									print "media removal detected on", device
									try:
										fd = os.open("/dev/" + device, os.O_RDONLY | os.O_NONBLOCK)
									except OSError, err:
										print "open device for blkrrpart ioctl failed", os.strerror(err.errno)
									else:
										try:
											fcntl.ioctl(fd, BLKRRPART)
										except IOError, err:
											print "ioctl BLKRRPART failed", os.strerror(err.errno)
										os.close(fd)
							else:
								if got_media:
									print "media insertion detected on", device
							devices_to_poll_processed.append((device, is_cdrom, got_media))
						self.__lock.acquire()
						for device, is_cdrom, state in devices_to_poll_processed:
							old_state = self.devices_to_poll.get(device)
							if old_state is not None and old_state[1] != state:
								msg = state and BDPoll.MSG_MEDIUM_INSERTED or BDPoll.MSG_MEDIUM_REMOVED
								self.devices_to_poll[device] = (is_cdrom, state)
								messages.push((msg, device))
								mp.send(0)

						self.__lock.release()
						messages.push((self.MSG_POLL_FINISHED,))
						mp.send(0)

				def addDevice(self, device, is_cdrom, inserted):
					self.__lock.acquire()
					if device in self.devices_to_poll:
						print "device", device, "already in bdpoll"
					else:
						print "add device", device, "to bdpoll current state:",
						if inserted:
							print "medium inserted"
						else:
							print "medium removed"
						self.devices_to_poll[device] = (is_cdrom, inserted)
					self.__lock.release()

				def removeDevice(self, device):
					self.__lock.acquire()
					if device in self.devices_to_poll:
						print "device", device, "removed from bdpoll"
						del self.devices_to_poll[device]
					else:
						print "try to del not exist device", device, "from bdpoll"
					self.__lock.release()

			netlink = Netlink()
			if bdpoll is not None:
				bdpoll.running = False
			bdpoll = BDPoll()
			for blockdev, removable, is_cdrom, medium_found in harddiskmanager.devices_scanned_on_init:
				if removable or is_cdrom:
					bdpoll.addDevice(blockdev, is_cdrom, medium_found)
		else:
			from twisted.internet.protocol import Protocol, Factory
			from twisted.internet import reactor

			try:
				import os
				os.remove("/tmp/hotplug.socket")
			except OSError:
				pass

			class Hotplug(Protocol):
				def connectionMade(self):
					print "HOTPLUG connection!"
					self.received = ""

				def dataReceived(self, data):
					print "hotplug:", data
					self.received += data
					print "complete", self.received

				def connectionLost(self, reason):
					print "HOTPLUG connection lost!"
					data = self.received.split('\0')[:-1]
					v = {}

					for x in data:
						i = x.find('=')
						var, val = x[:i], x[i+1:]
						v[var] = val

					processHotplugData(self, v)

			factory = Factory()
			factory.protocol = Hotplug
			reactor.listenUNIX("/tmp/hotplug.socket", factory)
	else:
		if bdpoll:
			bdpoll.running = False
			bdpoll.timeout() # XXX: I assume the timer is shut down before it executes again, so release the semaphore manually
			bdpoll.join()
		bdpoll = None

def Plugins(**kwargs):
	return PluginDescriptor(name = "Hotplug", description = "listens to hotplug events", where = PluginDescriptor.WHERE_AUTOSTART, needsRestart = True, fnc = autostart)
