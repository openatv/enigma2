from csv import writer
from hashlib import sha256
from json import dump, loads
from math import ceil
from os import getenv, getpid, listdir, makedirs, replace, uname
from os.path import dirname, join
from time import monotonic, process_time, strftime

from enigma import BT_SCALE, ePoint, eSize, eTimer, gRGB, getDesktop, loadSVG

from Components.ActionMap import ActionMap
from Components.config import config
from Components.Label import Label
from Components.Pixmap import Pixmap
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Tools.Conversions import NumberScaler

# Keep visual tests available when an older E2 lacks the diagnostic binding.
try:
	from enigma import gRenderTest
except ImportError:
	gRenderTest = None


class RenderMeasurements:
	VERSION = 5

	def __init__(self, width, height):
		self.runs = []
		self.verdicts = {}
		self.resultDirectory = join(config.crash.debug_path.value, "gles-testlab")
		self.runId = f"{strftime('%Y%m%d-%H%M%S')}-{getpid()}"
		self.metadata = {"schema": self.VERSION, "pid": getpid(), "desktop": [width, height], "runId": self.runId, "gpuTiming": "not measured", "scanoutTiming": "not measured", "intervalMeaning": "renderer completion intervals, including idle; not GPU duration", "cpuMeaning": "whole Enigma2 process including television and plugin", "visualVerdicts": self.verdicts}
		self.metadata["platform"] = list(uname())
		self.metadata["environment"] = {x: getenv(x) for x in ("E2EGL_DREAMBCM_ION_TARGET", "E2EGL_DREAMBCM_ION_UPLOAD", "E2EGL_DREAMBCM_ION_VERIFY", "E2EGL_EVENT_ANIMATION", "E2EGL_FONT_ATLAS_START")}
		self.metadata["skin"] = config.skin.primary_skin.value
		self.metadata["resultDirectory"] = self.resultDirectory
		with open(__file__, "rb") as pluginFile:
			self.metadata["pluginSha256"] = sha256(pluginFile.read()).hexdigest()
		try:
			with open("/usr/bin/enigma2", "rb") as binaryFile:
				self.metadata["binarySha256"] = sha256(binaryFile.read()).hexdigest()
		except OSError as error:
			self.metadata["binaryHashError"] = str(error)

	@staticmethod
	def resources():
		values = {"time": monotonic(), "cpuSeconds": process_time()}
		try:
			with open("/proc/self/status") as statusFile:
				for line in statusFile:
					if line.startswith(("VmRSS:", "VmSize:", "VmHWM:")):
						name, value, unit = line.split()
						values[name.rstrip(":")] = int(value) * 1024
			values["fds"] = len(listdir("/proc/self/fd"))
		except OSError as error:
			values["error"] = str(error)
		return values

	@staticmethod
	def distribution(values):
		ordered = sorted(values)
		return {"count": len(ordered), "p50": ordered[max(0, ceil(len(ordered) * .50) - 1)], "p95": ordered[max(0, ceil(len(ordered) * .95) - 1)], "p99": ordered[max(0, ceil(len(ordered) * .99) - 1)], "max": ordered[-1], "mean": sum(ordered) / len(ordered)} if ordered else {"count": 0}

	def save(self):
		makedirs(self.resultDirectory, exist_ok=True)
		resultPath = join(self.resultDirectory, f"{self.runId}.json")
		temporaryPath = join(self.resultDirectory, f"{self.runId}.tmp")
		with open(temporaryPath, "w", encoding="utf-8") as resultFile:
			dump({"metadata": self.metadata, "runs": self.runs}, resultFile, indent=2, ensure_ascii=False)
		replace(temporaryPath, resultPath)
		with open(join(self.resultDirectory, f"{self.runId}.csv"), "w", newline="", encoding="utf-8") as csvFile:
			csvWriter = writer(csvFile)
			csvWriter.writerow(("page", "status", "seconds", "cpuSeconds", "frames", "drawP95Us", "presentCallP95Us", "rssBeforeBytes", "rssAfterBytes", "fdsBefore", "fdsAfter", "ionUploads", "uploadBytes"))
			for run in self.runs:
				csvWriter.writerow((run["page"], run["status"], run["seconds"], run["cpuSeconds"], len(run["renderer"]["frames"]), run["drawUs"].get("p95"), run["swapUs"].get("p95"), run["before"].get("VmRSS"), run["after"].get("VmRSS"), run["before"].get("fds"), run["after"].get("fds"), run["totals"].get("ionUploads"), run["totals"].get("uploadBytes")))
		return resultPath


class GlesTestLabScreen(Screen):
	PAGES = ("Pixelformate", "Füllflächen und Alpha", "Runde Ecken und Rahmen", "Farbverläufe", "Überlagerte Ebenen", "Text und Mischformen", "Neue Texturen / ION", "Gemeinsame Schreibflächen / CPU-Vergleich")
	SKIN_TEXT = "#00eef4ff"
	LABEL_COUNT = 64
	PIXMAP_COUNT = 24
	WARMUP_SECONDS = 2.0
	MEASURE_SECONDS = 6.0

	def __init__(self, session):
		Screen.__init__(self, session)
		desktopSize = getDesktop(0).size()
		self.width, self.height = desktopSize.width(), desktopSize.height()
		self.scaleX, self.scaleY = self.width / 1920, self.height / 1080
		self.page = 0
		self.labelIndex = 0
		self.gradientIndex = self.LABEL_COUNT - 6
		self.pixmapIndex = 0
		self.nativePixmaps = []
		self.formats = []
		self.caseWidgets = []
		self.uploadWidgets = []
		self.measurements = RenderMeasurements(self.width, self.height)
		self.phase = None
		self.autoRun = False
		self.captureOwned = False
		self.ticks = []
		self.memorySamples = []
		self.savedPath = ""
		self.timer = eTimer()
		self.timer.callback.append(self.tick)
		self.skin = self.buildSkin()
		self["title"] = Label()
		self["details"] = Label()
		self["status"] = Label("Bereit. Grün: 2 s Aufwärmen + 6 s Messung. 1: Bild OK / 2: Bildfehler markieren.")
		self["footer"] = Label("ROT Beenden     GRÜN Messen/Stopp     GELB Alle Tests     BLAU Weiter     ← Zurück")
		for labelIndex in range(self.LABEL_COUNT):
			self[f"label{labelIndex}"] = Label()
		for pixmapIndex in range(self.PIXMAP_COUNT):
			self[f"pixmap{pixmapIndex}"] = Pixmap()
		self["actions"] = ActionMap(["ColorActions", "OkCancelActions", "DirectionActions", "NumberActions"], {"cancel": self.close, "red": self.close, "green": self.toggleRun, "yellow": self.startAll, "blue": self.nextPage, "right": self.nextPage, "left": self.previousPage, "1": self.markGood, "2": self.markBad}, -1)
		self.onLayoutFinish.append(self.ready)
		self.onClose.append(self.cleanup)

	def buildSkin(self):
		widgets = []
		for name, yPos, height, font in (("title", 44, 60, 38), ("details", 112, 56, 23), ("status", 904, 80, 24), ("footer", 1010, 42, 25)):
			widgets.append(f'<widget name="{name}" position="{self.sx(64)},{self.sy(yPos)}" size="{self.sx(1792)},{self.sy(height)}" font="Regular;{self.sy(font)}" foregroundColor="{self.SKIN_TEXT}" transparent="1" zPosition="200" />')
		for index in range(self.LABEL_COUNT):
			widgets.append(f'<widget name="label{index}" position="0,0" size="1,1" font="Regular;{self.sy(22)}" foregroundColor="{self.SKIN_TEXT}" />')
		for index in range(self.PIXMAP_COUNT):
			widgets.append(f'<widget name="pixmap{index}" position="0,0" size="1,1" />')
		return f'<screen name="GlesTestLabScreen" position="0,0" size="{self.width},{self.height}" flags="wfNoBorder" backgroundColor="#00101928">{"".join(widgets)}</screen>'

	def sx(self, value):
		return round(value * self.scaleX)

	def sy(self, value):
		return round(value * self.scaleY)

	def ready(self):
		self.setAnimationMode(0)
		self.checker = loadSVG(join(dirname(__file__), "checker.svg"), 0, 560, 250)
		self.showPage()

	def place(self, widget, xPos, yPos, width, height, zPosition):
		widget.move(ePoint(self.sx(xPos), self.sy(yPos)))
		widget.resize(eSize(self.sx(width), self.sy(height)))
		widget.setZPosition(zPosition)
		widget.show()
		self.caseWidgets.append(widget)

	def label(self, xPos, yPos, width, height, text="", color=None, alpha=False, radius=0, edges=15, border=0, gradient=None, zPosition=20):
		# E2 has no gradient-reset API: reserve separate widgets for gradients.
		if gradient:
			widget = self[f"label{self.gradientIndex}"].instance
			self.gradientIndex += 1
		else:
			widget = self[f"label{self.labelIndex}"].instance
			self.labelIndex += 1
		widget.setText(text)
		widget.setTransparent(color is None and gradient is None)
		widget.clearBackgroundColor()
		if color is not None:
			widget.setBackgroundColor(gRGB(color))
		widget.setWidgetAlphaBlend(alpha)
		widget.setCornerRadius(self.sy(radius), edges)
		widget.setWidgetBorderWidth(self.sy(border))
		widget.setWidgetBorderColor(gRGB(0x00ffffff))
		if gradient:
			start, middle, end, direction = gradient
			widget.setBackgroundGradient(gRGB(start), gRGB(middle), gRGB(end), direction, alpha)
		self.place(widget, xPos, yPos, width, height, zPosition)
		return widget

	def pixmap(self, pixmap, xPos, yPos, width, height, alpha=2, radius=0, zPosition=10):
		widget = self[f"pixmap{self.pixmapIndex}"].instance
		self.pixmapIndex += 1
		widget.setPixmap(pixmap)
		widget.setAlphatest(alpha)
		widget.setPixmapScale(BT_SCALE)
		widget.setCornerRadius(self.sy(radius), 15)
		self.place(widget, xPos, yPos, width, height, zPosition)
		return widget

	def fixture(self, bpp, alpha=True, accel=-1):
		if gRenderTest is None:
			return None
		pixmap = gRenderTest.createPixmap(320, 160, bpp, alpha, accel)
		if pixmap is not None:
			self.nativePixmaps.append(pixmap)
			self.formats.append(loads(gRenderTest.pixmapInfo(pixmap)))
		return pixmap

	def showPage(self):
		for index in range(self.LABEL_COUNT):
			self[f"label{index}"].hide()
		for index in range(self.PIXMAP_COUNT):
			self[f"pixmap{index}"].hide()
			self[f"pixmap{index}"].instance.setPixmap(None)
		self.labelIndex = self.pixmapIndex = 0
		self.gradientIndex = self.LABEL_COUNT - 6
		self.nativePixmaps = []
		self.formats = []
		self.caseWidgets = []
		self.uploadWidgets = []
		self.paintWidgets = []
		self["title"].setText(f"GLES TestLab  ·  {self.page + 1}/{len(self.PAGES)}  ·  {self.PAGES[self.page]}")
		self["details"].setText(f"{self.width} × {self.height}  |  Schachbrett = Untergrund  |  E2-Farbalpha: 00 deckend, FF transparent  |  Bildurteil: {self.measurements.verdicts.get(str(self.page), 'ungeprüft')}")
		for case in range(6):
			xPos, yPos = 64 + (case % 3) * 604, 195 + (case // 3) * 342
			self.pixmap(self.checker, xPos, yPos + 45, 560, 250, alpha=0, zPosition=1)
			self.drawCase(case, xPos, yPos)
		if gRenderTest is None:
			self["status"].setText("Diagnose-API fehlt: Formen sichtbar, native Farbtiefen und Renderer-Messung nicht verfügbar.")

	def paintedFixture(self, pattern, accel):
		if gRenderTest is None or not hasattr(gRenderTest, "createPaintedPixmap"):
			return None
		pixmap = gRenderTest.createPaintedPixmap(pattern, accel)
		if pixmap is not None:
			self.nativePixmaps.append(pixmap)
			info = loads(gRenderTest.pixmapInfo(pixmap))
			info["pattern"] = pattern
			if pattern == 0:
				info["cpuColorBarMismatches"] = gRenderTest.verifyColorBars(pixmap)
			self.formats.append(info)
		return pixmap

	def drawCase(self, case, xPos, yPos):
		title = ""
		if self.page == 0 or self.page == 6:
			bpp, alphaMode, accel = ((8, 0, -1), (8, 1, -1), (8, 2, -1), (32, 2, -1), (32, 2, 1), (16, 0, -1))[case]
			fixture = self.fixture(bpp, True, accel)
			title = f"{bpp} bpp · {'HW-Speicher angefordert' if accel == 1 else 'CPU-Speicher'} · Alpha {alphaMode}"
			if bpp == 16:
				title = "16 bpp · RGB565-Upload · ohne Pixelalpha"
			if fixture is not None:
				widget = self.pixmap(fixture, xPos + 20, yPos + 65, 520, 210, alpha=alphaMode, radius=20 if case == 4 else 0)
				if self.page == 6:
					self.uploadWidgets.append((widget, bpp, accel))
		elif self.page == 1:
			transparency = (0, 64, 128, 192, 255, 128)[case]
			title = f"Füllung · Transparenz {transparency}/255 · Blend {'aus' if case == 5 else 'an'}"
			self.label(xPos + 20, yPos + 65, 520, 210, color=(transparency << 24) | 0x18b8ec, alpha=case != 5)
		elif self.page == 2:
			edges = (1, 2, 4, 8, 15, 3)[case]
			title = f"Eckenmaske {edges} · Radius {48 if case != 5 else 110} · Rahmen {4 if case > 3 else 0}"
			self.label(xPos + 20, yPos + 65, 520, 210, color=0x602ccda1 if case > 3 else 0x002ccda1, alpha=case > 3, radius=48 if case != 5 else 110, edges=edges, border=4 if case > 3 else 0)
		elif self.page == 3:
			alpha = case >= 3
			colors = (0x00f03048, 0x00e9c75a, 0x001a9aee) if not alpha else (0x00f03048, 0x80e9c75a, 0xff1a9aee)
			if case % 3 != 2:
				colors = (colors[0], colors[2], colors[2])
			title = f"Verlauf · {'horizontal' if case % 2 else 'vertikal'} · Alpha {'an' if alpha else 'aus'}"
			self.label(xPos + 20, yPos + 65, 520, 210, alpha=alpha, radius=42 if case % 3 else 0, border=3 if case == 5 else 0, gradient=(*colors, 2 if case % 2 else 1))
		elif self.page == 4:
			title = f"Drei Ebenen · {'Pixmap 8/32' if case > 3 else 'Füllung'} · Z-Reihenfolge {case % 2}"
			for layer in range(3):
				zPosition = 12 + (2 - layer if case % 2 else layer)
				if case > 3:
					fixture = self.fixture(8 if layer == 1 else 32)
					if fixture is not None:
						self.pixmap(fixture, xPos + 25 + layer * 100, yPos + 60 + layer * 40, 300, 140, radius=25, zPosition=zPosition)
				else:
					self.label(xPos + 25 + layer * 100, yPos + 60 + layer * 40, 300, 140, color=(0x80000000 if case < 2 else 0x40000000) | (0xe94040, 0x40e960, 0x4080ed)[layer], alpha=True, radius=28 if case > 1 else 0, zPosition=zPosition)
		elif self.page == 7:
			pattern, accel = case % 3, -1 if case < 3 else 1
			fixture = self.paintedFixture(pattern, accel)
			title = f"{'CPU' if case < 3 else 'HW'} · {('RGB / CPU-Prüfung', 'Verlauf / Rahmen / Alpha', 'Blit / Rundung / Alpha')[pattern]}"
			if fixture is not None:
				widget = self.pixmap(fixture, xPos + 20, yPos + 65, 520, 210)
				self.paintWidgets.append((widget, pattern, accel))
				info = self.formats[-1]
				title += f" · {'geteilt' if info.get('sharedNative') else 'Fallback'}" if accel == 1 else ""
				if pattern == 0:
					title += f" · Fehler {info.get('cpuColorBarMismatches', '?')}"
		else:
			title = f"Text, Kanten und Mischung · Fall {case + 1}"
			self.label(xPos + 20, yPos + 65, 520, 210, color=0x70172c60, alpha=True, radius=30, border=2)
			self.label(xPos + 40, yPos + 100, 480, 150, ("ÄÖÜ ß 0123456789\nAlpha und runde Ecken", "Groß / klein / Überlappung\nABCDEFGHIJKLMNOPQRSTUVWXYZ", "العربية · Ελληνικά\nFonthinweis: fehlende Glyphen prüfen")[case % 3], zPosition=30)
		self.label(xPos, yPos, 560, 40, title, zPosition=100)

	def changePage(self, direction):
		if self.phase:
			self.finishRun("aborted")
		self.autoRun = False
		self.page = (self.page + direction) % len(self.PAGES)
		self.showPage()

	def nextPage(self):
		self.changePage(1)

	def previousPage(self):
		self.changePage(-1)

	def markGood(self):
		self.markVisual("manuell OK")

	def markBad(self):
		self.markVisual("manueller Bildfehler")

	def markVisual(self, verdict):
		self.measurements.verdicts[str(self.page)] = verdict
		if not self.phase:
			self.showPage()
			self.saveResults()

	def toggleRun(self):
		if self.phase:
			self.autoRun = False
			self.finishRun("aborted")
		else:
			self.autoRun = False
			self.startRun()

	def startAll(self):
		if self.phase:
			self.autoRun = False
			self.finishRun("aborted")
		self.autoRun = True
		self.page = 0
		self.showPage()
		self.startRun()

	def startRun(self):
		if gRenderTest is None:
			self["status"].setText("Messung nicht gestartet: Dieses E2 enthält die Diagnose-API noch nicht.")
			return
		self.phase = "warmup"
		self.phaseStart = monotonic()
		self.lastSample = self.phaseStart
		self.ticks = []
		self.memorySamples = []
		self["status"].setText("Aufwärmen 2 s, danach 6 s Messung: vollständiges Neuzeichnen alle angeforderten 20 ms. Timer ist kein FPS-Nachweis.")
		self.timer.start(20)

	def tick(self):
		now = monotonic()
		if self.phase == "warmup" and now - self.phaseStart >= self.WARMUP_SECONDS:
			self.captureOwned = gRenderTest.startCapture(4096)
			if not self.captureOwned:
				self.timer.stop()
				self.phase = None
				self["status"].setText("Messung belegt; vorhandener Mitschnitt wurde nicht verändert.")
				return
			self.phase = "measure"
			self.phaseStart = now
			self.before = self.measurements.resources()
		if self.phase == "measure":
			self.ticks.append(now)
			if now - self.lastSample >= 1:
				resources = self.measurements.resources()
				self.memorySamples.append(resources)
				self.lastSample = now
				if resources.get("fds", 0) - self.before.get("fds", 0) > 64:
					self.autoRun = False
					self.finishRun("resource-growth")
					self["status"].setText("Test angehalten: mehr als 64 zusätzliche FDs. Ergebnis gesichert. Nach Leerlauf erneut prüfen.")
					return
			if now - self.phaseStart >= self.MEASURE_SECONDS:
				self.finishRun("complete")
				if self.autoRun and self.page < len(self.PAGES) - 1:
					self.page += 1
					self.showPage()
					self.startRun()
				else:
					self.autoRun = False
				return
		if self.uploadWidgets:
			self.nativePixmaps = []
			self.formats = []
			for widget, bpp, accel in self.uploadWidgets:
				fixture = self.fixture(bpp, True, accel)
				if fixture is not None:
					widget.setPixmap(fixture)
		if self.paintWidgets:
			self.nativePixmaps = []
			self.formats = []
			for widget, pattern, accel in self.paintWidgets:
				fixture = self.paintedFixture(pattern, accel)
				if fixture is not None:
					widget.setPixmap(fixture)
		self.instance.invalidate()

	def finishRun(self, status):
		self.timer.stop()
		if self.captureOwned:
			after = self.measurements.resources()
			renderer = loads(gRenderTest.stopCapture())
			self.captureOwned = False
			columns = renderer["columns"]
			frames = renderer["frames"]
			series = {}
			for index, name in enumerate(columns):
				series[name] = [x[index] for x in frames]
			run = {"page": self.page, "name": self.PAGES[self.page], "status": status, "seconds": after["time"] - self.before["time"], "cpuSeconds": after["cpuSeconds"] - self.before["cpuSeconds"], "before": self.before, "after": after, "memorySamples": self.memorySamples, "sourceSurfaces": self.formats, "renderer": renderer, "workload": "full screen invalidate at requested 20ms; page 6 recreates native sources; page 7 recreates and paints CPU and HW-requested surfaces including CPU verification; 8bit content cache may hit", "unsupported": ["16bit pixel alpha (RGB565 has no alpha channel)", "GPU timer query", "physical GPU memory accounting"], "timerIntervalsMs": self.measurements.distribution([(self.ticks[x] - self.ticks[x - 1]) * 1000 for x in range(1, len(self.ticks))]), "totals": {x[0]: sum(x[1]) for x in series.items() if not x[0].endswith("Us")}}
			for name in ("drawUs", "swapUs", "intervalUs"):
				run[name] = self.measurements.distribution(series[name])
			self.measurements.runs.append(run)
			self.saveResults()
			rss = NumberScaler().scale(after.get("VmRSS", 0), style="Iec", maxNumLen=3, decimals=1)
			self["status"].setText(f"{len(frames)} Renderer-Abschlüsse · CPU {run['cpuSeconds']:.2f} s · Draw p95 {run['drawUs'].get('p95', 0)} µs · Present-Aufruf p95 {run['swapUs'].get('p95', 0)} µs\nRSS {rss} · ION-Uploads {run['totals'].get('ionUploads', 0)} · Datei: {self.measurements.runId}")
		self.phase = None

	def saveResults(self):
		try:
			self.savedPath = self.measurements.save()
		except OSError as error:
			self.savedPath = f"Speicherfehler: {error}"
			print(f"[GlesTestLab] {self.savedPath}")

	def cleanup(self):
		self.autoRun = False
		if self.phase:
			self.finishRun("closed")
		self.timer.stop()
		self.timer.callback.remove(self.tick)
		self.nativePixmaps = []


def main(session, **kwargs):
	session.open(GlesTestLabScreen)


def Plugins(**kwargs):
	return [PluginDescriptor(name="GLES TestLab", description="Bildprüfung und Renderer-Messung", where=[PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=main, needsRestart=False)]
