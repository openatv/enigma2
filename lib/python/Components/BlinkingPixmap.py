from Pixmap import PixmapConditional
from ConditionalWidget import BlinkingWidgetConditional, BlinkingWidget


class BlinkingPixmap(BlinkingWidget):
	def __init__(self):
		Widget.__init__(self)


class BlinkingPixmapConditional(BlinkingWidgetConditional, PixmapConditional):
	def __init__(self):
		BlinkingWidgetConditional.__init__(self)
		PixmapConditional.__init__(self)
