from Pixmap import *
from ConditionalWidget import *

class BlinkingPixmap(BlinkingWidget):
	def __init__(self):
		Widget.__init__(self)
		
class BlinkingPixmapConditional(BlinkingWidgetConditional, PixmapConditional):
	def __init__(self):
		BlinkingWidgetConditional.__init__(self)
		PixmapConditional.__init__(self)
