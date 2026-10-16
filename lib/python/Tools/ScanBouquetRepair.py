from collections import Counter, defaultdict

from enigma import eDVBDB, eServiceCenter, eServiceReference, iServiceInformation


class ScanBouquetRepair:
	"""Keep names only for one foreground scan, without changing settings formats."""

	def __init__(self):
		self.database = eDVBDB.getInstance()
		self.serviceCenter = eServiceCenter.getInstance()
		self.scanned = set()
		self.services = self.readServices()
		self.nameCounts = Counter(key for ref, key in self.services.values() if key is not None)
		self.bouquets = []
		visited = set()

		def visit(bouquet):
			path = bouquet.getPath().split('"')
			if len(path) < 3:
				return
			filename = path[1]
			if filename in visited or filename.startswith("userbouquet.LastScanned."):
				return
			visited.add(filename)
			serviceList = self.serviceCenter.list(bouquet)
			if serviceList is None:
				return
			entries = serviceList.getContent("R") or []
			known = {self.serviceKey(ref) for ref in entries if self.isDVBService(ref)} & self.services.keys()
			if known:
				self.bouquets.append((bouquet, known))
			for ref in entries:
				if ref.flags & eServiceReference.canDescent and "FROM BOUQUET " in ref.getPath():
					visit(ref)

		for mode in ("tv", "radio"):
			for filename in (f"bouquets.{mode}", f"userbouquet.favourites.{mode}"):
				visit(eServiceReference(f'1:7:0:0:0:0:0:0:0:0:FROM BOUQUET "{filename}" ORDER BY bouquet'))

	@staticmethod
	def serviceKey(ref):
		# Use the same service identity as the database, not a name or bouquet flag.
		return tuple(ref.getUnsignedData(index) for index in range(8))

	@staticmethod
	def isDVBService(ref):
		return ref.type == eServiceReference.idDVB and not ref.getPath() and not ref.flags & (eServiceReference.isMarker | eServiceReference.isDirectory | eServiceReference.isGroup)

	def readServices(self):
		services = {}
		transponders = {}
		for reference, data in self.database.getAllServicesRaw().items():
			ref = eServiceReference(reference)
			if not self.isDVBService(ref):
				continue
			identity = self.serviceKey(ref)
			key = None
			serviceType = ref.getUnsignedData(0)
			category = "radio" if serviceType in (2, 10) else "tv" if serviceType in (1, 17, 22, 25, 31, 32, 134, 195) else None
			name = data[0].strip().casefold()  # Original SDT name, never a user rename.
			if category and name and name not in ("<n/a>", "n/a", "(...)"):
				channel = identity[2:5]
				if channel not in transponders:
					info = self.serviceCenter.info(ref)
					transponders[channel] = info.getInfoObject(ref, iServiceInformation.sTransponderData) if info else None
				transponder = transponders[channel] or {}
				system = transponder.get("tuner_type")
				position = transponder.get("orbital_position") if system == "DVB-S" else None
				if system in ("DVB-C", "DVB-T", "ATSC") or system == "DVB-S" and position is not None:
					key = (name, category, system, position)
			services[identity] = (ref, key)
		return services

	def addScannedService(self, reference):
		ref = eServiceReference(reference)
		if self.isDVBService(ref):
			self.scanned.add(self.serviceKey(ref))

	def clear(self):
		self.services.clear()
		self.nameCounts.clear()
		self.bouquets.clear()
		self.scanned.clear()

	def repair(self):
		"""Return updated, unresolved and failed bouquet entry counts."""
		try:
			current = self.readServices()
			candidates = defaultdict(list)
			for identity, (ref, key) in current.items():
				if key is not None:
					candidates[key].append((identity, ref))
			replacements = {}
			for identity, (ref, key) in self.services.items():
				if identity in current or key is None or self.nameCounts[key] != 1:
					continue
				matches = candidates.get(key, [])
				if len(matches) == 1 and matches[0][0] in self.scanned:
					replacements[identity] = matches[0][1]
			updated = unresolved = failed = 0
			for bouquet, known in self.bouquets:
				serviceList = self.serviceCenter.list(bouquet)
				if serviceList is None:
					continue
				entries = serviceList.getContent("R") or []
				counts = Counter(self.serviceKey(ref) for ref in entries if self.isDVBService(ref))
				mutable = None
				changes = []
				for old in entries:
					identity = self.serviceKey(old)
					if not self.isDVBService(old) or identity not in known or identity in current:
						continue
					replacement = replacements.get(identity)
					if replacement is None or counts[identity] != 1 or counts[self.serviceKey(replacement)]:
						unresolved += 1
						continue
					if mutable is None:
						mutable = serviceList.startEdit()
					if mutable is None:
						failed += 1
						continue
					# Copy the entry to preserve its custom name, flags and position.
					new = eServiceReference(old)
					for index in range(8):
						new.setUnsignedData(index, replacement.getUnsignedData(index))
					if mutable.addService(new, old):
						failed += 1
						continue
					if mutable.removeService(old, False):
						mutable.removeService(new, False)
						failed += 1
						continue
					counts[self.serviceKey(new)] += 1
					changes.append((old, new))
				if changes:
					if mutable.flushChanges():
						# Retain the original in-memory entries if saving failed.
						for old, new in reversed(changes):
							if not mutable.addService(old, new):
								mutable.removeService(new, False)
						failed += len(changes)
					else:
						updated += len(changes)
						for old, new in changes:
							print(f"[ScanBouquetRepair] Updated {old.toString()} -> {new.toString()} in {bouquet.getPath()}.")
			return updated, unresolved, failed
		finally:
			self.clear()
