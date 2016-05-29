from Screen import Screen
from Components.ActionMap import ActionMap
from Components.Converter.ClientsStreaming import ClientsStreaming
import skin
import gettext
from Components.Sources.StaticText import StaticText

class StreamingClientsInfo(Screen):
		skin ="""<screen name="StreamingClientsInfo" position="center,center" size="600,500">
		<eLabel position="center,117" zPosition="-2" size="600,500" backgroundColor="#25062748" />
		<widget source="Title" render="Label" position="center,126" size="580,44" font="Regular; 35" valign="top" zPosition="0" backgroundColor="#25062748" halign="center" />
		<widget source="total" render="Label" position="center,174" size="580,50" zPosition="1" font="Regular; 22" halign="left" backgroundColor="#25062748" valign="center" />
		<widget source="liste" render="Label" position="center,234" size="580,370" zPosition="1" noWrap="1" font="Regular; 20" valign="top" />
	</screen>"""
		def __init__(self, session):
			Screen.__init__(self, session)
			self.setTitle(_("Streaming clients info"))
			if ClientsStreaming("NUMBER").getText() == "0":
				self["total"] = StaticText( _("No streaming Channel from this STB at this moment") )
				text = ""
			else:
				self["total"] = StaticText( _("Total Clients streaming: ") + ClientsStreaming("NUMBER").getText())
				text =  ClientsStreaming("EXTRA_INFO").getText()
			
			self["liste"] = StaticText(text)
			self["actions"] = ActionMap(["ColorActions", "SetupActions", "DirectionActions"],
			{
				"cancel": self.close,
				"ok": self.close
			})