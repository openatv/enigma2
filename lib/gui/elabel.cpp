/*

Scroll Text Feature of eLabel
Font Scale Feature of eLabel

Copyright (c) 2025-2026 jbleyel

This code may be used commercially. Attribution must be given to the original author.
Licensed under GPLv2.
*/


#include <lib/base/eerror.h>
#include <lib/gdi/font.h>
#include <lib/gui/elabel.h>
#include <lib/gui/ewindowstyleskinned.h>

eLabel::eLabel(eWidget* parent, int markedPos) : eWidget(parent), m_textPixmap(nullptr) {
	m_pos = markedPos;
	ePtr<eWindowStyle> style;
	getStyle(style);

	style->getFont(eWindowStyle::fontStatic, m_font);

	// default to topleft alignment
	m_valign = alignTop;
	m_halign = alignBidi;
}

eLabel::~eLabel()
{
	clearScrollPara();
}

static void realignScrollPara(eTextPara *para, int flags)
{
	if (flags & gPainter::RT_HALIGN_LEFT)
		para->realign(eTextPara::dirLeft);
	else if (flags & gPainter::RT_HALIGN_RIGHT)
		para->realign(eTextPara::dirRight);
	else if (flags & gPainter::RT_HALIGN_CENTER)
		para->realign((flags & gPainter::RT_WRAP) ? eTextPara::dirCenter : eTextPara::dirCenterIfFits);
	else if (flags & gPainter::RT_HALIGN_BLOCK)
		para->realign(eTextPara::dirBlock);
	else
		para->realign(eTextPara::dirBidi);
}

static ePoint scrollParaOffset(eTextPara *para, const eRect &area, int flags)
{
	ePoint offset;
	if (flags & gPainter::RT_VALIGN_CENTER)
	{
		eRect bbox = para->getBoundBox();
		int vcentered_top = area.top() + ((area.height() - bbox.height()) / 2);
		int correction = vcentered_top - bbox.top();
		if ((correction > 0) || (para->getLineCount() == 1))
			offset += ePoint(0, correction);
	}
	else if (flags & gPainter::RT_VALIGN_BOTTOM)
	{
		eRect bbox = para->getBoundBox();
		offset += ePoint(0, area.height() - bbox.height() - 2);
	}
	return offset;
}

static gFont *safeLabelFont(gFont *font, ePtr<gFont> &fallback)
{
	if (font)
		return font;
	eWarning("[eLabel] missing font, using Regular;20 fallback!");
	fallback = new gFont("Regular", 20);
	return fallback;
}

int eLabel::event(int event, void* data, void* data2) {
	switch (event) {
		case evtPaint: {
			// get style and allow base class to paint background etc.
			gPainter& painter = *(gPainter*)data2;

			const gDC *dc = painter.getDC();
			const bool useScrollPixmap = useCachedScrollPixmap(dc);

			if (m_scroll_text && m_scroll_config.cached && !useScrollPixmap && m_textPixmap) {
				m_textPixmap = nullptr;
				m_paint_pixmap = false;
			} else if (m_scroll_text && m_scroll_config.cached && useScrollPixmap && !m_textPixmap) {
				createScrollPixmap();
			}

			if (m_scroll_text && m_textPixmap && m_paint_pixmap && m_scroll_config.cached && useScrollPixmap) {
				// ensure timer is started with initial delay if not active
				if (!scrollTimer->isActive()) {
					scrollTimer->start(m_scroll_config.startDelay);
				}

				int srcX = 0;
				int srcY = 0;

				// determine source offset based on scroll direction
				if (m_scroll_config.direction == eScrollConfig::scrollLeft || m_scroll_config.direction == eScrollConfig::scrollRight)
					srcX = m_scroll_pos;
				else if (m_scroll_config.direction == eScrollConfig::scrollTop || m_scroll_config.direction == eScrollConfig::scrollBottom)
					srcY = m_scroll_pos;

				// perform blit of the text pixmap
				int visibleW = size().width() - m_padding.x() - m_padding.width();
				int visibleH = size().height() - m_padding.y() - m_padding.height();
				eSize s = eSize(visibleW, visibleH);
				eRect rec = eRect(ePoint(m_padding.x(), m_padding.y()), s);
				painter.blit(m_textPixmap, eRect(ePoint(-srcX + m_padding.x(), -srcY + m_padding.y()), s), rec, 0);

				m_paint_pixmap = false;
				// skip the normal renderText logic for scrolling
				return 0;
			}

			eWidget::event(event, data, data2);

			ePtr<eWindowStyle> style;
			getStyle(style);

			// set font & style
			painter.setFont(m_font);
			style->setStyle(painter, eWindowStyle::styleLabel);

			// choose foreground color (shadow has priority in existing code)
			if (m_have_shadow_color)
				painter.setForegroundColor(m_shadow_color);
			else if (m_have_foreground_color)
				painter.setForegroundColor(m_foreground_color);

			// build render flags
			int flags = buildFlags();

			if (isGradientSet() || m_blend)
				flags |= gPainter::RT_BLEND;

			int posX = m_padding.x();
			int posY = m_padding.y();

			// visible area (account for left/top + right/bottom padding)
			int visibleW = size().width() - m_padding.x() - m_padding.width();
			int visibleH = size().height() - m_padding.y() - m_padding.height();
			if (visibleW < 0)
				visibleW = 0;
			if (visibleH < 0)
				visibleH = 0;

			int rectW, rectH;

			/* For horizontal scroll we need full text width, height = visibleH.
			   For vertical scroll we need full text height, width = visibleW.
			   For non-scrolling modes we keep the visible area. */
			if (m_scroll_text && (m_scroll_config.direction == eScrollConfig::scrollLeft || m_scroll_config.direction == eScrollConfig::scrollRight)) {
				rectW = m_text_size.width(); // full text width (no-wrap computed earlier)
				rectH = visibleH;
			} else if (m_scroll_text && (m_scroll_config.direction == eScrollConfig::scrollTop || m_scroll_config.direction == eScrollConfig::scrollBottom)) {
				rectW = visibleW;
				rectH = m_text_size.height(); // full text height (wrapped)
			} else {
				// no running text: render within visible
				rectW = visibleW;
				rectH = visibleH;
			}

			auto position = eRect(posX, posY, rectW, rectH);
			auto basePosition = position;

			// apply scrolling offset (only if scrolling is active)
			if (m_scroll_config.direction && m_scroll_text) {
				// ensure timer is started with initial delay if not active
				if (!scrollTimer->isActive()) {
					scrollTimer->start(m_scroll_config.startDelay);
				}
				/* move the whole text-block - the sign follows existing convention:
				   position.x() - m_scroll_pos / position.y() - m_scroll_pos */
				if (m_scroll_config.direction == eScrollConfig::scrollLeft || m_scroll_config.direction == eScrollConfig::scrollRight)
					position.setX(position.x() - m_scroll_pos);
				else if (m_scroll_config.direction == eScrollConfig::scrollTop || m_scroll_config.direction == eScrollConfig::scrollBottom)
					position.setY(position.y() - m_scroll_pos);
			}


			// if we don't have shadow, m_shadow_offset will be 0,0
			// draw border/outline first
			auto shadowposition = eRect(position.x() - m_shadow_offset.x(), position.y() - m_shadow_offset.y(), position.width() - m_shadow_offset.x(), position.height() - m_shadow_offset.y());

			// If scrolling text is active
			// clip to the visible padded area. Otherwise do normal rendering.
			if (m_scroll_text) {
				eRect clipRect(ePoint(m_padding.x(), m_padding.y()), eSize(visibleW, visibleH));
				painter.resetClip(clipRect);
			}

			ePoint paraOffset;
			if (canUseScrollPara(dc, flags) && ensureScrollPara(basePosition, flags, paraOffset)) {
				ePoint scrollOffset(position.x() - basePosition.x(), position.y() - basePosition.y());
				painter.renderPara(m_scrollPara, paraOffset + scrollOffset);

				if (m_scroll_config.mode == eScrollConfig::scrollModeRoll) {
					ePoint rollOffset = scrollOffset;
					if (m_scroll_config.direction == eScrollConfig::scrollLeft || m_scroll_config.direction == eScrollConfig::scrollRight)
						rollOffset += ePoint(m_text_size.width() - visibleW, 0);
					else
						rollOffset += ePoint(0, m_text_size.height() - visibleH);
					painter.renderPara(m_scrollPara, paraOffset + rollOffset);
				}
			} else {
				painter.renderText(shadowposition, m_text, flags, m_text_border_color, m_text_border_width, m_pos, &m_text_offset, m_tab_width);

				// draw main text (foreground or shadowed)
				if (m_have_shadow_color) {
					if (!m_have_foreground_color)
						style->setStyle(painter, eWindowStyle::styleLabel);
					else
						painter.setForegroundColor(m_foreground_color);

					painter.setBackgroundColor(m_shadow_color);
					painter.renderText(position, m_text, flags, gRGB(), 0, m_pos, &m_text_shaddowoffset, m_tab_width);
				}

				if (m_scroll_text && m_scroll_config.mode == eScrollConfig::scrollModeRoll) {
					eRect rollPosition = position;
					if (m_scroll_config.direction == eScrollConfig::scrollLeft || m_scroll_config.direction == eScrollConfig::scrollRight)
						rollPosition.setX(position.x() + m_text_size.width() - visibleW);
					else
						rollPosition.setY(position.y() + m_text_size.height() - visibleH);

					auto rollShadowPosition = eRect(rollPosition.x() - m_shadow_offset.x(), rollPosition.y() - m_shadow_offset.y(), rollPosition.width() - m_shadow_offset.x(), rollPosition.height() - m_shadow_offset.y());

					if (m_have_shadow_color)
						painter.setForegroundColor(m_shadow_color);
					else if (m_have_foreground_color)
						painter.setForegroundColor(m_foreground_color);

					painter.renderText(rollShadowPosition, m_text, flags, m_text_border_color, m_text_border_width, m_pos, &m_text_offset, m_tab_width);

					if (m_have_shadow_color) {
						if (!m_have_foreground_color)
							style->setStyle(painter, eWindowStyle::styleLabel);
						else
							painter.setForegroundColor(m_foreground_color);

						painter.setBackgroundColor(m_shadow_color);
						painter.renderText(rollPosition, m_text, flags, gRGB(), 0, m_pos, &m_text_shaddowoffset, m_tab_width);
					}
				}
			}

			return 0;
		}
		case evtChangedFont:
		case evtChangedText:
		case evtChangedAlignment:
		case evtChangedMarkedPos:
			clearScrollPara();
			invalidate();
			return 0;
		case evtParentVisibilityChanged:
			if (!isVisible()) {
				stopScroll();
			}
			return 0;
		case evtChangedSize:
			updateTextSize();
			[[fallthrough]];
		default:
			return eWidget::event(event, data, data2);
	}
}

void eLabel::updateTextSize() {
	if (m_scroll_config.direction == eScrollConfig::scrollNone) {
		if (m_fontScaleType) {
			ePtr<gFont> fallbackFont;
			gFont *font = safeLabelFont(m_font, fallbackFont);
			int visibleW = std::max(1, size().width() - m_padding.x() - m_padding.width());
			int visibleH = std::max(1, size().height() - m_padding.y() - m_padding.height());
			int originalFontSize = m_originalFontSize > 0 ? m_originalFontSize : font->pointSize;
			eSize s = eSize(visibleW, visibleH);
			font->pointSize = originalFontSize;
			font->pointWidth = 0;
			eSize text_size = calculateTextSize(font, m_text, s, true); // nowrap at original size
			// A negative m_fontScaleSize is relative to the original font size (i.e. the minimum floor is m_originalFontSize + m_fontScaleSize)
			int scaleFloor = m_fontScaleSize < 0 ? originalFontSize + m_fontScaleSize : m_fontScaleSize;

			if (m_fontScaleType == 1) {
				int newFontSize = originalFontSize;
				if (text_size.width() > visibleW || text_size.height() > visibleH) {
					int scaleW = text_size.width() > 0 ? originalFontSize * visibleW / text_size.width() : originalFontSize;
					int scaleH = text_size.height() > 0 ? originalFontSize * visibleH / text_size.height() : originalFontSize;
					newFontSize = std::max(std::min(scaleW, scaleH), scaleFloor);
				}
				if (font->pointSize != newFontSize)
					font->pointSize = newFontSize;
			} else if (m_fontScaleType == 2) {
				int newFontWidth = 0;
				if (text_size.width() > visibleW && text_size.height() <= visibleH) {
					int scaleW = originalFontSize * visibleW / text_size.width();
					newFontWidth = std::max(scaleW, scaleFloor);
				}
				if (font->pointWidth != newFontWidth)
					font->pointWidth = newFontWidth;
			}
		}
		return;
	}

	stopScroll();
	ePtr<gFont> fallbackFont;
	gFont *font = safeLabelFont(m_font, fallbackFont);

	int visibleW = std::max(1, size().width() - m_padding.x() - m_padding.width());
	int visibleH = std::max(1, size().height() - m_padding.y() - m_padding.height());
	eSize s = eSize(visibleW, visibleH);
	if (m_scroll_config.direction == eScrollConfig::scrollLeft || m_scroll_config.direction == eScrollConfig::scrollRight) {
		m_text_size = calculateTextSize(font, m_text, s, true); // nowrap
		if (m_text_size.width() > s.width()) {
			m_text_size.setWidth(m_text_size.width() + font->pointSize / 10); // avoid issues with rounding
			m_scroll_text = true;
			if (m_scroll_config.mode == eScrollConfig::scrollModeRoll)
				m_text_size.setWidth(m_text_size.width() + s.width() * 1.5);
		}
	} else if (m_scroll_config.direction == eScrollConfig::scrollTop || m_scroll_config.direction == eScrollConfig::scrollBottom) {
		m_text_size = calculateTextSize(font, m_text, s, false); // allow wrap
		if (m_text_size.height() > s.height()) {
			m_text_size.setHeight(m_text_size.height() + font->pointSize / 10); // avoid issues with rounding
			if (m_scroll_config.mode == eScrollConfig::scrollModeRoll)
				m_text_size.setHeight(m_text_size.height() + s.height() * 1.5);
			m_scroll_text = true;
		}
	}
	if (m_scroll_text) {
		if (m_scroll_config.direction == eScrollConfig::scrollRight)
			m_scroll_pos = std::max(0, m_text_size.width() - visibleW);
		else if (m_scroll_config.direction == eScrollConfig::scrollBottom)
			m_scroll_pos = std::max(0, m_text_size.height() - visibleH);

		if (m_scroll_config.cached) {
			// limit 1MB pixmap size
			if ((m_text_size.width() * m_text_size.height()) > 1000000) {
				m_scroll_config.cached = false;
				if (m_scroll_config.mode == eScrollConfig::scrollModeRoll)
					m_scroll_config.mode = eScrollConfig::scrollModeNormal;
			} else {
				m_textPixmap = nullptr;
				m_paint_pixmap = false;
			}
		}
	}
}

bool eLabel::useCachedScrollPixmap(const gDC *dc) const
{
	return m_scroll_config.cached && !(dc && dc->isHardwareAccelerated());
}

bool eLabel::canUseScrollPara(const gDC *dc, int flags) const
{
	return dc && dc->isHardwareAccelerated() && m_scroll_text && m_text_border_width == 0 && m_pos < 0 && !m_have_shadow_color && m_shadow_offset == ePoint() && !(flags & (gPainter::RT_UNDERLINE | gPainter::RT_ELLIPSIS));
}

bool eLabel::ensureScrollPara(const eRect &area, int flags, ePoint &offset)
{
	offset = ePoint();
	if (m_scrollPara && m_scrollParaArea == area && m_scrollParaFlags == flags && m_scrollParaText == m_text) {
		offset = m_scrollParaOffset;
		return true;
	}

	clearScrollPara();

	eTextPara *para = new eTextPara(area);
	para->AddRef();
	para->setFont(m_font, m_tab_width);
	if (para->renderString(m_text.empty() ? nullptr : m_text.c_str(), (flags & gPainter::RT_WRAP) ? RS_WRAP : 0, 0, -1) < 0) {
		para->Release();
		return false;
	}

	realignScrollPara(para, flags);
	para->setBlend(flags & gPainter::RT_BLEND);

	m_scrollPara = para;
	m_scrollParaArea = area;
	m_scrollParaFlags = flags;
	m_scrollParaText = m_text;
	m_scrollParaOffset = scrollParaOffset(para, area, flags);
	offset = m_scrollParaOffset;
	return true;
}

void eLabel::clearScrollPara()
{
	if (m_scrollPara) {
		m_scrollPara->Release();
		m_scrollPara = nullptr;
	}
	m_scrollParaText.clear();
	m_scrollParaFlags = 0;
	m_scrollParaOffset = ePoint();
	m_scrollParaArea = eRect();
}

void eLabel::createScrollPixmap() {
	if (!m_scroll_text)
		return;

	int visibleW = std::max(1, size().width() - m_padding.x() - m_padding.width());
	int visibleH = std::max(1, size().height() - m_padding.y() - m_padding.height());

	int w = std::max(m_text_size.width(), size().width());
	int h = std::max(m_text_size.height(), size().height());

	eSize s = eSize(w, h);

	m_textPixmap = new gPixmap(s, 32, gPixmap::accelNever);

	// build flags as in paint
	int flags = buildFlags();

	ePtr<gDC> dc = new gDC(m_textPixmap);
	gPainter p(dc);

	ePtr<eWindowStyle> style;
	getStyle(style);

	style->setStyle(p, eWindowStyle::styleLabel);
	p.setFont(m_font);
	p.resetClip(eRect(ePoint(0, 0), s));

	if (m_have_background_color)
		p.setBackgroundColor(m_background_color);

	p.clear();

	if (m_have_shadow_color)
		p.setForegroundColor(m_shadow_color);
	else if (m_have_foreground_color)
		p.setForegroundColor(m_foreground_color);

	int posX = 0;
	int posY = 0;
	w = s.width();
	h = s.height();

	auto position = eRect(posX, posY, w, h);

	auto shadowposition = eRect(position.x() - m_shadow_offset.x(), position.y() - m_shadow_offset.y(), position.width() - m_shadow_offset.x(), position.height() - m_shadow_offset.y());

	p.renderText(shadowposition, m_text, flags, m_text_border_color, m_text_border_width, m_pos, &m_text_offset, m_tab_width);

	if (m_have_shadow_color) {
		if (!m_have_foreground_color)
			style->setStyle(p, eWindowStyle::styleLabel);
		else
			p.setForegroundColor(m_foreground_color);

		p.setBackgroundColor(m_shadow_color);
		p.renderText(position, m_text, flags, gRGB(), 0, m_pos, &m_text_shaddowoffset, m_tab_width);
	}

	if (m_scroll_config.mode == eScrollConfig::scrollModeRoll) {
		if (m_scroll_config.direction == eScrollConfig::scrollLeft || m_scroll_config.direction == eScrollConfig::scrollRight)
			posX = s.width() - visibleW;
		else
			posY = s.height() - visibleH;

		w = s.width();
		h = s.height();

		auto position = eRect(posX, posY, w, h);

		auto shadowposition = eRect(position.x() - m_shadow_offset.x(), position.y() - m_shadow_offset.y(), position.width() - m_shadow_offset.x(), position.height() - m_shadow_offset.y());

		p.renderText(shadowposition, m_text, flags, m_text_border_color, m_text_border_width, m_pos, &m_text_offset, m_tab_width);

		if (m_have_shadow_color) {
			if (!m_have_foreground_color)
				style->setStyle(p, eWindowStyle::styleLabel);
			else
				p.setForegroundColor(m_foreground_color);

			p.setBackgroundColor(m_shadow_color);
			p.renderText(position, m_text, flags, gRGB(), 0, m_pos, &m_text_shaddowoffset, m_tab_width);
		}
	}

	m_paint_pixmap = false;
	invalidate();
}

void eLabel::setText(const std::string& string) {
	if (m_text == string)
		return;
	m_text = string;
	stopScroll();
	updateTextSize();
	event(evtChangedText);
}

void eLabel::setMarkedPos(int markedPos) {
	m_pos = markedPos;
	event(evtChangedMarkedPos);
}

void eLabel::setFont(gFont* font) {
	if (!font) {
		eWarning("[eLabel] setFont called without a font!");
		return;
	}
	m_font = font;
	m_originalFontSize = font->pointSize;
	event(evtChangedFont);
}

void eLabel::setVAlign(int align) {
	m_valign = align;
	event(evtChangedAlignment);
}

void eLabel::setHAlign(int align) {
	m_halign = align;
	event(evtChangedAlignment);
}

void eLabel::setForegroundColor(const gRGB& col) {
	if ((!m_have_foreground_color) || (m_foreground_color != col)) {
		m_foreground_color = col;
		m_have_foreground_color = 1;
		invalidate();
	}
}

gRGB eLabel::getForegroundColor(int styleID) {
	if (m_have_foreground_color)
		return m_foreground_color;

	ePtr<eWindowStyleManager> mgr;
	eWindowStyleManager::getInstance(mgr);

	if (mgr) {
		ePtr<eWindowStyle> style;
		mgr->getStyle(styleID, style);
		if (style) {
			return style->getColor(eWindowStyleSkinned::colForeground);
		}
	}
	return gRGB(0xFFFFFF);
}

void eLabel::setShadowColor(const gRGB& col) {
	if ((!m_have_shadow_color) || (m_shadow_color != col)) {
		m_shadow_color = col;
		m_have_shadow_color = 1;
		invalidate();
	}
}

void eLabel::setTextBorderColor(const gRGB& col) {
	if (m_text_border_color != col) {
		m_text_border_color = col;
		invalidate();
	}
}

void eLabel::setWrap(int wrap) {
	if (m_wrap != wrap) {
		m_wrap = wrap;
		invalidate();
	}
}

void eLabel::setUnderline(bool underline) {
	if (m_underline != underline) {
		m_underline = underline;
		invalidate();
	}
}

void eLabel::setAlphatest(int alphatest) {
	bool blend = (alphatest > 0); // blend if BT_ALPHATEST or BT_ALPHABLEND
	if (m_blend != blend) {
		m_blend = blend;
		invalidate();
	}
}

void eLabel::clearForegroundColor() {
	if (m_have_foreground_color) {
		m_have_foreground_color = 0;
		invalidate();
	}
}

void eLabel::setTabWidth(int width) {
	if (width == -1) {
		ePtr<gFont> fallbackFont;
		gFont *font = safeLabelFont(m_font, fallbackFont);
		eTextPara para(eRect(0, 0, 1000, 1000));
		para.setFont(font);
		para.renderString("W", 0);
		m_tab_width = para.getBoundBox().size().width() * 8;
	} else {
		m_tab_width = width;
	}
}

eSize eLabel::calculateSize() {
	return calculateTextSize(m_font, m_text, size(), m_wrap == 0);
}

eSize eLabel::calculateTextSize(gFont* font, const std::string& string, eSize targetSize, bool nowrap) {
	// Calculate text size for a piece of text without creating an eLabel instance
	// this avoids the side effect of "invalidate" being called on the parent container
	// during the setup of the font and text on the eLabel
	ePtr<gFont> fallbackFont;
	font = safeLabelFont(font, fallbackFont);
	eTextPara para(eRect(0, 0, targetSize.width(), targetSize.height()));
	para.setFont(font);
	para.renderString(string.empty() ? 0 : string.c_str(), nowrap ? 0 : RS_WRAP);
	return para.getBoundBox().size();
}

void eLabel::setFontScale(int scaleType, int size) {
	m_fontScaleType = scaleType;
	m_fontScaleSize = size;
}

void eLabel::setScrollText(int direction, long delay, long startDelay, long endDelay, int repeat, int stepSize, int mode) {
	if (m_scroll_config.direction == direction || direction == eScrollConfig::scrollNone)
		return;

	m_scroll_config.direction = direction;
	m_scroll_config.repeat = repeat;
	m_scroll_config.startDelay = std::min(startDelay, 10000L);
	m_scroll_config.endDelay = std::min(endDelay, 10000L);
	m_scroll_config.delay = std::max(delay, (long)50);
	m_scroll_config.stepSize = std::max(stepSize, 1);
	m_scroll_config.mode = mode;
	m_scroll_config.cached = (mode == eScrollConfig::scrollModeBounceCached || mode == eScrollConfig::scrollModeCached || mode == eScrollConfig::scrollModeRoll);
	// ensure timer exists before stopping/clearing scroll state (stopScroll assumes scrollTimer)
	if (!scrollTimer) {
		scrollTimer = eTimer::create(eApp);
		CONNECT(scrollTimer->timeout, eLabel::updateScrollPosition);
	}
	stopScroll();
}

void eLabel::stopScroll() {
	if (scrollTimer)
		scrollTimer->stop();
	clearScrollPara();
	m_end_delay_active = false;
	m_scroll_text = false;
	m_scroll_pos = 0;
	m_repeat_count = 0;
	m_scroll_started = false;
	m_scroll_swap = false;
}

void eLabel::updateScrollPosition() {
	if (!m_scroll_text)
		return;

	// calculate visible area
	int visibleW = std::max(1, size().width() - m_padding.x() - m_padding.width());
	int visibleH = std::max(1, size().height() - m_padding.y() - m_padding.height());

	// compute max_scroll depending on direction
	int max_scroll = 0;
	if (m_scroll_config.direction == eScrollConfig::scrollLeft || m_scroll_config.direction == eScrollConfig::scrollRight)
		max_scroll = std::max(0, m_text_size.width() - visibleW);
	else if (m_scroll_config.direction == eScrollConfig::scrollTop || m_scroll_config.direction == eScrollConfig::scrollBottom)
		max_scroll = std::max(0, m_text_size.height() - visibleH);

	// determine step sign
	int step = m_scroll_config.stepSize;
	bool reverse = (m_scroll_config.direction == eScrollConfig::scrollRight || m_scroll_config.direction == eScrollConfig::scrollBottom);

	// in bounce mode, swap direction when m_scroll_swap is active
	if ((m_scroll_config.mode == eScrollConfig::scrollModeBounce || m_scroll_config.mode == eScrollConfig::scrollModeBounceCached) && m_scroll_swap)
		reverse = !reverse;

	if (reverse)
		step = -step;

	// apply step
	m_scroll_pos += step;

	// clamp to [0 .. max_scroll]
	if (m_scroll_pos < 0)
		m_scroll_pos = 0;
	if (m_scroll_pos > max_scroll)
		m_scroll_pos = max_scroll;

	// check if end reached
	if (m_scroll_pos == 0 || m_scroll_pos == max_scroll) {
		if (m_scroll_config.mode == eScrollConfig::scrollModeBounce || m_scroll_config.mode == eScrollConfig::scrollModeBounceCached) {
			// toggle bounce direction
			m_scroll_swap = !m_scroll_swap;

			// choose delay depending on which end we reached: use endDelay at max end,
			// use startDelay when we returned to the beginning (0)
			long bounceDelay = (m_scroll_pos == max_scroll) ? m_scroll_config.endDelay : m_scroll_config.startDelay;
			if (!m_end_delay_active && bounceDelay > 0) {
				// don't toggle m_scroll_swap immediately — toggle AFTER the delay
				m_end_delay_active = true;
				m_scroll_started = false;
				scrollTimer->stop();
				scrollTimer->start(bounceDelay);
				return;
			}
		} else {
			// classic repeat/stop behavior
			if (!m_end_delay_active && m_scroll_config.endDelay > 0) {
				m_end_delay_active = true;
				m_scroll_started = false;
				scrollTimer->stop();
				scrollTimer->start(m_scroll_config.endDelay);
				if (m_scroll_config.repeat != -1)
					m_repeat_count++;
				return;
			}

			if (m_scroll_config.repeat == 0 || (m_scroll_config.repeat != -1 && m_repeat_count >= m_scroll_config.repeat)) {
				// Run once → stop scrolling
				stopScroll();
				invalidate();
				return;
			} else {
				// Loop → reset position and wait for start delay
				if (m_scroll_config.direction == eScrollConfig::scrollLeft || m_scroll_config.direction == eScrollConfig::scrollTop)
					m_scroll_pos = 0;
				else
					m_scroll_pos = max_scroll;

				m_scroll_started = false;
				scrollTimer->stop();
				scrollTimer->start(m_scroll_config.startDelay);
				invalidate();
				return;
			}
		}
	}

	// first tick after start → set timer interval
	if (!m_scroll_started) {
		m_scroll_started = true;
		m_end_delay_active = false;
		scrollTimer->changeInterval(m_scroll_config.delay);
	}

	// request repaint
	if (m_scroll_config.cached && m_textPixmap)
		m_paint_pixmap = true;

	invalidate();
}
