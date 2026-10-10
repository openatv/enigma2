from Components.ActionMap import HelpableActionMap
from Components.Label import Label
from Components.QRCode import QRCode
from Components.Sources.StaticText import StaticText
from Screens.Screen import Screen

MANUAL_URL = "https://book.opena.tv"


class UserManual(Screen):
	skin = """
	<screen name="UserManual" title="User Manual" position="center,center" size="980,570" resolution="1280,720">
		<widget name="qrcode" position="290,10" size="400,400" />
		<widget name="text" position="10,e-160" size="e-20,100" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" />
		<widget source="key_red" render="Label" position="10,e-50" size="180,40" backgroundColor="key_red" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
		<widget source="key_help" render="Label" position="e-100,e-50" size="90,40" backgroundColor="key_back" conditional="key_help" font="Regular;20" foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center">
			<convert type="ConditionalShowHide" />
		</widget>
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session, enableHelp=True)
		self.setTitle(_("User Manual"))
		self["qrcode"] = QRCode(MANUAL_URL)
		self["text"] = Label(f"{_('Scan the QR code to open the manual:')}\n{MANUAL_URL}")
		self["key_red"] = StaticText(_("Close"))
		closeText = _("Close the screen")
		self["actions"] = HelpableActionMap(self, ["OkCancelActions", "ColorActions"], {
			"ok": (self.close, closeText),
			"cancel": (self.close, closeText),
			"red": (self.close, closeText)
		}, prio=0, description=_("User Manual Actions"))
