# Enigma2 Python Code Style Guide

Not all files in the codebase follow these rules — when editing legacy code, apply rules only to the lines you touch, unless a full cleanup is planned.

---

## General rules

1. Write human readable code.
2. Write code so that it looks like it was written by a human, the same human who wrote the rest of the code.
3. Use variable names that explain what the variable is for and what it does.
4. Keep UI components consistent, coherent and familiar with all the other UI code.
5. Write code that flows in a logical progression and does not require jumping all over the current and other modules to make sense.
6. Don't create a mess of modules where the code is not being shared.
7. Don't define static items in a module that doesn't use them and force an import into the module that does use them.
8. Don't create a method if the code is only a few lines long and the method is only used once.
9. Use `Screens/Menu.py` and `Screens/Setup.py` as reference examples for screens.
10. When creating new code, tell the skinners what they need to do to skin it.
11. Use screen variables that allow screens to be shared or "panel"ed as appropriate.
12. Don't use Python reserved words or builtin names as variable names.
13. Follow PEP 8. Not every PEP 8 rule is used, but most are; see [PEP 8 rules enforced by autopep8](#pep-8-rules-enforced-by-autopep8) below.

---

## Indentation

Tabs, not spaces.  
`W191` (indentation contains tabs) is explicitly ignored in ruff.

```python
class MyScreen(Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		self.myValue = 0
```

---

## Naming conventions

### Classes

`PascalCase`

```python
class MyScreen(Screen):
class ConfigListScreen:
class MultiContentTemplateParser(TemplateParser):
```

### Functions and methods

`camelCase`

```python
def createMenuList(self):
def selectionChanged(self):
def addItem(self, element):
```

### Module-level constants

`UPPER_SNAKE_CASE` — immutable values that represent fixed configuration, indices, or flags.  
Keep module-level constants to a minimum. Prefer class constants where possible, see [Helper class instead of module-level code](#helper-class-instead-of-module-level-code).

```python
MENU_TEXT = 0
MENU_MODULE = 1
ALLOW_SUSPEND = False
MODULE_NAME = __name__.split(".")[-1]
```

### Module-level variables (mutable)

`camelCase` — dictionaries, lists, or other state that changes at runtime.

```python
domScreens = {}
windowStyles = {}
scrollLabelStyle = {}
```

### Instance variables

`self.camelCase`

```python
self.menuList = []
self.pluginLanguageDomain = None
self.timerEntry = None
```

### Private / internal

Don't prefix names with an underscore `_`. Python doesn't enforce privacy anyway and the prefix makes the code harder to read.

```python
# Bad
self._dynPhase = 0

def _updateDynamicStack(self):
	pass

# Good
self.dynPhase = 0

def updateDynamicStack(self):
	pass
```

### Parameters

`camelCase`, same as local variables.

```python
def addFunctionTimer(key, name, entryFunction, cancelFunction, useOwnThread=False):
```

---

## Backward compatibility — do not rename

Some identifiers are part of the public API and **must not be renamed**, even if they violate style rules, because external plugins and skins depend on them by name.

### Screen widget keys

`self["name"]` keys are referenced both in the skin XML and by external plugins.  
Renaming them silently breaks all plugins that access them.

```python
# self["list"] is used in skin XML as name="list" and by plugins as screen["list"]
self["list"] = List(entries)
self["key_red"] = StaticText(_("Exit"))
```

### Public API methods

Methods that are called by the framework, overridden by subclasses, or called from plugins must keep their existing names, regardless of case style.

Common examples:
- `selectionChanged` — called by listbox components
- `layoutFinished` — called by the screen framework
- `ok`, `cancel` — mapped to key actions
- `createSummary` — called by the screen framework for LCD summary screens

### Class-level skin attributes

These attributes are read by the framework and must not be renamed:

| Attribute      | Purpose                                      |
| -------------- | -------------------------------------------- |
| `skin`         | Inline skin XML string                       |
| `skinName`     | List of skin fallback names                  |
| `ALLOW_SUSPEND` | Controls standby/shutdown permission        |
| `ENABLE_RESUME_AFTER_POWEROFF` | Wakeup behavior              |

### Config paths

`config.x.y.z` paths are persisted to disk and used by plugins.  
Never rename a config key once it has been released — doing so discards saved user settings.

---

## Import order

Imports are grouped in this order:

1. Python standard library (`os`, `time`, ...)
2. Third-party packages like `twisted` or `PIL`
3. `enigma`
4. `skin`, `Components.*`, `Plugins.Plugin`, `Screens.*`, `Tools.*`
5. Absolute imports of the plugin's own modules (`Plugins.Extensions.MyPlugin.*`)
6. Relative imports (rare)

- There is **no blank line** between groups 1 and 2. All other groups are separated by one blank line.
- Within each group, imports are sorted alphabetically by module path and case-insensitive, `import x` and `from x import y` mixed.
- Module paths are sorted by folder: first the modules directly in a folder, then its sub folders. So `skin` and `ServiceReference` (in `lib/python`) come before `Components.*`, and `Components.Element` comes before `Components.Converter.*`. This is not done for the Python standard library, `os.path` stays before `re`.
- Multiple names from the same module go on one line, sorted alphabetically, also with `as`. Lines are never wrapped.

```python
from gettext import dgettext
from os.path import getmtime, isdir, isfile, join
from twisted.internet.threads import deferToThread

from enigma import eTimer, eWindowStyleManager

from skin import menus
from Components.ActionMap import HelpableActionMap, HelpableNumberActionMap
from Components.config import ConfigDictionarySet, NoSave, config, configfile
from Components.Label import Label
from Components.SystemInfo import BoxInfo, getBoxDisplayName
from Components.Sources.List import List
from Components.Sources.StaticText import StaticText
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen, ScreenSummary
from Screens.Setup import Setup
from Tools.BoundFunction import boundFunction
from Tools.Directories import SCOPE_GUISKIN, SCOPE_SKINS, fileReadXML, resolveFilename
from Tools.LoadPixmap import LoadPixmap

from Plugins.Extensions.MyPlugin.MyList import MyList

from .client import uploadReport
```

**No multiple modules on one line** (`import os, sys` → `E401`).

### Always use `from` imports

Always import names directly with `from module import name`, for example `from os import close`. Never use the bare `import module` form and then access names via dotted path.

```python
# Bad
import os
if os.path.exists(path):
    os.path.join(a, b)

# Good
from os.path import exists, join
if exists(path):
    join(a, b)
```

```python
# Bad
import os
import sys

# Good
from os import listdir, unlink
from os.path import dirname, isfile, join
from sys import argv
```

This applies to stdlib, enigma, all enigma2 modules and other modules like `twisted`, `PIL` or `qrcode` alike. There is no exception: also a long list of names goes into one `from` line. If a name clashes with a builtin or another import, rename it with `as` (`from os import open as osOpen`).

### Imports at the top

Put all imports at the top of the module whenever possible.  
Only import inside a function when really needed, e.g. to prevent circular imports. Add a short comment why.

```python
# Bad
def showInfo(self):
	from Screens.MessageBox import MessageBox
	self.session.open(MessageBox, _("Done."), MessageBox.TYPE_INFO)

# Good — local import only to prevent a circular import
def openSetup(self):
	from Screens.Setup import Setup  # Prevent circular import.
	self.session.open(Setup, "MySetup")
```

### No wildcard imports

`from module import *` is not allowed. It pollutes the namespace and makes it impossible to tell where a name comes from.

```python
# Bad
from Components.config import *
from enigma import *

# Good
from Components.config import ConfigBoolean, ConfigSelection, config
from enigma import eTimer, eListbox
```

Ruff enforces this via `F401` (unused names) and `F821` (undefined names), which wildcard imports routinely mask.

### Translation builtins

`_`, `ngettext`, and `pgettext` are declared as builtins in `pyproject.toml`.  
Do not import them — they are always available.

```python
# Correct — no import needed
label = _("Settings")
```

### Plugin translations

Special case: plugins with their own translation domain define `PluginLanguageDomain`, `PluginLanguagePath` and their own `_()` in the plugin's `__init__.py`.  
`_()` looks in the plugin domain first and falls back to the enigma2 translation.  
The plugin modules import it with `from . import _`.

```python
# __init__.py
PluginLanguageDomain = "MyPlugin"
PluginLanguagePath = "Extensions/MyPlugin/locale"


def localeInit():
	bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


def _(text):
	translated = dgettext(PluginLanguageDomain, text)
	return gettext(text) if translated == text else translated
```

`PluginLanguageDomain` and `PluginLanguagePath` keep these names although they are constants. `PluginLanguageDomain` matches the `PluginLanguageDomain` parameter of `Setup`, and many plugins use both names.  
Don't use another name like `translate()` for the translation function, `xgettext` finds `_()` by default.

---

## Code patterns

### Single return

Use a single `return` at the end of a function where possible.  
Don't force it if early returns keep the code easier to read.

```python
# Bad
def getServiceName(self, serviceReference):
	if serviceReference is None:
		return ""
	info = eServiceCenter.getInstance().info(serviceReference)
	if info is None:
		return ""
	return info.getName(serviceReference)

# Good
def getServiceName(self, serviceReference):
	serviceName = ""
	info = serviceReference and eServiceCenter.getInstance().info(serviceReference)
	if info:
		serviceName = info.getName(serviceReference)
	return serviceName
```

### List comprehensions

Use list comprehensions where possible.  
Inside a comprehension the loop variable is always `x`.

```python
# Bad
choices = []
for adapter in adapters:
	if adapter.isActive:
		choices.append((adapter.name, adapter.description))

# Good
choices = [(x.name, x.description) for x in adapters if x.isActive]
```

### Tuple or set instead of list

Use a tuple for fixed sequences and a set for membership tests where possible.  
A list is only needed when the content changes.

```python
# Bad
if mode in ["auto", "manual", "off"]:
	pass
for key in ["red", "green", "yellow", "blue"]:
	pass

# Good
if mode in ("auto", "manual", "off"):
	pass
for key in ("red", "green", "yellow", "blue"):
	pass

SKIP_EXTENSIONS = {".tmp", ".bak", ".swp"}
if extension in SKIP_EXTENSIONS:
	pass
```

### Helper class instead of module-level code

Avoid module-level functions and constants. Group related constants, data and functions in a helper class with one module-level instance.  
Only functions that the framework calls by name, like `Plugins()`, `main()` or an autostart function, stay at module level and just call the helper.

```python
# Bad
DEVICE_PATH = "/proc/stb/xyz"
MODES = (("0", "Off"), ("1", "On"))


def readMode():
	with open(DEVICE_PATH) as fd:
		return fd.read().strip()


# Good
class DeviceHelper:
	DEVICE_PATH = "/proc/stb/xyz"

	def __init__(self):
		self.modes = (("0", "Off"), ("1", "On"))

	def readMode(self):
		with open(self.DEVICE_PATH) as fd:
			mode = fd.read().strip()
		return mode


deviceHelper = DeviceHelper()


def autostart(reason, **kwargs):
	if reason == 0:
		deviceHelper.applyMode()
```

### Path concatenation

Use `join` from `os.path` to build paths. Import it as `join`, not under another name.
Don't concatenate paths with `+`, `%` or f-strings.

```python
# Bad
path = directory + "/" + fileName
path = f"{directory}/{fileName}"
from os.path import join as pathjoin

# Good
from os.path import join
path = join(directory, fileName)
```

### f-strings

Use f-strings where possible, instead of `%` formatting, `str.format()` or `+` concatenation.

```python
# Bad
print("[Example] Error %d: %s" % (err.errno, err.strerror))
text = "Version " + version
text = "{} of {}".format(index, count)

# Good
print(f"[Example] Error {err.errno}: {err.strerror}")
text = f"Version {version}"
text = f"{index} of {count}"
```

Exception: translatable texts. The msgid must be a constant string, so keep `%` there.

```python
# Good
text = _("Tracking: %s") % tracking
```

### Shell commands

Run commands without an extra shell where possible and always use the full path of the binary.  
Pass a tuple to `Console().ePopen()`: the binary, `argv[0]` and then the arguments.  
Only use a command string (which starts a shell) when shell features like pipes or redirection are really needed.

```python
# Bad — starts /bin/sh and depends on $PATH
self.console.ePopen(f"ifconfig {self.adapter} up", callback=ifUpCallback)

# Good — no shell, full path
self.console.ePopen(("/sbin/ifconfig", "/sbin/ifconfig", self.adapter, "up"), callback=ifUpCallback)
```

### Sizes and units

Use `NumberScaler` from `Tools.Conversions` to show sizes like KB, MB or GB. Don't divide by 1024 and add the unit by hand.  
`style` selects the units: `"Si"` (kB, MB, GB, base 1000), `"Iec"` (KiB, MiB, GiB, base 1024) or `"Jedec"` (KB, MB, GB, base 1024).  
Use `UnitScaler` when you need the number and the unit prefix separately.

```python
# Bad
size = f"{freeSpace / 1024 / 1024:.1f} MB"

# Good
from Tools.Conversions import NumberScaler

size = NumberScaler().scale(freeSpace, style="Iec", maxNumLen=3, decimals=1)  # "1.5 MiB"
```

---

## Screens

### Color buttons

Fill the four color buttons from left to right without gaps: red, green, yellow, blue.  
Red is almost always close / exit / cancel.  
Keep the button texts short.

```python
# Bad — gap at green, long text
self["key_red"] = StaticText(_("Cancel"))
self["key_yellow"] = StaticText(_("Edit the selected entry"))

# Good
self["key_red"] = StaticText(_("Cancel"))
self["key_green"] = StaticText(_("Edit"))
```

### Setup screens

Setup based classes should subclass `Setup` and not `ConfigListScreen`.  
Use a setup XML file when possible. A screen with only one or two entries doesn't need one, use `setup=None` and override `createSetup()` instead.

```python
# Bad
class MySetup(ConfigListScreen, Screen):
	def __init__(self, session):
		Screen.__init__(self, session)
		...

# Good
class MySetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, setup="MySetup")

# Good — only one entry, no XML file
class MySetup(Setup):
	def __init__(self, session):
		Setup.__init__(self, session, setup=None)

	def createSetup(self):
		self.list = [(_("My option"), config.plugins.myPlugin.option, _("Description of my option."))]
		self["config"].setList(self.list)
		self.setTitle(_("My Setup"))
```

---

## PEP 8 rules enforced by autopep8

The following rule codes are applied automatically. Violations in new code should be avoided.

### E401 — one import per line

```python
# Bad
import os, sys

# Good
import os
import sys
```

### E502 — redundant backslash inside brackets

```python
# Bad
result = (value1 + \
          value2)

# Good
result = (value1 +
          value2)
```

### E251 / E252 — spaces around parameter defaults

```python
# Bad
def foo(x =1, y: int=2):

# Good — no spaces for plain defaults, spaces around annotated defaults
def foo(x=1, y: int = 2):
```

### E20x — whitespace before/after brackets

```python
# Bad
spam( ham[1], { eggs: 2 } )
list [0]

# Good
spam(ham[1], {"eggs": 2})
list[0]
```

### E211 — whitespace before `(` or `[`

```python
# Bad
spam (1)
dct ['key']

# Good
spam(1)
dct['key']
```

### E225 / E226 / E227 / E228 — whitespace around operators

```python
# Bad
x=1
y =x+1
flags=a|b

# Good
x = 1
y = x + 1
flags = a | b
```

### E231 — whitespace after `,`, `;`, `:`

```python
# Bad
a = (1,2,3)
d = {"a":1}

# Good
a = (1, 2, 3)
d = {"a": 1}
```

### E241 / E242 — multiple spaces or tab after `,`

```python
# Bad
a = (1,  2,	3)

# Good
a = (1, 2, 3)
```

### E261 / E262 — inline comment format

```python
# Bad
x = 1 # comment
x = 1  #comment
x = 1  ## comment

# Good — two spaces before, one space after #
x = 1  # comment
```

### E701 — multiple statements on one line (colon)

```python
# Bad
if x: pass
for i in l: print(i)

# Good
if x:
    pass
for i in l:
    print(i)
```

### E301 / E302 / E303 / E304 / E305 / E306 — blank lines

```python
# E302: two blank lines before top-level class or function
def foo():
    pass


def bar():       # two blank lines before
    pass


class MyClass:   # two blank lines before
    pass


# E301: one blank line before a method inside a class
class MyClass:
    def method_a(self):
        pass

    def method_b(self):   # one blank line before
        pass


# E303: max two blank lines (three or more → error)
# E304: no blank line between decorator and def
@decorator
def foo():       # no blank line after decorator
    pass


# E305: two blank lines after last function/class definition before module-level code
class Foo:
    pass


x = 1            # two blank lines after class


# E306: one blank line before nested function/class
def outer():
    x = 1

    def inner():  # one blank line before nested def
        pass
```

### W291 / W292 / W293 / W391 — trailing whitespace and file endings

- `W291` — no trailing spaces on non-empty lines
- `W292` — file must end with a newline
- `W293` — no trailing whitespace on blank lines
- `W391` — no blank line at the very end of the file

---

## Ruff rules

Configuration in `pyproject.toml`:

```toml
[tool.ruff]
builtins = ["_", "ngettext", "pgettext"]
select = ["E", "F", "W"]
ignore = ["W191", "E501"]
```

| Ignored rule | Reason                                              |
| ------------ | --------------------------------------------------- |
| `W191`       | Tabs are the required indentation style             |
| `E501`       | Line length is not enforced                         |

### Key F (Pyflakes) rules that ruff enforces

| Rule   | Description                                          |
| ------ | ---------------------------------------------------- |
| `F401` | Imported name is unused — remove it or add `# noqa F401` if it is a re-export |
| `F811` | Name re-defined in the same scope (e.g. duplicate import) |
| `F821` | Undefined name used                                  |
| `F841` | Local variable is assigned but never used            |
| `F401` with `# noqa` | Use `# noqa F401` when an import is intentionally re-exported |

```python
# Intentional re-export — suppress F401
from Tools.Directories import resolveFilename  # noqa F401
```

### Suppressing a rule for one line

```python
x = unused_var  # noqa F841
from module import name  # noqa F401
```

Use sparingly — only when the suppression is genuinely correct, not to silence a real bug.

---

## Testing

1. Test your changes. Then test them again.
2. Test as many options as possible, not just your personal configuration. The code is not just for you.
3. If you want others to test your code, give them a test plan.
4. If you can't test all the options your code addresses, ask for testing help. Tell the helpers what you need tested, what to expect and what not to expect.
5. If you ask others to test, freeze that version of the code so you can verify their issue reports. Then confirm that their issues are fixed in the next test version.
6. If you are testing hardware drivers or hardware-related code, make sure you have enough test devices to reasonably test it.
