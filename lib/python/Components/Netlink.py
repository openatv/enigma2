# Listen to hotplug events. Can be used to listen for hotplug events and
# similar things, like network connections being (un)plugged.
import os
import socket


class NetlinkSocket(socket.socket):
	def __init__(self):
		NETLINK_KOBJECT_UEVENT = 15  # hasn't landed in socket yet, see linux/netlink.h
		socket.socket.__init__(self, socket.AF_NETLINK, socket.SOCK_DGRAM, NETLINK_KOBJECT_UEVENT)
		self.bind((os.getpid(), -1))

	def parse(self):
		data = self.recv(512).decode("utf-8", "ignore")
		event = {}
		for item in data.split('\x00'):
			if not item:
				# terminator
				yield event
				event = {}
			else:
				try:
					k, v = item.split('=', 1)
					event[k] = v
				except Exception:
					event[None] = item


# Quick unit test (you can run this on any Linux machine)
if __name__ == '__main__':
	nls = NetlinkSocket()
	print("socket no: %s" % nls.fileno())
	while True:
		for item in nls.parse():
			print(repr(item))
