#ifndef __lib_gui_eqrcode_h
#define __lib_gui_eqrcode_h

#include <array>

#include <lib/gui/ewidget.h>
#include <lib/gui/qrcodegen.h>

class eQRCode : public eWidget {
public:
	explicit eQRCode(eWidget* parent);

	enum { ecLow, ecMedium, ecQuartile, ecHigh };

	void setText(const std::string& text);
	std::string getText() const { return m_text; }
	void setErrorCorrection(int level);
	void setQuietZone(int modules);
	void setForegroundColor(const gRGB& color);
	void setBackgroundColor(const gRGB& color) override;
	bool isValid() const { return m_valid; }

protected:
	int event(int event, void* data = nullptr, void* data2 = nullptr) override;
	std::string getClassName() const override { return std::string("eQRCode"); }

private:
	void encode();

	std::string m_text;
	int m_ecc = ecMedium;
	int m_quiet_zone = 4;
	gRGB m_foreground_color = gRGB(0, 0, 0);
	bool m_valid = false;
#ifndef SWIG
	std::array<uint8_t, qrcodegen_BUFFER_LEN_MAX> m_qrcode;
#endif
};

#endif
