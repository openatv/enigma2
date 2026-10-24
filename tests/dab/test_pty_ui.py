"""Run with python3 tests/dab/test_pty_ui.py; no receiver is required."""
import builtins
import importlib
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lib/python"))
builtins._ = lambda text: text


class Constants:
	def __getattr__(self, name):
		value = len(self.__dict__) + 1
		setattr(self, name, value)
		return value


def module(name, **attributes):
	result = types.ModuleType(name)
	result.__dict__.update(attributes)
	sys.modules[name] = result
	return result


events = Constants()
fields = Constants()
reference = type("Reference", (), {"idServiceDAB": 4115, "__init__": lambda self, value: setattr(self, "type", int(value.split(":")[0]))})
module("enigma", eAVControl=object, eServiceReference=reference, iPlayableService=events, iServiceInformation=fields)
module("Components.International", international=types.SimpleNamespace(getLanguageName=lambda code: code))
module("Tools.Transponder", ConvertToHumanReadable=lambda value: value)
ServiceInfo = importlib.import_module("Components.Converter.ServiceInfo").ServiceInfo
metadata = importlib.import_module("Tools.DAB").dabMetadata


class Info:
	def __init__(self):
		self.code = -1
		self.table = -1
		self.genre = "DL Plus genre"
		self.reference = "4115:0:0"

	def getInfo(self, field):
		return {fields.sDABPTY: self.code, fields.sDABPTYTable: self.table}.get(field, -1)

	def getInfoString(self, field):
		return {fields.sServiceref: self.reference, fields.sTagGenre: self.genre}.get(field, "")


class PTYTests(unittest.TestCase):
	def setUp(self):
		self.info = Info()
		self.converter = ServiceInfo("DABPTY")
		self.converter.source = types.SimpleNamespace(service=types.SimpleNamespace(info=lambda: self.info))

	def test_late_values_changes_and_clear(self):
		# Use the real Element cache while a renderer consumes each event.
		values = []
		self.converter.downstream_elements.append(types.SimpleNamespace(changed=lambda *args: values.append(self.converter.text)))
		self.assertEqual(self.converter.text, "")
		self.info.code = 1
		self.converter.changed((self.converter.CHANGED_SPECIFIC, events.evUpdatedInfo))
		self.assertEqual(values[-1], "")  # Table not known yet.
		self.info.table = 1
		self.converter.changed((self.converter.CHANGED_SPECIFIC, events.evUpdatedInfo))
		self.assertEqual(values[-1], "News")
		self.info.code = 24
		self.converter.changed((self.converter.CHANGED_SPECIFIC, events.evUpdatedInfo))
		self.assertEqual(values[-1], "Jazz Music")
		self.info.code = -1
		self.converter.changed((self.converter.CHANGED_SPECIFIC, events.evUpdatedInfo))
		self.assertEqual(values[-1], "")
		self.converter.source.service = None
		self.converter.changed((self.converter.CHANGED_SPECIFIC, events.evEnd))
		self.assertEqual(values[-1], "")

	def test_genre_is_independent(self):
		genre = ServiceInfo("DABGenre")
		genre.source = self.converter.source
		self.info.code, self.info.table = 11, 1
		self.assertEqual(self.converter.text, "Rock Music")
		self.assertEqual(genre.text, "DL Plus genre")

	def test_unavailable_reserved_and_non_dab(self):
		for value in (-1, 0, 30, 31, 32, None, "Unknown"):
			self.assertEqual(metadata.programmeTypeName(value, 1), "")
		self.assertEqual(metadata.programmeTypeName(24, 2), "")
		self.assertEqual(metadata.programmeTypeName(1, 255), "")
		self.assertEqual(metadata.programmeTypeName(1, 1), "News")
		self.info.code, self.info.table, self.info.reference = 1, 1, "1:0:0"
		self.assertEqual(self.converter.text, "")

	def test_tables_and_runtime_translation(self):
		self.assertEqual(metadata.programmeTypeName(2, 1), "Current Affairs")
		self.assertEqual(metadata.programmeTypeName(2, 2), "Information")
		try:
			builtins._ = lambda text: "translated:" + text
			self.assertEqual(metadata.programmeTypeName(1, 1), "translated:News")
		finally:
			builtins._ = lambda text: text


if __name__ == "__main__":
	unittest.main()
