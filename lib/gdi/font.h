#ifndef __FONT_H
#define __FONT_H

#ifndef SWIG

#include <ft2build.h>
#include FT_FREETYPE_H
#include FT_CACHE_H
#include FT_CACHE_IMAGE_H
#include FT_CACHE_SMALL_BITMAPS_H
#include FT_STROKER_H
typedef FTC_ImageCache FTC_Image_Cache;
typedef FTC_ImageTypeRec FTC_Image_Desc;
typedef FTC_SBitCache FTC_SBit_Cache;
#include <vector>

#include <lib/gdi/fb.h>
#include <lib/gdi/esize.h>
#include <lib/gdi/epoint.h>
#include <lib/gdi/erect.h>
#include <string>
#include <list>
#include <lib/base/object.h>

#include <set>

class FontRenderClass;
class Font;
class gDC;
class gFont;
struct gRGB;

#endif
class fontRenderClass
{
#ifndef SWIG
	friend class Font;
	friend class eTextPara;
	fbClass *fb;
	struct fontListEntry
	{
		std::string filename, face;
		int scale; // 100 is 1:1
		int renderflags;
		fontListEntry *next;
		~fontListEntry();
	} *font;

	FT_Library library;
	FTC_Manager cacheManager;				/* the cache manager							 */
	FTC_Image_Cache	imageCache;					/* the glyph image cache					 */
	FTC_SBit_Cache sbitsCache;				/* the glyph small bitmaps cache	 */
	FT_Stroker stroker;
	int strokerRadius;

	int getFaceProperties(const std::string &face, FTC_FaceID &id, int &renderflags);
#ifdef HAVE_FREETYPE2
	FT_Error getGlyphBitmap(FTC_Image_Desc *font, FT_UInt glyph_index, FTC_SBit *sbit);
	FT_Error getGlyphImage(FTC_Image_Desc *font, FT_UInt glyph_index, FT_Glyph *glyph, FT_Glyph *borderglyph, int bordersize);
#else
	FT_Error getGlyphBitmap(FTC_Image_Desc *font, FT_ULong glyph_index, FTC_SBit *sbit);
	FT_Error getGlyphImage(FTC_Image_Desc *font, FT_ULong glyph_index, FT_Glyph *glyph, FT_Glyph *borderglyph, int bordersize);
#endif
	static fontRenderClass *instance;
#else
	fontRenderClass();
	~fontRenderClass();
#endif
public:
	float getLineHeight(const gFont& font);
	static fontRenderClass *getInstance();
#ifndef SWIG
	std::string AddFont(const std::string &filename, const std::string &name, int scale, int renderflags = 0);
	FT_Error FTC_Face_Requester(FTC_FaceID	face_id, FT_Face* aface);
	int getFont(ePtr<Font> &font, const std::string &face, int size, int tabwidth=-1);
	fontRenderClass();
	~fontRenderClass();
#endif
};

#ifndef SWIG

#define RS_WRAP		1
#define RS_DOT		2
#define RS_DIRECT	4
#define RS_FADE		8

#define GS_ISSPACE  1
#define GS_ISFIRST  2
#define GS_USED			4
#define GS_INVERT   8
#define GS_SOFTHYPHEN 16
#define GS_HYPHEN   32
#define GS_COLORCHANGE 64
#define GS_LF 128
#define GS_CANBREAK (GS_ISSPACE|GS_SOFTHYPHEN|GS_HYPHEN)

struct pGlyph
{
	int x, y, w;
	unsigned long newcolor;
	ePtr<Font> font;
#ifdef HAVE_FREETYPE2
	FT_UInt glyph_index;
#else
	FT_ULong glyph_index;
#endif
	int flags;
	eRect bbox;
	FT_Glyph image, borderimage;
	pGlyph()
	{
		image = NULL;
		borderimage = NULL;
	}
};

typedef std::vector<pGlyph> glyphString;

class Font;
class eLCD;

class eTextPara: public iObject
{
	DECLARE_REF(eTextPara);
	ePtr<Font> current_font, replacement_font, fallback_font;
	FT_Face current_face, replacement_face, fallback_face;
	int use_kerning;
	int previous;
	static std::string replacement_facename;
	static std::string fallback_facename;
	static std::set<int> forced_replaces;

	eRect area;
	ePoint cursor;
	eSize maximum;
	int left;
	glyphString glyphs;
	std::list<int> lineOffsets;
	std::list<int> lineChars;
	int charCount;
	int lineCount;
	int totalheight;
	int bboxValid;
	eRect boundBox;
	bool doTopBottomReordering;

	int appendGlyph(Font *current_font, FT_Face current_face, FT_UInt glyphIndex, int flags, int rflags, int border, bool last,
			bool activate_newcolor, unsigned long newcolor);
	void newLine(int flags);
	void setFont(Font *font, Font *replacement_font, Font *fallback_font);
	void calc_bbox();
public:
	eTextPara(eRect area, ePoint start=ePoint(-1, -1))
		: current_font(0), replacement_font(0), current_face(0), replacement_face(0),
		fallback_font(0), fallback_face(0),
		area(area), cursor(start), maximum(0, 0), left(start.x()), charCount(0), totalheight(0),
		bboxValid(0), doTopBottomReordering(false)
	{
	}
	virtual ~eTextPara();

	static void setReplacementFont(std::string font) { replacement_facename=font; }
	static void forceReplacementGlyph(int unicode) { forced_replaces.insert(unicode); }

	static void setFallbackFont(std::string font) { fallback_facename=font; }

	void setFont(const gFont *font);
	int renderString(const char *string, int flags=0, int border=0);

	void clear();
	int getLineCount(void) const { return lineCount; }

	void blit(gDC &dc, const ePoint &offset, const gRGB &background, const gRGB &foreground, bool border = false);

	enum
	{
		dirLeft, dirRight, dirCenter, dirBlock, dirCenterIfFits, dirBidi
	};

	void realign(int dir);

	const eRect & getBoundBox()
	{
		if (!bboxValid)
			calc_bbox();

		return boundBox;
	}

	const int size() const
	{
		return glyphs.size();
	}

	const eRect& getGlyphBBox(int num) const
	{
		ASSERT(num >= 0);
		ASSERT(num < (int)glyphs.size());
		return glyphs[num].bbox;
	}

	void setGlyphFlag(int g, int f)
	{
		ASSERT(g >= 0);
		ASSERT(g < (int)glyphs.size());
		glyphs[g].flags |= f;
	}

	void clearGlyphFlag(int g, int f)
	{
		ASSERT(g >= 0);
		ASSERT(g < (int)glyphs.size());
		glyphs[g].flags |= f;
	}
};

class Font: public iObject
{
	DECLARE_REF(Font);
public:
	FTC_ScalerRec scaler;
	FTC_Image_Desc font;
	fontRenderClass *renderer;
#ifdef HAVE_FREETYPE2
	FT_Error getGlyphBitmap(FT_UInt glyph_index, FTC_SBit *sbit);
	FT_Error getGlyphImage(FT_UInt glyph_index, FT_Glyph *glyph, FT_Glyph *borderglyph, int bordersize);
#else
	FT_Error getGlyphBitmap(FT_ULong glyph_index, FTC_SBit *sbit);
	FT_Error getGlyphImage(FT_ULong glyph_index, FT_Glyph *glyph, FT_Glyph *borderglyph, int bordersize);
#endif
	FT_Face face;
	FT_Size size;

	int tabwidth;
	int height;
	Font(fontRenderClass *render, FTC_FaceID faceid, int isize, int tabwidth, int renderflags);
	virtual ~Font();
};

extern fontRenderClass *font;

#endif  // !SWIG

#endif
