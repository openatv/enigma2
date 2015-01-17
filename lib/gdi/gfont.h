#ifndef __lib_gdi_gfont_h
#define __lib_gdi_gfont_h

#include <lib/base/object.h>
#include <string>

/**
 * \brief A softreference to a font.
 *
 * The font is specified by a name and a size.
 * \c gFont is part of the \ref gdi.
 */
class gFont: public iObject
{
	DECLARE_REF(gFont);
public:

	std::string family;
	int pointSize;

	/**
	 * \brief Constructs a font with the given name and size.
	 * \param family The name of the font, for example "NimbusSansL-Regular Sans L Regular".
	 * \param pointSize the size of the font in PIXELS.
	 */
	gFont(const std::string &family, int pointSize):
		family(family), pointSize(pointSize)
	{
	}

	virtual ~gFont()
	{
	}

	gFont()
		:pointSize(0)
	{
	}
};

#endif
