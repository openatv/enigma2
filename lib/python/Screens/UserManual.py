from enigma import eCanvas, eRect, gRGB

from Components.ActionMap import ActionMap
from Components.GUIComponent import GUIComponent
from Components.Label import Label
from Screens.Screen import Screen

MANUAL_URL = "https://book.opena.tv"


class QRCanvas(GUIComponent):
	GUI_WIDGET = eCanvas


class UserManual(Screen):
	skin = """
	<screen name="UserManual" title="User Manual" position="center,center" size="500,470" resolution="1280,720">
		<widget name="qrcode" position="75,10" size="350,350" />
		<widget name="text" position="10,370" size="480,90" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" />
	</screen>"""

	def __init__(self, session):
		Screen.__init__(self, session)
		self.setTitle(_("User Manual"))
		self["qrcode"] = QRCanvas()
		self["text"] = Label(f"{_('Scan the QR code to open the manual:')}\n{MANUAL_URL}")
		self["actions"] = ActionMap(["OkCancelActions"], {
			"ok": self.close,
			"cancel": self.close
		}, prio=-1)
		self.onLayoutFinish.append(self.drawQRCode)

	def drawQRCode(self):
		try:
			from qrcode import QRCode  # Optional package, the URL is shown as text anyway.
		except ImportError:
			self["qrcode"].hide()
			return
		code = QRCode(border=4)
		code.add_data(MANUAL_URL)
		matrix = code.get_matrix()
		canvas = self["qrcode"].instance
		size = canvas.size()
		canvas.setSize(size)  # Allocates the canvas pixmap.
		scale = min(size.width(), size.height()) // len(matrix)
		offsetX = (size.width() - scale * len(matrix)) // 2
		offsetY = (size.height() - scale * len(matrix)) // 2
		canvas.fillRect(eRect(0, 0, size.width(), size.height()), gRGB(0x00FFFFFF))
		black = gRGB(0x00000000)
		for y, row in enumerate(matrix):
			for x, dark in enumerate(row):
				if dark:
					canvas.fillRect(eRect(offsetX + x * scale, offsetY + y * scale, scale, scale), black)
