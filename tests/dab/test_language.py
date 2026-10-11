"""Host UI tests: real helpers, CurrentService, ServiceInfo and screen methods.
Only native receiver bindings and UI construction are substituted.
"""
import ast
import builtins
import sys
from importlib import import_module
from pathlib import Path
from types import ModuleType, SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib/python"))
builtins._ = lambda text: f"translated:{text}"


def stub(name, **values):
    module = ModuleType(name)
    module.__dict__.update(values)
    sys.modules[name] = module
    return module


# Use the actual language data and accessors without initializing package tools.
tree = ast.parse((ROOT / "lib/python/Components/International.py").read_text())
cls = next(node for node in tree.body if isinstance(node, ast.ClassDef))
keep = {"LANG_NAME", "LANG_TRANSLATED", "LANG_MAX", "LANGUAGE_DATA"}
cls.body = [node for node in cls.body if (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in keep for t in node.targets)) or (isinstance(node, ast.FunctionDef) and node.name in {"getLanguage", "getLanguageTranslated"})]
ns = {"_": builtins._}
exec(compile(ast.Module(body=[cls], type_ignores=[]), "International.py", "exec"), ns)
stub("Components.International", international=ns["International"]())
dab = import_module("Tools.DAB")
DAB_LANGUAGE_IDENTIFIERS, getDABLanguageName = dab.DAB_LANGUAGE_IDENTIFIERS, dab.getDABLanguageName
LanguageCodes = import_module("Tools.ISO639").LanguageCodes

for identifier in DAB_LANGUAGE_IDENTIFIERS.values():
    assert identifier in LanguageCodes or identifier in ns["International"].LANGUAGE_DATA, identifier
assert getDABLanguageName("112") == "translated:Greek"
assert getDABLanguageName("9") == "translated:English"
assert getDABLanguageName("91") == "translated:Papiamento"
for value in (None, "", "Unknown", "0", "44", "128", "-1"):
    assert getDABLanguageName(value) == ""
assert getDABLanguageName("Greek") == "Greek"


class Constants:
    def __init__(self):
        self.values = {}

    def __getattr__(self, name):
        return self.values.setdefault(name, len(self.values) + 1)


events, fields = Constants(), Constants()


class Reference:
    idServiceDAB = 10

    def __init__(self, value):
        self.type = int(value.split(":")[0])

    def getUnsignedData(self, index):
        return 0


stub("enigma", eAVControl=None, eServiceReference=Reference, iPlayableService=events, iServiceInformation=fields, eServiceCenter=None)
stub("Tools.Transponder", ConvertToHumanReadable=None)
stub("NavigationInstance", instance=None)


class PerServiceBase:
    def __init__(self, navcore, eventmap, with_event=False):
        self.eventmap = eventmap


stub("Components.PerServiceDisplay", PerServiceBase=PerServiceBase)
CurrentService = import_module("Components.Sources.CurrentService").CurrentService
ServiceInfo = import_module("Components.Converter.ServiceInfo").ServiceInfo


class Info:
    def __init__(self, path):
        self.data = {fields.sServiceref: f"10:0:0:0:0:0:0:0:0:0:dab://{path}/"}

    def getInfoString(self, field):
        return self.data.get(field, "")

    def getInfo(self, field):
        return -2 if field in self.data else -1


for path in ("dvb", "rtlsdr"):
    info = Info(path)
    service = SimpleNamespace(info=lambda: info, frontendInfo=lambda: None)
    nav = SimpleNamespace(getCurrentService=lambda: service, getCurrentlyPlayingServiceReference=lambda: Reference("10:"))
    source = CurrentService(nav)
    language, protection = ServiceInfo("DABLanguage"), ServiceInfo("DABProtection")
    language.connect(source)
    protection.connect(source)
    # Reads during downstream notifications exercise the production cached decorator.
    readings = []

    class Renderer:
        def changed(self, what):
            readings.append((language.text, protection.text))

    language.connectDownstream(Renderer())
    assert language.text == protection.text == ""
    for code, level, expected in (("112", "EEP 3-A", "translated:Greek"), ("9", "EEP 2-A", "translated:English"), ("0", "Unknown", "")):
        info.data.update({fields.sTagLanguageCode: code, fields.sDABProtection: level})
        source.eventmap[events.evUpdatedInfo](events.evUpdatedInfo)
        assert readings[-1] == (expected, "" if level == "Unknown" else level)
        assert language.text == expected
    service = None
    source.serviceEvent(events.evEnd)
    assert language.text == protection.text == ""

# Execute the real InformationService callback and rendering method, without widgets.
tree = ast.parse((ROOT / "lib/python/Screens/Information.py").read_text())
cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "InformationService")
methods = [node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name in {"serviceInformationUpdated", "showServiceInformation"}]
ns = {"_": lambda x: x, "eServiceReference": Reference, "iServiceInformation": fields, "getDABLanguageName": getDABLanguageName, "getRTLSDRChannelFrequency": lambda x: None}
exec(compile(ast.Module(body=methods, type_ignores=[]), "Information.py", "exec"), ns)
info = Info("dvb")
starts = []
screen = SimpleNamespace(session=SimpleNamespace(nav=SimpleNamespace(getCurrentlyPlayingServiceReference=lambda: Reference("10:"))), informationTimer=SimpleNamespace(start=lambda *args: starts.append(args)), serviceReferenceType=10, serviceInfo=info, serviceName="ERT", service=None, formatLine=lambda indent, label, value=None: (label, value))
ns["serviceInformationUpdated"](screen)
assert starts == [(25, True)]
for code, expected in (("112", "translated:Greek"), ("9", "translated:English"), ("0", None)):
    info.data[fields.sTagLanguageCode] = code
    info.data[fields.sDABProtection] = "EEP 3-A" if expected else "Unknown"
    rows = ns["showServiceInformation"](screen)
    language_rows = [row for row in rows if isinstance(row, tuple) and row[0] == "Language"]
    assert language_rows == ([] if expected is None else [("Language", expected)])
    protection_rows = [row for row in rows if isinstance(row, tuple) and row[0] == "Protection"]
    assert protection_rows == ([] if expected is None else [("Protection", "EEP 3-A")])
print("UI tests passed: both paths, late language, changes, unavailable values, cached converter and existing information screen")
