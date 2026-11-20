from copy import deepcopy
from gettext import bindtextdomain, dgettext
from os.path import dirname, isdir, join
from xml.etree.ElementTree import Element

from enigma import eListbox, eListboxPythonMultiContent, getDesktop

from skin import domScreens, getcomponentTemplate, getcomponentTemplateNames
from Components.config import ConfigSelection, config
from Components.MovieLibrary import movieLibrary
from Components.MultiContent import MultiContentEntryProgress
from Components.Converter.XmlMultiContent import MultiContentTemplateParser
from Tools.Directories import SCOPE_PLUGINS, resolveFilename


class MovieListStyles:
	def refreshChoices(self):
		movieLibrary.refreshChoices()
		displayChoices = [("legacy", _("Default skin layout")), ("information", _("Movie information"))]
		if movieLibrary.getProvider() is not None:
			displayChoices.append(("artwork", _("Movie artwork")))
		config.movielist.displayStyle.setChoices(displayChoices, default="information")
		skinDomain = dirname(config.skin.primary_skin.value).replace("MetrixHD", "MyMetrixLite")
		localePath = resolveFilename(SCOPE_PLUGINS, join("Extensions", skinDomain, "locale"))
		translate = _
		if skinDomain and isdir(localePath):
			bindtextdomain(skinDomain, localePath)
			translate = lambda text: dgettext(skinDomain, text)  # noqa: E731
		screenChoices = [("", _("Default skin layout"))]
		for name, (element, path) in domScreens.items():
			if element.get("base") == "MovieSelection":
				screenChoices.append((name, translate(element.get("label", name))))
		styleLabels = {
			"classic": _("Classic movie list (EMC)"),
			"classicExtended": _("Classic movie list with description (EMC)"),
			"compact": _("Compact list"),
			"detailed": _("Information list"),
			"tiles": _("Tiles"),
			"tilesLarge": _("Large tiles"),
			"posters": _("Poster grid"),
			"posterList": _("Poster list")
		}
		styleNames = getcomponentTemplateNames("movieList") or ()
		widgetChoices = [("", _("Legacy mode"))]
		artworkAvailable = any("details" in getattr(x[1], "capabilities", ()) for x in movieLibrary.providers.values())
		for name in styleNames:
			template = getcomponentTemplate("movieList", name)
			fields = template
			if not artworkAvailable and fields is not None and any(x.get("index") in ("Poster", "Preview") for x in fields.iter("pixmap")):
				continue
			label = translate(template.get("label")) if template is not None and template.get("label") else styleLabels.get(name, name)
			widgetChoices.append((name, label))
		playerChoices = [("", _("Default skin layout"))]
		playerChoices.extend((name, translate(element.get("label", name))) for name, (element, path) in domScreens.items() if element.get("base") == "MoviePlayer")
		for name, choices in (("screenStyle", screenChoices), ("widgetStyle", widgetChoices), ("playerStyle", playerChoices)):
			setting = getattr(config.movielist, name, None)
			if setting is None:
				setattr(config.movielist, name, ConfigSelection(default="", choices=choices))
			else:
				setting.setChoices(choices, default="")

	def getScreenNames(self, library=False, screenStyle=None):
		screenStyle = config.movielist.screenStyle.value if screenStyle is None else screenStyle
		if library and movieLibrary.getProvider() is None:
			return self.getScreenNames(library=False, screenStyle=screenStyle)
		if library:
			names = ["MovieLibrarySelection"]
			screen = domScreens.get(screenStyle)
			if screen and screen[0].get("libraryScreen"):
				names.insert(0, screen[0].get("libraryScreen"))
			return self.getProviderScreenNames(names)
		names = ["MovieSelectionSlim", "MovieSelection"] if config.movielist.useslim.value else ["MovieSelection"]
		if screenStyle:
			names.insert(0, screenStyle)
		return self.getProviderScreenNames(names)

	def getProviderScreenNames(self, names):
		if movieLibrary.getProvider() is None:
			for name in names:
				screen = domScreens.get(name)
				if screen and screen[0].get("simpleScreen"):
					return [screen[0].get("simpleScreen"), *names]
		return names

	def createTemplate(self, name, width, height, scale, mode="default"):
		template = getcomponentTemplate("movieList", name)
		if template is None:
			return None
		try:
			if template.get("resolution"):
				resolution = tuple(int(x) for x in template.get("resolution").split(","))
				if len(resolution) != 2 or min(resolution) <= 0:
					raise ValueError("Invalid movie template resolution")
				scale = ((getDesktop(0).size().height(), resolution[1]),) * 2
			return MovieListTemplate(template, width, height, scale, mode)
		except (ValueError, TypeError, KeyError, IndexError, ZeroDivisionError) as error:
			print(f"[MovieListStyle] Invalid style '{name}': {error}. Using the legacy list.")
			return None


class MovieListTemplate(MultiContentTemplateParser):
	INDEX_NAMES = {"Title": 0, "Date": 1, "Description": 2, "ServiceName": 3, "Status": 4, "Progress": 5, "Kind": 6, "Poster": 7, "Year": 8, "Rating": 9, "FileInfo": 10, "Preview": 11}

	def __init__(self, template, width, height, scale, mode="default"):
		MultiContentTemplateParser.__init__(self)
		self.indexNames = self.INDEX_NAMES
		self.scale = scale
		self.itemWidth = max(1, int(width * scale[0][1] / scale[0][0]))
		self.itemHeight = max(1, int(height * scale[1][1] / scale[1][0]))
		template = deepcopy(template)  # The skin registry is shared with other screens.
		selectedMode = next((x for x in template.findall("mode") if x.get("name") == mode), None)
		if selectedMode is None:
			mode = "default"
			selectedMode = template.find("mode[@name='default']")
		orientation = selectedMode.get("orientation", template.get("orientation", "vertical")) if selectedMode is not None else template.get("orientation", "vertical")
		if orientation not in ("vertical", "grid"):
			raise ValueError("Movie styles support vertical lists and grids")
		self.isGrid = orientation == "grid"
		template.set("itemWidth", str(min(self.itemWidth, max(1, int(template.get("itemWidth", self.itemWidth))))) if self.isGrid else str(self.itemWidth))
		template.set("itemHeight", str(int(template.get("itemHeight", "40"))))
		for element in template.findall("mode"):
			grid = element.get("orientation", template.get("orientation", "vertical")) == "grid"
			element.set("itemWidth", str(min(self.itemWidth, max(1, int(element.get("itemWidth", template.get("itemWidth")))))) if grid else str(self.itemWidth))
		self.dom = Element("templates")
		self.dom.append(template)
		for element in template.iter():
			field = element.get("index")
			if field is not None and field not in self.INDEX_NAMES:
				raise ValueError(f"Unknown movie field '{field}'")
			if field is not None and element.tag not in ("text", "progress", "pixmap"):
				raise ValueError("Movie fields support text, progress and pixmap elements")
			if field is not None and ((field in ("Poster", "Preview")) != (element.tag == "pixmap")):
				raise ValueError("Pixmap elements must use the Poster or Preview field")
			if element.tag == "progress" and field != "Progress":
				raise ValueError("Progress elements must use the Progress field")
		self.readTemplate(template.get("name"))
		mode = self.template["modes"].get(mode)
		if not mode or not mode[1] or not self.template["fonts"]:
			raise ValueError("A movie style needs fonts and a non-empty default template")
		self.itemWidth, self.itemHeight = self.scaleWithHeight(*mode[0])
		if not (0 < self.itemWidth <= width and 0 < self.itemHeight <= height):
			raise ValueError("Template dimensions exceed the movie list")
		self.content = []
		self.fields = set()
		fieldNames = {self.INDEX_NAMES[x]: x for x in self.INDEX_NAMES}
		for item in mode[1]:
			if item[0] == eListboxPythonMultiContent.TYPE_TEXT:
				if isinstance(item[7], int):
					self.fields.add(fieldNames[item[7]])
				if not 0 <= item[5] < len(self.template["fonts"]):
					raise ValueError("Text references an undefined font")
			elif item[0] == eListboxPythonMultiContent.TYPE_PROGRESS:
				self.fields.add("Progress")
				# Native template progress uses negative data indices and the full progress tuple.
				item = MultiContentEntryProgress(pos=item[1:3], size=item[3:5], percent=-self.INDEX_NAMES["Progress"], borderWidth=item[6], foreColor=item[7], foreColorSelected=item[8], borderColor=item[9], startColor=item[10], midColor=item[11], endColor=item[12], startColorSelected=item[13], midColorSelected=item[14], endColorSelected=item[15], cornerRadius=item[16], cornerEdges=item[17])
			elif item[0] in (eListboxPythonMultiContent.TYPE_PIXMAP, eListboxPythonMultiContent.TYPE_PIXMAP_ALPHATEST, eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND) and isinstance(item[5], int):
				self.fields.add(fieldNames[item[5]])
			self.content.append(item)
		self.fields = frozenset(self.fields)

	def apply(self, content):
		content.setOrientation(eListbox.orGrid if self.isGrid else eListbox.orVertical)
		content.setItemWidth(self.itemWidth)
		content.setItemHeight(self.itemHeight)
		for index, font in enumerate(self.template["fonts"]):
			content.setFont(index, font)
		content.setTemplate(self.content)


movieListStyles = MovieListStyles()
