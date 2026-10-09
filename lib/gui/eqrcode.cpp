#include <algorithm>
#include <array>
#include <lib/base/eerror.h>
#include <lib/gui/eqrcode.h>

eQRCode::eQRCode(eWidget* parent) : eWidget(parent) {}

void eQRCode::setText(const std::string& text) {
	if (m_text == text)
		return;
	m_text = text;
	encode();
}

void eQRCode::setErrorCorrection(int level) {
	if (level < ecLow || level > ecHigh || m_ecc == level)
		return;
	m_ecc = level;
	encode();
}

void eQRCode::setQuietZone(int modules) {
	if (modules < 0 || m_quiet_zone == modules)
		return;
	m_quiet_zone = modules;
	invalidate();
}

void eQRCode::setForegroundColor(const gRGB& color) {
	m_foreground_color = color;
	invalidate();
}

void eQRCode::setBackgroundColor(const gRGB& color) {
	eWidget::setBackgroundColor(color);
	invalidate();
}

void eQRCode::encode() {
	m_valid = false;
	if (!m_text.empty()) {
		std::array<uint8_t, qrcodegen_BUFFER_LEN_MAX> temp;
		m_valid = qrcodegen_encodeText(m_text.c_str(), temp.data(), m_qrcode.data(), (enum qrcodegen_Ecc)m_ecc, qrcodegen_VERSION_MIN, qrcodegen_VERSION_MAX, qrcodegen_Mask_AUTO, true);
		if (!m_valid)
			eWarning("[eQRCode] Text too long to encode (%zu bytes).", m_text.size());
	}
	invalidate();
}

int eQRCode::event(int event, void* data, void* data2) { // NOSONAR - signature of eWidget::event
	switch (event) {
		case evtPaint: {
			eWidget::event(event, data, data2);
			if (!m_valid)
				return 0;
			gPainter& painter = *(gPainter*)data2;
			const int width = size().width() - m_padding.x() - m_padding.width();
			const int height = size().height() - m_padding.y() - m_padding.height();
			const int count = qrcodegen_getSize(m_qrcode.data());
			const int total = count + 2 * m_quiet_zone;
			const int moduleSize = std::min(width, height) / total;
			if (moduleSize < 1) {
				eWarning("[eQRCode] Widget too small for %d modules.", total);
				return 0;
			}
			const int side = moduleSize * total;
			const int left = m_padding.x() + (width - side) / 2;
			const int top = m_padding.y() + (height - side) / 2;
			if (!m_have_background_color) {
				painter.setForegroundColor(gRGB(0xFF, 0xFF, 0xFF));
				painter.fill(eRect(left, top, side, side));
			}
			painter.setForegroundColor(m_foreground_color);
			const int x0 = left + m_quiet_zone * moduleSize;
			const int y0 = top + m_quiet_zone * moduleSize;
			for (int y = 0; y < count; y++) {
				int x = 0;
				while (x < count) {
					if (!qrcodegen_getModule(m_qrcode.data(), x, y)) {
						x++;
						continue;
					}
					int run = x;
					while (run < count && qrcodegen_getModule(m_qrcode.data(), run, y))
						run++;
					painter.fill(eRect(x0 + x * moduleSize, y0 + y * moduleSize, (run - x) * moduleSize, moduleSize));
					x = run;
				}
			}
			return 0;
		}
		case evtChangedSize:
			invalidate();
			[[fallthrough]];
		default:
			return eWidget::event(event, data, data2);
	}
}
