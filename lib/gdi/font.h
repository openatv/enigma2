#ifndef __FONT_H
#define __FONT_H

#include <freetype/freetype.h>
#include <freetype/ftcache.h>
#include <freetype/cache/ftcglyph.h>
#include <freetype/cache/ftcimage.h>
#include <freetype/cache/ftcmanag.h>
#include <freetype/cache/ftcsbits.h>
#include <freetype/cache/ftlru.h>
#include <vector>

#include <lib/gdi/fb.h>
#include <lib/gdi/esize.h>
#include <lib/gdi/epoint.h>
#include <lib/gdi/erect.h>
#include <lib/base/estring.h>

class FontRenderClass;
class Font;
class gPixmapDC;
class gFont;
class gRGB;

class fontRenderClass
{ 
	friend class Font;
	friend class eTextPara;
	fbClass *fb;
	struct fontListEntry
	{
		eString filename, face;
		int scale; // 100 is 1:1
		fontListEntry *next;
		~fontListEntry();
	} *font;

	FT_Library library;
	FTC_Manager			cacheManager;				/* the cache manager							 */
	FTC_Image_Cache	imageCache;					/* the glyph image cache					 */
	FTC_SBit_Cache	 sbitsCache;				/* the glyph small bitmaps cache	 */

	FTC_FaceID getFaceID(const eString &face);
	FT_Error getGlyphBitmap(FTC_Image_Desc *font, FT_ULong glyph_index, FTC_SBit *sbit);
	static fontRenderClass *instance;
public:
	float getLineHeight(const gFont& font);
	eString AddFont(const eString &filename, const eString &name, int scale);
	static fontRenderClass *getInstance();
	FT_Error FTC_Face_Requester(FTC_FaceID	face_id,
															FT_Face*		aface);
	Font *getFont(const eString &face, int size, int tabwidth=-1);
	fontRenderClass();
	~fontRenderClass();
};

#define RS_WRAP		1
#define RS_DOT		2
#define RS_DIRECT	4
#define RS_FADE		8

#define GS_ISSPACE  1
#define GS_ISFIRST  2
#define GS_USED			4

struct pGlyph
{
	int x, y, w;
	Font *font;
	FT_ULong glyph_index;
	int flags;
	eRect bbox;
};

typedef std::vector<pGlyph> glyphString;

class Font;
class eLCD;

class eTextPara
{
	Font *current_font, *replacement_font;
	FT_Face current_face, replacement_face;
	int use_kerning;
	int previous;
	static eString replacement_facename;

	eRect area;
	ePoint cursor;
	eSize maximum;
	int left;
	glyphString glyphs;
	int refcnt;

	int appendGlyph(Font *current_font, FT_Face current_face, FT_UInt glyphIndex, int flags, int rflags);
	void newLine(int flags);
	void setFont(Font *font, Font *replacement_font);
	eRect boundBox;
	void calc_bbox();
	int bboxValid;
public:
	eTextPara(eRect area, ePoint start=ePoint(-1, -1))
		: current_font(0), replacement_font(0), current_face(0), replacement_face(0),
			area(area), cursor(start), maximum(0, 0), left(start.x()), refcnt(0), bboxValid(0)
	{
	}
	~eTextPara();
	
	static void setReplacementFont(eString font) { replacement_facename=font; }

	void destroy();
	eTextPara *grab();

	void setFont(const gFont &font);
	int renderString(const eString &string, int flags=0);

	void clear();

	void blit(gPixmapDC &dc, const ePoint &offset, const gRGB &background, const gRGB &foreground);

	enum
	{
		dirLeft, dirRight, dirCenter, dirBlock
	};

	void realign(int dir);

	const eRect & getBoundBox()
	{
		if (!bboxValid)
			calc_bbox();

		return boundBox;
	}

	const eRect& getGlyphBBox(int num) const
	{
		return glyphs[num].bbox;
	}
};

class Font
{
public:
	FTC_Image_Desc font;
	fontRenderClass *renderer;
	int ref;
	FT_Error getGlyphBitmap(FT_ULong glyph_index, FTC_SBit *sbit);
	FT_Face face;
	FT_Size size;
	
	int tabwidth;
	int height;
	Font(fontRenderClass *render, FTC_FaceID faceid, int isize, int tabwidth);
	~Font();
	
	void lock();
	void unlock();	// deletes if ref==0
};

extern fontRenderClass *font;

#endif
