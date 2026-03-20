/*
 * eCanvas – dual-path canvas (software fallback + GPU-native replay)
 *
 * See ecanvas.h for architecture overview.
 */

#include <cmath>
#include <lib/gdi/grc.h> /* gPainter, gDC */
#include <lib/gui/ecanvas.h>

eCanvas::eCanvas(eWidget* parent) : ePixmap(parent) {}

void eCanvas::setSize(eSize size) {
	m_canvas_size = size;
	/* Retain the software pixmap (accelNever) for the software-DC fallback.
	 * On GLES boxes this pixmap is never blitted; it exists only so that
	 * ePixmap::checkSize() doesn't force transparency unexpectedly. */
	setPixmap(new gPixmap(size, 32, gPixmap::accelNever));
}

void eCanvas::clear(gRGB color) {
	CanvasOp op;
	op.type = OP_CLEAR;
	op.color = color;
	m_ops.push_back(op);

	/* Also update the software pixmap so the software path stays coherent. */
	if (m_pixmap) {
		ePtr<gDC> d = new gDC(m_pixmap);
		gPainter p(d, eRect());
		p.resetClip(eRect(ePoint(0, 0), m_pixmap->size()));
		p.setBackgroundColor(color);
		p.clear();
	}
	invalidate();
}

void eCanvas::fillRect(eRect rect, gRGB color) {
	CanvasOp op;
	op.type = OP_FILL_RECT;
	op.rect = rect;
	op.color = color;
	m_ops.push_back(op);

	if (m_pixmap) {
		ePtr<gDC> dc = new gDC(m_pixmap);
		gPainter p(dc);
		p.resetClip(eRect(ePoint(0, 0), m_pixmap->size()));
		p.setForegroundColor(color);
		p.fill(rect);
	}
	invalidate(rect);
}

void eCanvas::drawLine(int x0, int y0, int x1, int y1, gRGB color) {
	CanvasOp op;
	op.type = OP_LINE;
	op.x0 = x0;
	op.y0 = y0;
	op.x1 = x1;
	op.y1 = y1;
	op.color = color;
	m_ops.push_back(op);

	if (m_pixmap) {
		ePtr<gDC> dc = new gDC(m_pixmap);
		gPainter p(dc);
		p.resetClip(eRect(ePoint(0, 0), m_pixmap->size()));
		p.setForegroundColor(color);
		p.line(ePoint(x0, y0), ePoint(x1, y1));
	}
	invalidate(eRect(x0, y0, x1, y1).normalize());
}

void eCanvas::writeText(eRect rect, gRGB fg, gRGB bg, gFont* font, const char* string, int flags) {
	CanvasOp op;
	op.type = OP_TEXT;
	op.rect = rect;
	op.fg = fg;
	op.bg = bg;
	op.font = font;
	op.text = string ? string : "";
	op.flags = flags;
	m_ops.push_back(op);

	if (m_pixmap) {
		ePtr<gDC> dc = new gDC(m_pixmap);
		gPainter p(dc);
		p.setFont(font);
		p.resetClip(eRect(ePoint(0, 0), m_pixmap->size()));
		p.setForegroundColor(fg);
		p.setBackgroundColor(bg);
		p.renderText(rect, string, flags);
	}
	invalidate(rect);
}

void eCanvas::drawRotatedLine(int ox, int oy, int x0, int y0, int x1, int y1, float angle, bool cw, gRGB color) {
	CanvasOp op;
	op.type = OP_ROTATED_LINE;
	op.ox = ox;
	op.oy = oy;
	op.x0 = x0;
	op.y0 = y0;
	op.x1 = x1;
	op.y1 = y1;
	op.angle = angle;
	op.cw = cw;
	op.color = color;
	m_ops.push_back(op);

	/* Apply the same rotation math to compute the final coords so we can
	 * keep the software pixmap pixel-accurate as well. */
	float a = angle * 0.017453292519943295769f;
	int c = cw ? 1 : -1;
	int nx0 = ox - (int)(-x0 * cosf(a) + y0 * sinf(a) * c);
	int ny0 = oy - (int)(-x0 * sinf(a) * c - y0 * cosf(a));
	int nx1 = ox - (int)(-x1 * cosf(a) + y1 * sinf(a) * c);
	int ny1 = oy - (int)(-x1 * sinf(a) * c - y1 * cosf(a));
	drawLine(nx0, ny0, nx1, ny1, color); /* drawLine() records its own op */
	/* But that added a duplicate OP_LINE – pop it and keep OP_ROTATED_LINE. */
	if (m_ops.size() >= 2 && m_ops.back().type == OP_LINE)
		m_ops.pop_back();
}

void eCanvas::replayOps(gPainter& painter) const {
	for (const CanvasOp& op : m_ops) {
		switch (op.type) {
			case OP_CLEAR:
				painter.setBackgroundColor(op.color);
				painter.clear();
				break;

			case OP_FILL_RECT:
				painter.setForegroundColor(op.color);
				painter.fill(op.rect);
				break;

			case OP_LINE:
				painter.setForegroundColor(op.color);
				painter.line(ePoint(op.x0, op.y0), ePoint(op.x1, op.y1));
				break;

			case OP_ROTATED_LINE: {
				float a = op.angle * 0.017453292519943295769f;
				int c = op.cw ? 1 : -1;
				int nx0 = op.ox - (int)(-op.x0 * cosf(a) + op.y0 * sinf(a) * c);
				int ny0 = op.oy - (int)(-op.x0 * sinf(a) * c - op.y0 * cosf(a));
				int nx1 = op.ox - (int)(-op.x1 * cosf(a) + op.y1 * sinf(a) * c);
				int ny1 = op.oy - (int)(-op.x1 * sinf(a) * c - op.y1 * cosf(a));
				painter.setForegroundColor(op.color);
				painter.line(ePoint(nx0, ny0), ePoint(nx1, ny1));
				break;
			}

			case OP_TEXT:
				painter.setFont(op.font);
				painter.setForegroundColor(op.fg);
				painter.setBackgroundColor(op.bg);
				painter.renderText(op.rect, op.text.c_str(), op.flags);
				break;
		}
	}
}

int eCanvas::event(int event, void* data, void* data2) {
	if (event == evtPaint) {
		gPainter& painter = *static_cast<gPainter*>(data2);

		/* Detect at paint time whether the active DC is hardware-accelerated. */
		const gDC* dc = painter.getDC();
		if (dc && dc->isHardwareAccelerated()) {
			/*
			 * GPU PATH: replay recorded commands directly through the hardware
			 * painter.  No pixmap blitting, no VRAM uploads, fully zero-copy.
			 */
			eWidget::event(event, data, data2); /* paint widget background */
			replayOps(painter);
			return 0;
		}

		/*
		 * SOFTWARE PATH: let ePixmap do its normal blit of m_pixmap to the
		 * screen.  This path is identical to the legacy eCanvas behaviour on
		 * any non-GLES platform.
		 */
		return ePixmap::event(event, data, data2);
	}

	return ePixmap::event(event, data, data2);
}
