from Components.ConditionalWidget import BlinkingWidget, BlinkingWidgetConditional
from Components.Pixmap import PixmapConditional


class BlinkingPixmap(BlinkingWidget):
	def __init__(self):
		BlinkingWidget.__init__(self)


class BlinkingPixmapConditional(BlinkingWidgetConditional, PixmapConditional):
	def __init__(self):
		BlinkingWidgetConditional.__init__(self)
		PixmapConditional.__init__(self)
