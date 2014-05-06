from Components.Console import Console
import os

swapdevice = None

def bigStorage(minFree):
		mounts = open('/proc/mounts', 'rb').readlines()
		mountpoints = [x.split(' ', 2)[1] for x in mounts]
		for candidate in mountpoints:
			if not candidate.startswith('/media'):
				continue
			try:
				diskstat = os.statvfs(candidate)
				free = diskstat.f_bfree * diskstat.f_bsize
				if free > minFree:
					print 
					return candidate
			except:
				pass
		return None

class SwapCheck:
	def __init__(self, callback=None, extra_args=None):
		self.Console = Console()
		if not extra_args: extra_args = []
		self.extra_args = extra_args
		assert callable(callback), "callback must be callable"
		self.callback = callback
		self.retry = 0
		if self.callback:
			self.MemCheck1()

	def MemCheck1(self):
		path = bigStorage(9000000)
		if path:
			global swapdevice
			swapdevice = os.path.join(path, 'swapfile_tmp')
			print "[SwapCheck] Location:", swapdevice

			if os.path.exists(swapdevice):
				print "[SwapCheck] Removing old swapfile"
				self.Console.ePopen("swapoff " + swapdevice + " && rm " + swapdevice)
			f = open('/proc/meminfo', 'r')
			for line in f.readlines():
				if line.find('MemFree') != -1:
					parts = line.strip().split()
					memfree = int(parts[1])
				elif line.find('SwapFree') != -1:
					parts = line.strip().split()
					swapfree = int(parts[1])
			f.close()
			TotalFree = memfree + swapfree
			print "[SwapCheck] Free Mem",TotalFree
			if int(TotalFree) < 5000:
				print "[SwapCheck] Not Enough Ram"
				self.MemCheck2()
			else:
				print "[SwapCheck] Found Enough Ram"
				if self.extra_args:
					self.callback(self.extra_args)
				else:
					self.callback()
		else:
			if self.extra_args:
				self.callback(self.extra_args)
			else:
				self.callback()

	def MemCheck2(self):
		print "[SwapCheck] Creating Swapfile"
		self.Console.ePopen("dd if=/dev/zero of=" + swapdevice + " bs=1024 count=16440", self.MemCheck3)

	def MemCheck3(self, result, retval, extra_args = None):
		if retval == 0:
			self.Console.ePopen("mkswap " + swapdevice, self.MemCheck4)
		else:
			self.retry += 1
			if self.retry < 5:
				self.Console.ePopen("dd if=/dev/zero of=" + swapdevice + " bs=1024 count=16440", self.MemCheck3)
			else:
				if self.extra_args:
					self.callback(self.extra_args)
				else:
					self.callback()

	def MemCheck4(self, result, retval, extra_args = None):
		if retval == 0:
			self.Console.ePopen("swapon " + swapdevice, self.MemCheck5)

	def MemCheck5(self, result, retval, extra_args = None):
		if self.extra_args:
			self.callback(self.extra_args)
		else:
			self.callback()

	def RemoveSwap(self):
		if swapdevice and os.path.exists(swapdevice):
			print "[SwapCheck] Removing Swapfile",swapdevice
			self.Console.ePopen("swapoff " + swapdevice + " && rm " + swapdevice)
