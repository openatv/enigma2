#include <lib/gdi/font.h>

#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include <pthread.h>
#include <sys/types.h>
#include <unistd.h>
#include <byteswap.h>

#ifndef BYTE_ORDER
#error "no BYTE_ORDER defined!"
#endif

// use this for init Freetype...
#include <ft2build.h>
#include FT_FREETYPE_H
#define FTC_Image_Cache_New(a,b)	FTC_ImageCache_New(a,b)
#define FTC_SBit_Cache_New(a,b)		FTC_SBitCache_New(a,b)
#define FTC_SBit_Cache_Lookup(a,b,c,d)	FTC_SBitCache_Lookup(a,b,c,d,NULL)

#include <lib/base/eerror.h>
#include <lib/gdi/lcd.h>
#include <lib/gdi/grc.h>
#include <lib/base/elock.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#include <lib/gdi/font_arabic.h>
#include <hb-ft.h>
#include <hb-ot.h>
#include <fribidi/fribidi.h>

#include <map>

fontRenderClass *fontRenderClass::instance;

static pthread_mutex_t ftlock=PTHREAD_ADAPTIVE_MUTEX_INITIALIZER_NP;

struct fntColorCacheKey
{
	gRGB start, end;
	fntColorCacheKey(const gRGB &start, const gRGB &end)
		: start(start), end(end)
	{
	}
	bool operator <(const fntColorCacheKey &c) const
	{
		if (start < c.start)
			return 1;
		else if (start == c.start)
			return end < c.end;
		return 0;
	}
};

std::map<fntColorCacheKey,gLookup> colorcache;

static gLookup &getColor(const gPalette &pal, const gRGB &start, const gRGB &end)
{
	fntColorCacheKey key(start, end);
	std::map<fntColorCacheKey,gLookup>::iterator i=colorcache.find(key);
	if (i != colorcache.end())
		return i->second;
	gLookup &n=colorcache.insert(std::pair<fntColorCacheKey,gLookup>(key,gLookup())).first->second;
//	eDebug("[Font] Creating new font color cache entry %02x%02x%02x%02x .. %02x%02x%02x%02x", start.a, start.r, start.g, start.b,
//		end.a, end.r, end.g, end.b);
	n.build(16, pal, start, end);
//	eDebugNoNewLineStart("[Font] ");
//	for (int i=0; i<16; i++)
//		eDebugNoNewLine("%02x|%02x%02x%02x%02x ", (int)n.lookup[i], pal.data[n.lookup[i]].a, pal.data[n.lookup[i]].r, pal.data[n.lookup[i]].g, pal.data[n.lookup[i]].b);
//	eDebugNoNewLine("\n");
	return n;
}

fontRenderClass *fontRenderClass::getInstance()
{
	return instance;
}

FT_Error myFTC_Face_Requester(	FTC_FaceID	face_id,
				FT_Library	library,
				FT_Pointer	request_data,
				FT_Face*	aface)
{
	return ((fontRenderClass*)request_data)->FTC_Face_Requester(face_id, aface);
}


FT_Error fontRenderClass::FTC_Face_Requester(FTC_FaceID	face_id, FT_Face* aface)
{
	fontListEntry *font=(fontListEntry *)face_id;
	if (!font)
		return -1;

//	eDebug("[Font] FTC_Face_Requester (%s)", font->face.c_str());

	int error;
	if ((error=FT_New_Face(library, font->filename.c_str(), 0, aface)))
	{
		eDebug("[Font] Failed: %s", strerror(error));
		return error;
	}
	FT_Select_Charmap(*aface, ft_encoding_unicode);
	return 0;
}

int fontRenderClass::getFaceProperties(const std::string &face, FTC_FaceID &id, int &renderflags)
{
	auto it = fontMap.find(face);
	if (it == fontMap.end())
		return -1;
	id          = (FTC_FaceID)it->second;
	renderflags = it->second->renderflags;
	return 0;
}

inline FT_Error fontRenderClass::getGlyphBitmap(FTC_Image_Desc *font, FT_UInt glyph_index, FTC_SBit *sbit)
{
	return FTC_SBit_Cache_Lookup(sbitsCache, font, glyph_index, sbit);
}

inline FT_Error fontRenderClass::getGlyphImage(FTC_Image_Desc *font, FT_UInt glyph_index, FT_Glyph *glyph, FT_Glyph *borderglyph, int bordersize)
{
	FT_Glyph image;
	FT_Error err = FTC_ImageCache_Lookup(imageCache, font, glyph_index, &image, NULL);
	if (err) return err;

	if (glyph)
	{
		err = FT_Glyph_Copy(image, glyph);
		if (err) return err;
	}

	if (borderglyph && bordersize)
	{
		err = FT_Glyph_Copy(image, borderglyph);
		if (err) return err;
		if (bordersize != strokerRadius)
		{
			strokerRadius = bordersize;
			FT_Stroker_Set(stroker, strokerRadius, FT_STROKER_LINECAP_ROUND, FT_STROKER_LINEJOIN_ROUND, 0);
		}
		err = FT_Glyph_Stroke(borderglyph, stroker, 1);
	}
	return err;
}

std::string fontRenderClass::AddFont(const std::string &filename, const std::string &name, int scale, int renderflags)
{
	eDebugNoNewLineStart("[Font] Adding font '%s'", filename.c_str());
	fflush(stdout);
	int error;
	FT_Face face;

	singleLock s(ftlock);
	if ((error=FT_New_Face(library, filename.c_str(), 0, &face)))
	{
		eWarning("[Font] Failed: %m");
		return std::string();
	}
	FT_Done_Face(face);

	auto it = fontMap.find(name);
	if (it != fontMap.end())
	{
		FTC_Manager_RemoveFaceID(cacheManager, (FTC_FaceID)it->second);
		delete it->second;
	}

	fontListEntry *n = new fontListEntry;
	n->filename = filename;
	n->face = name;
	n->scale = scale;
	n->renderflags = renderflags;

	fontMap[name] = n;
	fontFacesCacheValid = false;
	eDebugNoNewLine(" -> '%s'.\n", n->face.c_str());

	return n->face;
}

void fontRenderClass::ClearFonts()
{
	singleLock s(ftlock);
	for (auto &entry : fontMap)
	{
		FTC_Manager_RemoveFaceID(cacheManager, (FTC_FaceID)entry.second);
		delete entry.second;
	}
	fontMap.clear();
	fontFacesCacheValid = false;
	eTextPara::setReplacementFont("");
	eTextPara::setFallbackFont("");
}

void clearFonts()
{
	fontRenderClass::getInstance()->ClearFonts();
}

// Drops the retained FT_Face while the owning FreeType library is still alive.
fontRenderClass::fontListEntry::~fontListEntry()
{
	if (shapingFont)
		hb_font_destroy(shapingFont);
}

fontRenderClass::fontRenderClass()
{
	fb = fbClass::getInstance();
	instance=this;
	eDebug("[Font] Initializing lib.");
	if (FT_Init_FreeType(&library))
	{
		eDebug("[Font] Initializing failed!");
		return;
	}
	eDebug("[Font] Loading fonts.");
	fflush(stdout);

	int maxbytes=4*1024*1024;
	eDebug("[Font] Initializing font cache, using max. %dMB.", maxbytes/1024/1024);
	fflush(stdout);
	if (FTC_Manager_New(library, 8, 8, maxbytes, myFTC_Face_Requester, this, &cacheManager))
	{
		eDebug("[Font] Initializing font cache failed!");
		return;
	}
	if (!cacheManager)
	{
		eDebug("[Font] Initializing font cache manager error!");
		return;
	}
	if (FTC_SBit_Cache_New(cacheManager, &sbitsCache))
	{
		eDebug("[Font] Initializing font cache sbit failed!");
		return;
	}
	if (FTC_Image_Cache_New(cacheManager, &imageCache))
	{
		eDebug("[Font] Initializing font cache imagecache failed!");
	}
	if (FTC_CMapCache_New(cacheManager, &cmapCache))
	{
		eDebug("[Font] Initializing font cache cmap failed!");
	}
	if (FT_Stroker_New(library, &stroker))
	{
		eDebug("[Font] Initializing font stroker failed!");
	}
	
	strokerRadius = -1;
}

float fontRenderClass::getLineHeight(const gFont& font)
{
	if (!instance)
		return 0;
	ePtr<Font> fnt;
	getFont(fnt, font.family.c_str(), font.pointSize);
	if (!fnt)
		return 0;
	singleLock s(ftlock);
	FT_Face current_face;
	if ((FTC_Manager_LookupFace(cacheManager, fnt->scaler.face_id, &current_face) < 0) ||
	    (FTC_Manager_LookupSize(cacheManager, &fnt->scaler, &fnt->size) < 0))
	{
		eDebug("[Font] FTC_Manager_Lookup_Size failed!");
		return 0;
	}
	int height = current_face->size->metrics.height;
	if (!height)
	{
		/* some fonts don't have height filled in. Estimate it based on the bbox dimensions. */
		/* Usually, 'height' is less than the complete boundingbox height, so we use only yMax, to avoid getting a much too large line spacing */
		height = FT_MulFix(current_face->bbox.yMax, current_face->size->metrics.y_scale);
	}
	return (height>>6);
}

fontRenderClass::~fontRenderClass()
{
	singleLock s(ftlock);
	// Cached shaping fonts release their FT_Face while the FreeType library is alive.
	for (auto &entry : fontMap)
		delete entry.second;
	fontMap.clear();

//	auskommentiert weil freetype und enigma die kritische masse des suckens ueberschreiten.
//	FTC_Manager_Done(cacheManager);
//	FT_Done_FreeType(library);
}

int fontRenderClass::getFont(ePtr<Font> &font, const std::string &face, int size, int tabwidth)
{
	FTC_FaceID id;
	int renderflags;
	if (getFaceProperties(face, id, renderflags) < 0)
	{
		font = 0;
		return -1;
	}
	font = new Font(this, id, size * ((fontListEntry*)id)->scale / 100, tabwidth, renderflags);
	return 0;
}

// get all font faces (names) available in enigma2
std::vector<std::string> fontRenderClass::getFontFaces()
{
	if (!fontFacesCacheValid)
	{
		fontFacesCache.clear();
		for (const auto &entry : fontMap)
			fontFacesCache.push_back(entry.first);
		fontFacesCacheValid = true;
	}
	return fontFacesCache;
}

inline FT_UInt fontRenderClass::getCharIndex(Font *fnt, unsigned long chr, int rflags)
{
	if (rflags & RS_DIRECT)
		return (FT_UInt)chr;
	return FTC_CMapCache_Lookup(cmapCache, fnt->scaler.face_id, -1, (FT_UInt32)chr);
}

FT_UInt Font::getCharIndex(unsigned int codepoint)
{
	return renderer->getCharIndex(this, codepoint, 0);
}

void addFont(const char *filename, const char *alias, int scale_factor, int is_replacement, int renderflags)
{
	fontRenderClass::getInstance()->AddFont(filename, alias, scale_factor, renderflags);
	if (is_replacement == 1)
		eTextPara::setReplacementFont(alias);
	else if (is_replacement == -1)
		eTextPara::setFallbackFont(alias);

}

DEFINE_REF(Font);

// renderString holds ftlock while shaping. Keep one font per registered face,
// sharing its OpenType tables across labels without retaining rendered text.
hb_font_t *Font::getShapingFont(FT_Face face)
{
	auto *entry = static_cast<fontRenderClass::fontListEntry *>(scaler.face_id);
	if (!entry->shapingFont)
	{
		hb_face_t *hbFace = hb_ft_face_create_referenced(face);
		entry->shapingFont = hb_font_create(hbFace);
		hb_face_destroy(hbFace);
		hb_ot_font_set_funcs(entry->shapingFont);
	}
	unsigned int width, height;
	hb_font_get_ppem(entry->shapingFont, &width, &height);
	if (width != scaler.width || height != scaler.height)
	{
		hb_font_set_scale(entry->shapingFont, scaler.width * 64, scaler.height * 64);
		hb_font_set_ppem(entry->shapingFont, scaler.width, scaler.height);
	}
	return entry->shapingFont;
}

Font::Font(fontRenderClass *render, FTC_FaceID faceid, int isize, int tw, int renderflags): tabwidth(tw)
{
	renderer=render;
	font.face_id = faceid;
	font.width = isize;
	font.height = isize;
	font.flags = renderflags;
	scaler.face_id = faceid;
	scaler.width = isize;
	scaler.height = isize;
	scaler.pixel = 1;
	height=isize;
	if (tabwidth==-1)
		tabwidth=8*isize;
//	font.image_type |= ftc_image_flag_autohinted;
}

inline FT_Error Font::getGlyphBitmap(FT_UInt glyph_index, FTC_SBit *sbit)
{
	return renderer->getGlyphBitmap(&font, glyph_index, sbit);
}

int Font::getGlyphAdvance(FT_Face face, FT_UInt glyphIndex)
{
	FTC_SBit bitmap;
	if (!getGlyphBitmap(glyphIndex, &bitmap) && bitmap->buffer)
		return bitmap->xadvance;
	if (FT_Load_Glyph(face, glyphIndex, FT_LOAD_DEFAULT))
		return 0;
	return face->glyph->advance.x >> 6;
}

inline FT_Error Font::getGlyphImage(FT_UInt glyph_index, FT_Glyph *glyph, FT_Glyph *borderglyph, int bordersize)
{
	return renderer->getGlyphImage(&font, glyph_index, glyph, borderglyph, bordersize);
}

Font::~Font()
{
}

DEFINE_REF(eTextPara);
int eTextPara::appendGlyph(Font *current_font, FT_Face current_face, FT_UInt glyphIndex, int flags, int rflags, int border, bool last,
		bool activate_newcolor, unsigned long newcolor, const PositionedGlyph *position)
{
	int xadvance, top, left, height;
	pGlyph ng;
	int xborder = 0, endBorder = 0;

	if (border)
	{
		/* TODO: scale border radius with current_font scaling */
		if (current_font->getGlyphImage(glyphIndex, &ng.image, &ng.borderimage, 64 * border))
			return 1;
		if (ng.image && ng.image->format != FT_GLYPH_FORMAT_BITMAP)
		{
			FT_Glyph_To_Bitmap(&ng.image, FT_RENDER_MODE_NORMAL, NULL, 1);
			if (ng.image->format != FT_GLYPH_FORMAT_BITMAP) return 1;
		}
		if (ng.borderimage && ng.borderimage->format != FT_GLYPH_FORMAT_BITMAP)
		{
			FT_Glyph_To_Bitmap(&ng.borderimage, FT_RENDER_MODE_NORMAL, NULL, 1);
			if (ng.borderimage->format != FT_GLYPH_FORMAT_BITMAP) return 1;
		}
		FT_BitmapGlyph glyph = NULL;
		if (ng.borderimage)
		{
			xadvance = ng.borderimage->advance.x;
			/*
			 * NOTE: our boundingbox calculation uses xadvance, and ignores glyph width.
			 * This is fine for all glyphs, except the last one (i.e. rightmost, for left-to-right rendering)
			 * For border glyphs, xadvance is significantly smaller than the glyph width.
			 * In fact, border glyphs often have the same xadvance as normal glyphs, borders
			 * are allowed to overlap.
			 * As a result, the boundingbox is calculated too small, the actual glyphs won't
			 * fit into it, and depending on the alignment, one of the borders on the sides
			 * will be cut off.
			 * Ideally, the boundingbox calculation should be rewritten, to use both advance and glyph dimensions.
			 * However, for now we adjust xadvance of the last glyph, so the current calculation will produce
			 * a better fitting boundingbox for border glyphs.
			 *
			 * The compensation equals half of the difference between 'normal' glyph width,
			 * and border glyph width. (half the width difference is on the left, and half on the right
			 * of the glyph, we only need to compensate for the part on the right)
			 * And since xadvance is in 16.16 units, we use (dW/2) << 16 = dW << 15
			 */
			if (last && ng.image)
			{
				int extraWidth = int(((FT_BitmapGlyph)ng.borderimage)->bitmap.width) - int(((FT_BitmapGlyph)ng.image)->bitmap.width);
				xadvance += extraWidth * 32768;
				endBorder = extraWidth / 2;
			}
			if (!previous && ng.image)
			{
				/* Move the first character, to make sure the border does not get cut off by the boundingbox (xborder is in pixel units, so just divide the width difference by two)  */
				xborder = (((FT_BitmapGlyph)ng.borderimage)->bitmap.width - ((FT_BitmapGlyph)ng.image)->bitmap.width) / 2;
			}
			glyph = (FT_BitmapGlyph)ng.borderimage;
		}
		else if (ng.image)
		{
			xadvance = ng.image->advance.x;
			glyph = (FT_BitmapGlyph)ng.image;
		}
		else
		{
			return 1;
		}
		xadvance >>= 16;

		top = glyph->top;
		left = glyph->left;
		height = glyph->bitmap.rows;
	}
	else
	{
		FTC_SBit glyph;
		if (current_font->getGlyphBitmap(glyphIndex, &glyph) || !glyph->buffer)
		{
			/* SBit failed or returned corrupt data (FT_Char/FT_Byte field overflow
			 * for large glyphs: buffer=null, h=0, xadvance wraps around).
			 * Fall back to direct rendering via current_face. */
			if (FT_Load_Glyph(current_face, glyphIndex, FT_LOAD_DEFAULT) ||
			    FT_Render_Glyph(current_face->glyph, FT_RENDER_MODE_NORMAL) ||
			    FT_Get_Glyph(current_face->glyph, &ng.image))
				return 1;
			FT_BitmapGlyph bglyph = (FT_BitmapGlyph)ng.image;
			xadvance = current_face->glyph->advance.x >> 6;
			top = bglyph->top;
			left = bglyph->left;
			height = bglyph->bitmap.rows;
		}
		else
		{
			xadvance = glyph->xadvance;
			top = glyph->top;
			left = glyph->left;
			height = glyph->height;
		}
	}

	if (position)
	{
		xadvance = position->advance + endBorder;
		if (position->xOffset || position->yOffset)
		{
			left += position->xOffset;
			top -= position->yOffset;
			flags |= GS_POSITIONED;
		}
	}
	int wrapWidth = position ? position->clusterWidth : xadvance;
	if (int nx = cursor.x() + wrapWidth; wrapWidth >= 0 && (rflags & RS_WRAP) && !(flags & GS_ISFIRST) && (nx > area.right()))
	{
		int cnt = 0, maycnt = -1;
		glyphString::reverse_iterator i(glyphs.rbegin()), mayi(glyphs.rend());
			/* find first possibility (from end to begin) to break */
		while (i != glyphs.rend())
		{
			if (i->flags&(GS_CANBREAK|GS_ISFIRST)) /* stop on either space/hyphen/shy or start of line (giving up) */
				break;
			if ((i->flags&GS_MAYBREAK) && maycnt == -1)
			{
				maycnt = cnt;
				mayi = i;
			}
			cnt++;
			++i;
		}
		if (maycnt != -1 && (i == glyphs.rend() || !(i->flags&GS_CANBREAK)))
		{
			cnt = maycnt;
			i = mayi;
		}

			/* if ... */
		if (i != glyphs.rend()  /* ... we found anything */
			&& (i->flags&(GS_CANBREAK|GS_MAYBREAK)) /* ...and this is a space/hyphen/soft-hyphen */
			&& (!(i->flags & GS_ISFIRST)) /* ...and this is not an start of line (line with just a single space/hyphen) */
			&& cnt ) /* ... and there are actual non-space characters after this */
		{
				/* if we have a soft-hyphen, and used that for breaking, turn it into a real hyphen */
			if (i->flags & GS_SOFTHYPHEN)
			{
				i->flags &= ~GS_SOFTHYPHEN;
				i->flags |= GS_HYPHEN;
			}
			--i; /* skip the space/hyphen/softhyphen */
			int linelength=cursor.x()-i->x;
			i->flags|=GS_ISFIRST; /* make this a line start */
			ePoint offset=ePoint(i->x, i->y);
			newLine(rflags);
			offset-=cursor;

				/* and move everything to the end into the next line. */
			do
			{
				i->x-=offset.x();
				i->y-=offset.y();
				i->bbox.moveBy(-offset.x(), -offset.y());
			} while (i-- != glyphs.rbegin()); // rearrange them into the next line
			cursor+=ePoint(linelength, 0);  // put the cursor after that line
		} else
		{
			if (cnt)
			{
				newLine(rflags);
				flags|=GS_ISFIRST;
			}
		}
	}

	int kern=0;
	if (!position && previous && use_kerning && !glyphs.empty() && glyphs.back().font == current_font)
	{
		FT_Vector delta;
		FT_Get_Kerning(current_face, previous, glyphIndex, ft_kerning_default, &delta);
		kern=delta.x>>6;
	}

	ng.bbox.setLeft(cursor.x() + left + xborder);
	ng.bbox.setTop( cursor.y() - top );
	ng.bbox.setHeight( height );

	xadvance += kern + xborder;
	// Public glyph bounds use the layout advance, including for zero-advance marks.
	ng.bbox.setWidth(xadvance);

	ng.x = cursor.x() + kern + xborder;
	ng.y = cursor.y();
	ng.w = xadvance;

	ng.font = current_font;
	ng.glyph_index = glyphIndex;
	ng.flags = flags;

	if (activate_newcolor)
	{
		ng.flags |= GS_COLORCHANGE;
		ng.newcolor = newcolor;
	}

	glyphs.push_back(ng);

		/* when we have a SHY, don't xadvance. It will either be the last in the line (when used for breaking), or not displayed. */
	if (!(flags & GS_SOFTHYPHEN))
		cursor += ePoint(xadvance, 0);
	previous = glyphIndex;
	return 0;
}

void eTextPara::calc_bbox()
{
	if (glyphs.empty())
	{
		bboxValid = 0;
		boundBox = eRect();
		return;
	}

	bboxValid = 1;

	glyphString::iterator i(glyphs.begin());

	boundBox.setLeft(std::min(i->x, i->bbox.left()));
	boundBox.setRight(i->bbox.right());

	while (++i != glyphs.end())
	{
		if (i->flags & (GS_ISSPACE|GS_SOFTHYPHEN))
			continue;
		if (std::min(i->x, i->bbox.left()) < boundBox.left())
			boundBox.setLeft(std::min(i->x, i->bbox.left()));
		if ( i->bbox.right() > boundBox.right() )
			boundBox.setRight( i->bbox.right() );
	}
	boundBox.setTop(area.y());
	boundBox.setBottom(area.y() + totalheight);
//	eDebug("[eTextPara] boundBox left = %i, top = %i, right = %i, bottom = %i", boundBox.left(), boundBox.top(), boundBox.right(), boundBox.bottom() );
}

void eTextPara::newLine(int flags)
{
	if (maximum.width()<cursor.x())
		maximum.setWidth(cursor.x());
	cursor.setX(left);

	/* Use the cached line height computed once in setFont().
	 * Fall back to reading FT metrics if cachedLineHeight was never set. */
	int height = cachedLineHeight;
	if (!height)
	{
		height = current_face->size->metrics.height;
		if (!height)
			height = FT_MulFix(current_face->bbox.yMax,
			                   current_face->size->metrics.y_scale);
		height >>= 6;
	}

	cursor += ePoint(0, height);
	if (maximum.height()<cursor.y())
		maximum.setHeight(cursor.y());
	previous=0;
	totalheight += height;
	lineCount++;
}

eTextPara::~eTextPara()
{
	clear();
}

void eTextPara::setFont(const gFont *font, int tabwidth)
{
	ePtr<Font> fnt, replacement, fallback;
	fontRenderClass::getInstance()->getFont(fnt, font->family.c_str(), font->pointSize, tabwidth);
	if (!fnt)
		eWarning("[eTextPara] Font '%s' is missing!", font->family.c_str());
	else if (font->pointWidth > 0 && font->pointWidth < font->pointSize)
	{
		fnt->scaler.width = font->pointWidth;
		fnt->font.width   = font->pointWidth;
	}
	fontRenderClass::getInstance()->getFont(replacement, replacement_facename.c_str(), font->pointSize, tabwidth);
	fontRenderClass::getInstance()->getFont(fallback, fallback_facename.c_str(), font->pointSize, tabwidth);
	setFont(fnt, replacement, fallback);

	/* Cache line height for newLine() ─────────────────
	 * Compute once here, inside the lock that setFont(Font*,...) already
	 * holds via FTC_Manager_LookupSize, so current_face and its size
	 * metrics are guaranteed to be valid when we read them.              */
	cachedLineHeight = 0;
	if (current_face && current_face->size)
	{
		int h = current_face->size->metrics.height;
		if (!h)
			h = FT_MulFix(current_face->bbox.yMax,
			               current_face->size->metrics.y_scale);
		cachedLineHeight = h >> 6;
	}
	/* ─────────────────────────────────────────────────────────────────── */
}

std::string eTextPara::replacement_facename;
std::string eTextPara::fallback_facename;
std::set<int> eTextPara::forced_replaces;

void eTextPara::setFont(Font *fnt, Font *replacement, Font *fallback)
{
	if (!fnt)
		return;
	current_font=fnt;
	replacement_font=replacement;
	fallback_font=fallback;
	singleLock s(ftlock);

			// we ask for replacment_font first becauseof the cache
	if (replacement_font)
	{
		if ((FTC_Manager_LookupFace(fontRenderClass::instance->cacheManager,
					    replacement_font->scaler.face_id,
					    &replacement_face) < 0) ||
		    (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager,
					    &replacement_font->scaler,
					    &replacement_font->size) < 0))
		{
			eDebug("[eTextPara] setFont: FTC_Manager_Lookup_Size replacement_font failed!");
			return;
		}
	}
	if (current_font)
	{
		if ((FTC_Manager_LookupFace(fontRenderClass::instance->cacheManager,
					    current_font->scaler.face_id,
					    &current_face) < 0) ||
		    (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager,
					    &current_font->scaler,
					    &current_font->size) < 0))
		{
			eDebug("[eTextPara] setFont: FTC_Manager_Lookup_Size current_font failed!");
			return;
		}
	}
	if (fallback_font)
	{
		if ((FTC_Manager_LookupFace(fontRenderClass::instance->cacheManager,
					    fallback_font->scaler.face_id,
					    &fallback_face) < 0) ||
		    (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager,
					    &fallback_font->scaler,
					    &fallback_font->size) < 0))
		{
			eDebug("[eTextPara] FTC_Manager_Lookup_Size failed!");
			return;
		}
	}
	previous=0;
	use_kerning=FT_HAS_KERNING(current_face);
}

int eTextPara::renderString(const char *string, int rflags, int border, int markedpos)
{
	singleLock s(ftlock);

	if (!current_font)
		return -1;

	if ((FTC_Manager_LookupFace(fontRenderClass::instance->cacheManager,
				current_font->scaler.face_id,
				&current_face) < 0) ||
	    (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager,
				&current_font->scaler,
				&current_font->size) < 0))
	{
		eDebug("[eTextPara] renderString: FTC_Manager_Lookup_Size current_font failed!");
		return -1;
	}

	if (cursor.y()==-1)
	{
		int height = current_face->size->metrics.height;
		int ascender = current_face->size->metrics.ascender;
		if (!height || !ascender)
		{
			int ymax = FT_MulFix(current_face->bbox.yMax, current_face->size->metrics.y_scale);
			if (!height)
			{
				/* some fonts don't have height filled in. Estimate it based on the bbox dimensions. */
				/* For the first line we calculate the full boundingbox height, this gives the best result when centering vertically */
				height = ymax - FT_MulFix(current_face->bbox.yMin, current_face->size->metrics.y_scale);
			}
			if (!ascender)
			{
				/* some fonts don't have ascender filled in. Estimate it based on the bbox dimensions. */
				ascender = ymax;
			}
		}
		totalheight = height >> 6;
		lineCount = 1;
		cursor=ePoint(area.x(), area.y()+(ascender>>6));
		left=cursor.x();
	}

	std::vector<unsigned long> uc_string, uc_visual;
	if (string)
		uc_string.reserve(strlen(string));

	const char *p = string ? string : "";

	// With only ASCII, Latin-1 letters or strong LTR characters, visual order is logical order.
	bool simpleLtr = true;
	bool styled = false;
	constexpr int64_t inheritColor = -2, defaultColor = -1;
	int64_t color = inheritColor;
	std::vector<int64_t> logicalColors, visualColors;

	while (*p)
	{
		unsigned int unicode=(unsigned char)*p++;

		if (unicode & 0x80) // we have (hopefully) UTF8 here, and we assume that the encoding is VALID
		{
			if ((unicode & 0xE0)==0xC0) // two bytes
			{
				unicode&=0x1F;
				unicode<<=6;
				if (*p)
					unicode|=(*p++)&0x3F;
			} else if ((unicode & 0xF0)==0xE0) // three bytes
			{
				unicode&=0x0F;
				unicode<<=6;
				if (*p)
					unicode|=(*p++)&0x3F;
				unicode<<=6;
				if (*p)
					unicode|=(*p++)&0x3F;
			} else if ((unicode & 0xF8)==0xF0) // four bytes
			{
				unicode&=0x07;
				unicode<<=6;
				if (*p)
					unicode|=(*p++)&0x3F;
				unicode<<=6;
				if (*p)
					unicode|=(*p++)&0x3F;
				unicode<<=6;
				if (*p)
					unicode|=(*p++)&0x3F;
			}
			if (simpleLtr && (unicode < 0xC0 || unicode > 0xFF))
			{
				auto type = fribidi_get_bidi_type(unicode);
				simpleLtr = type == FRIBIDI_TYPE_LTR || type == FRIBIDI_TYPE_ON ||
					type == FRIBIDI_TYPE_ET || type == FRIBIDI_TYPE_CS || type == FRIBIDI_TYPE_ES;
			}
		}
		else if (unicode < 0x20 && unicode != '\n' && unicode != '\r' && unicode != '\t')
			simpleLtr = false;
		if (!(rflags & RS_DIRECT))
		{
			if (unicode == '\\')
			{
				if (*p == 'C' || (*p == 'c' && strspn(p + 1, "0123456789abcdefABCDEF:;<=>?") >= 8))
				{
					if (!styled)
						logicalColors.resize(uc_string.size(), inheritColor);
					styled = true;
					color = *p == 'C' ? defaultColor : int64_t(gRGB(p + 1).argb());
					p += *p == 'C' ? 1 : 9;
					continue;
				}
				if (*p == 't' || *p == 'r' || *p == 'n')
				{
					unicode = *p == 't' ? '\t' : (*p == 'r' ? '\r' : '\n');
					++p;
				}
			}
			if (unicode == '\r')
				continue;
			if (unicode == 0x85 || unicode == 0x2029 || unicode == 0x8A || unicode == 0xE08A)
				unicode = '\n';
		}
		uc_string.push_back(unicode);
		if (styled)
			logicalColors.push_back(color);
	}

	std::vector<bool> paragraphRtl;
	std::vector<PositionedGlyph> positioned;
	std::vector<TextCluster> visualClusters;
	const int characterOffset = characterCount;
	characterCount += uc_string.size();
	std::array<LayoutFont, 3> fonts = {{{current_font, current_face},
		{replacement_font, replacement_face}, {fallback_font, fallback_face}}};
	if (simpleLtr || (rflags & RS_DIRECT))
	{
		uc_visual.swap(uc_string);
		visualColors.swap(logicalColors);
	}
	else
	{
		for (auto &entry : fonts)
		{
			if (!entry.font)
				continue;
			FT_Size size;
			if (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager, &entry.font->scaler, &size))
				return -1;
			entry.face = size->face;
		}
		if (!layoutParagraphs(uc_string, fonts, forced_replaces, uc_visual, paragraphRtl, positioned, logicalColors, visualColors,
				&visualClusters, (rflags & RS_WRAP) ? std::max(1, area.right() - left - 2 * border) : 0,
				std::max(1, area.right() - cursor.x() - 2 * border)))
			return -1;
		hasRtlParagraph |= std::find(paragraphRtl.begin(), paragraphRtl.end(), true) != paragraphRtl.end();
		if (glyphClusters.empty())
			for (size_t i = 0; i < glyphs.size(); ++i)
				glyphClusters.push_back({int(i), int(i + 1), false});
	}
	auto nextPosition = positioned.begin();

	glyphs.reserve(glyphs.size() + uc_visual.size());
	size_t paragraph = 0;
	bool trackClusters = !visualClusters.empty() || !glyphClusters.empty();
	if (trackClusters)
		glyphClusters.reserve(glyphs.size() + uc_visual.size());

	// Multiple renderString calls can append to one paragraph. Leading text
	// inherits its preceding style; an explicit reset uses the blit foreground.
	int64_t inherited = defaultColor;
	if (styled)
	{
		for (auto g = glyphs.rbegin(); g != glyphs.rend(); ++g)
		{
			if (g->flags & GS_COLORRESET)
				break;
			if (g->flags & GS_COLORCHANGE)
			{
				inherited = g->newcolor;
				break;
			}
		}
	}
	int64_t previousColor = inherited;
	int nextflags = 0;
	int markedlen = 1;
	if (markedpos > 0xFFFF)
	{
		markedlen = markedpos >> 16;
		markedpos &= 0xFFFF;
	}

	for (std::vector<unsigned long>::const_iterator i(uc_visual.begin());
		i != uc_visual.end(); ++i)
	{
		int isprintable=1;
		int flags = nextflags;
		int visualIndex = i - uc_visual.begin();
		TextCluster cluster = visualClusters.empty() ? TextCluster{visualIndex, visualIndex + 1, false} : visualClusters[visualIndex];
		if (cluster.start >= 0)
		{
			cluster.start += characterOffset;
			cluster.end += characterOffset;
		}
		if (!paragraphRtl.empty() && paragraphRtl[paragraph])
			flags |= GS_RTL;
		unsigned long chr = *i;

		if (!(rflags&RS_DIRECT))
		{
			switch (chr)
			{
			case '\t':
				isprintable=0;
				cursor+=ePoint(current_font->tabwidth, 0);
				cursor-=ePoint(cursor.x()%current_font->tabwidth, 0);
				if (!(nextflags&GS_ISFIRST))
					nextflags|=GS_FIXED;
				break;
			case 0x8A:
			case 0xE08A:
			case '\n':
				isprintable=0;
				newLine(rflags);
				++paragraph;
				nextflags|=GS_ISFIRST;
				nextflags&=~GS_FIXED;
				break;
			case '\r':
			case 0x86: case 0xE086:
			case 0x87: case 0xE087:
				isprintable=0;
				break;
			case 0xAD: // soft-hyphen
				flags |= GS_SOFTHYPHEN;
				chr = 0x2010; /* hyphen */
				break;
			case 0x2010:
			case '-':
				flags |= GS_HYPHEN;
				break;
			case '/':
				flags |= GS_MAYBREAK;
				break;
			case ' ':
				flags|=GS_ISSPACE;
			default:
				break;
			}
		}
		if (isprintable)
		{
			const int64_t style = styled ? visualColors[i - uc_visual.begin()] : inheritColor;
			const int64_t desiredColor = style == inheritColor ? inherited : style;
			const bool colorChanged = desiredColor != previousColor;
			if (colorChanged && desiredColor == -1)
				flags |= GS_COLORRESET;

			if (markedpos == -2 || (markedpos >= 0 && cluster.start < markedpos + markedlen && cluster.end > markedpos))
				flags |= GS_INVERT;

			FT_UInt index = 0;

				/* FIXME: our font doesn't seem to have a hyphen, so use hyphen-minus for it. */
			if (chr == 0x2010)
				chr = '-';

			const PositionedGlyph *position = nullptr;
			LayoutFont source{};
			if (nextPosition != positioned.end() && nextPosition->visualIndex == size_t(i - uc_visual.begin()))
			{
				position = &*nextPosition++;
				source = fonts[position->fontIndex];
				index = position->glyph;
			}
			else
			{
				for (auto &candidate : fonts)
				{
					if (!candidate.font || (&candidate == &fonts[0] && forced_replaces.count(chr)))
						continue;
					index = fontRenderClass::instance->getCharIndex(candidate.font, chr, rflags);
					if (index)
					{
						source = candidate;
						break;
					}
				}
			}
			if (index || position)
			{
				// Complex text was broken in logical order before per-line bidi layout.
				int result = appendGlyph(source.font, source.face, index, flags, paragraphRtl.empty() ? rflags : rflags & ~RS_WRAP,
					border, i == uc_visual.end() - 1, colorChanged && desiredColor >= 0, static_cast<unsigned long>(desiredColor), position);
				if (!result)
				{
					const size_t glyphIndex = glyphs.size() - 1;
					if (!trackClusters && cluster.start != int(glyphIndex))
					{
						// Tabs, newlines and missing glyphs can also break the LTR
						// identity mapping. Earlier glyphs still map one-to-one.
						glyphClusters.reserve(glyphs.size() + uc_visual.size() - visualIndex - 1);
						for (size_t j = 0; j < glyphIndex; ++j)
							glyphClusters.push_back({int(j), int(j + 1), false});
						trackClusters = true;
					}
					if (trackClusters)
						glyphClusters.push_back(cluster);
				}
			}
			else
				eDebug("[eTextPara] Unicode U+%4lx not present", chr);

			if (index || position)
			{
				nextflags = 0;
				previousColor = desiredColor;
			}
		} else if (nextflags&GS_ISFIRST && !glyphs.empty() && cluster.start >= 0)
		{
			// Newline found, mark the last glyph with the newline flag
			glyphs.back().flags |= GS_LF;
		}
	}
	bboxValid=false;
	calc_bbox();
	return 0;
}

void eTextPara::blit(gDC &dc, const ePoint &offset, const gRGB &cbackground, const gRGB &foreground, bool border, bool marked)
{
	if (glyphs.empty()) return;

	singleLock s(ftlock);

	if (!current_font)
		return;

	if ((FTC_Manager_LookupFace(fontRenderClass::instance->cacheManager,
 				    current_font->scaler.face_id,
 				    &current_face) < 0) ||
	    (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager,
				    &current_font->scaler,
				    &current_font->size) < 0))
	{
		eDebug("[eTextPara] FTC_Manager_Lookup_Size failed!");
		return;
	}
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wregister"

	ePtr<gPixmap> target;
	dc.getPixmap(target);
	gUnmanagedSurface *surface = target->surface;
	gRGB currentforeground = foreground;
	const gRGB background = (m_blend && surface->bpp == 32 && !marked) ? gRGB(currentforeground.r, currentforeground.g, currentforeground.b, 200) : cbackground;

	register int opcode = -1;

	__u32 lookup32_normal[16];
	__u32 lookup32_invert[16];
	__u16 *lookup16_normal = (__u16*)lookup32_normal; // shares the same memory
	__u16 *lookup16_invert = (__u16*)lookup32_invert;
	gColor *lookup8_normal = 0;
	gColor *lookup8_invert = (gColor*)lookup32_invert;
	__u32 *lookup32;
	__u16 *lookup16;
	gColor *lookup8;

	gRegion sarea(eRect(0, 0, surface->x, surface->y));
	gRegion clip = dc.getClip() & sarea;
	clip &= eRect(area.left() + offset.x(), area.top() + offset.y(), area.width(), area.height()+(current_face->size->metrics.ascender>>6));

	int buffer_stride=surface->stride;

	bool setcolor = true;
	for (glyphString::iterator i(glyphs.begin()); i != glyphs.end(); ++i)
	{
		/* don't do colorchanges in borders */
		if (!border)
		{
			if (i->flags & GS_COLORRESET)
			{
				currentforeground = foreground;
				setcolor = true;
			}
			else if (i->flags & GS_COLORCHANGE)
			{
				currentforeground = i->newcolor;
				setcolor = true;
			}
		}
		if (setcolor)
		{
			setcolor = false;
			if (surface->bpp == 8)
			{
				if (surface->clut.data)
				{
					lookup8_normal=getColor(surface->clut, background, currentforeground).lookup;

					int i;
					for (i=0; i<16; ++i)
						lookup8_invert[i] = lookup8_normal[i^0xF];

					opcode=0;
				} else
					opcode=1;
			} 
			else if (surface->bpp == 32)
			{
				opcode = (m_blend) ? 4 : 3;

				for (int i=0; i<16; ++i)
				{
					unsigned char da = background.a, dr = background.r, dg = background.g, db = background.b;
#define BLEND(y, x, a) (y + (((x-y) * a)>>8))

					int sa = i * 16;
					if (sa < 256)
					{
						da = BLEND(background.a, currentforeground.a, sa) & 0xFF; // NOSONAR
						dr = BLEND(background.r, currentforeground.r, sa) & 0xFF; // NOSONAR
						dg = BLEND(background.g, currentforeground.g, sa) & 0xFF; // NOSONAR
						db = BLEND(background.b, currentforeground.b, sa) & 0xFF; // NOSONAR
					}
#undef BLEND
					da ^= 0xFF;
					lookup32_normal[i]=db | (dg << 8) | (dr << 16) | (da << 24);;
				}
				for (int i=0; i<16; ++i)
					lookup32_invert[i]=lookup32_normal[i^0xF];
			} 
			else if (surface->bpp == 16)
			{
				opcode=2;
				for (int i = 0; i != 16; ++i)
				{
#define BLEND(y, x, a) (y + (((x-y) * a)>>8))
					unsigned char da = background.a, dr = background.r, dg = background.g, db = background.b;
					int sa = i * 16;
					if (sa < 256)
					{
						dr = BLEND(background.r, foreground.r, sa) & 0xFF;
						dg = BLEND(background.g, foreground.g, sa) & 0xFF;
						db = BLEND(background.b, foreground.b, sa) & 0xFF;
					}
#undef BLEND
#if BYTE_ORDER == LITTLE_ENDIAN
					lookup16_normal[i] = bswap_16(((db >> 3) << 11) | ((dg >> 2) << 5) | (dr >> 3));
#else
					lookup16_normal[i] = ((db >> 3) << 11) | ((dg >> 2) << 5) | (dr >> 3);
#endif
					da ^= 0xFF;
				}
				for (int i=0; i<16; ++i)
					lookup16_invert[i]=lookup16_normal[i^0xF];
			} 
			else
			{
				eWarning("[eTextPara] Can't render to %dbpp!", surface->bpp);
				return;
			}
		}
		if (i->flags & GS_SOFTHYPHEN)
			continue;

		if (!(i->flags & GS_INVERT))
		{
			lookup8 = lookup8_normal;
			lookup16 = lookup16_normal;
			lookup32 = lookup32_normal;
		} 
		else
		{
			lookup8 = lookup8_invert;
			lookup16 = lookup16_invert;
			lookup32 = lookup32_invert;
		}

		int rxbase, rybase;
		__u8 *dbase;
		__u8 *sbase;
		int sxbase;
		int sybase;
		int pitch;
		if (i->image)
		{
			FT_BitmapGlyph glyph = border ? (FT_BitmapGlyph)i->borderimage : (FT_BitmapGlyph)i->image;
			if (!glyph || !glyph->bitmap.buffer) continue;
			rxbase = i->x + glyph->left + offset.x();
			rybase = i->y - glyph->top + offset.y();
			sbase = glyph->bitmap.buffer;
			sxbase = glyph->bitmap.width;
			sybase = glyph->bitmap.rows;
			pitch = glyph->bitmap.pitch;
		}
		else
		{
			static FTC_SBit glyph_bitmap;
			if (fontRenderClass::instance->getGlyphBitmap(&i->font->font, i->glyph_index, &glyph_bitmap))
				continue;
			rxbase=i->x+glyph_bitmap->left + offset.x();
			rybase=i->y - glyph_bitmap->top + offset.y();
			sbase=glyph_bitmap->buffer;
			sxbase=glyph_bitmap->width;
			sybase=glyph_bitmap->height;
			pitch = glyph_bitmap->pitch;
		}
		if (i->flags & GS_POSITIONED)
		{
			// The bounding box already tracks the positioned bitmap origin,
			// including moves made while wrapping and aligning the line.
			rxbase = i->bbox.left() + offset.x();
			rybase = i->bbox.top() + offset.y();
			if (!border && i->borderimage)
			{
				auto outline = reinterpret_cast<FT_BitmapGlyph>(i->borderimage);
				auto fill = reinterpret_cast<FT_BitmapGlyph>(i->image);
				rxbase += fill->left - outline->left;
				rybase += outline->top - fill->top;
			}
		}
		dbase = (__u8*)(surface->data)+buffer_stride*rybase+rxbase*surface->bypp;
		for (unsigned int c = 0; c < clip.rects.size(); ++c)
		{
			int rx = rxbase, ry = rybase;
			__u8 *d = dbase;
			__u8 *s = sbase;
			register int sx = sxbase;
			int sy = sybase;
			if ((sy+ry) >= clip.rects[c].bottom())
				sy = clip.rects[c].bottom()-ry;
			if ((sx+rx) >= clip.rects[c].right())
				sx = clip.rects[c].right()-rx;
			if (rx < clip.rects[c].left())
			{
				int diff=clip.rects[c].left()-rx;
				s+=diff;
				sx-=diff;
				rx+=diff;
				d+=diff*surface->bypp;
			}
			if (ry < clip.rects[c].top())
			{
				int diff=clip.rects[c].top()-ry;
				s+=diff*pitch;
				sy-=diff;
				ry+=diff;
				d+=diff*buffer_stride;
			}
			if ((sx>0) && (sy>0))
			{
				int extra_source_stride = pitch - sx;
				switch (opcode)
				{
				case 0: 		// 4bit lookup to 8bit
					{
						register int extra_buffer_stride = buffer_stride - sx;
						register __u8 *td=d;
						for (int ay = 0; ay < sy; ay++)
						{
							register int ax;

							for (ax=0; ax<sx; ax++)
							{
								register int b=(*s++)>>4;
								if(b)
									*td=lookup8[b];
								++td;
							}
							s += extra_source_stride;
							td += extra_buffer_stride;
						}
					}
					break;
				case 1:	// 8bit direct
					{
						register int extra_buffer_stride = buffer_stride - sx;
						register __u8 *td=d;
						for (int ay = 0; ay < sy; ay++)
						{
							register int ax;
							for (ax=0; ax<sx; ax++)
							{
								register int b=*s++;
								*td++^=b;
							}
							s += extra_source_stride;
							td += extra_buffer_stride;
						}
					}
					break;
				case 2: // 16bit
					{
						int extra_buffer_stride = (buffer_stride >> 1) - sx;
						register __u16 *td = (__u16*)d;
						for (int ay = 0; ay != sy; ay++)
						{
								register int ax;
								for (ax = 0; ax != sx; ax++)
								{
									register int b = (*s++) >> 4;
									if (b)
										*td = lookup16[b];
									++td;
								}
								s += extra_source_stride;
								td += extra_buffer_stride;
						}
					}
					break;
				case 3: // 32bit
					{
						register int extra_buffer_stride = (buffer_stride >> 2) - sx;
						register __u32 *td=(__u32*)d;
						for (int ay = 0; ay < sy; ay++)
						{
							register int ax;
							for (ax=0; ax<sx; ax++)
							{
								register int b=(*s++)>>4;
								if(b)
									*td=lookup32[b] | 0xFF000000;
								++td;
							}
							s += extra_source_stride;
							td += extra_buffer_stride;
						}
					}
					break;
				case 4: // 32-bit blend
					{
						register int extra_buffer_stride = (buffer_stride >> 2) - sx;
						register __u32 *td = (__u32 *)d;
						for (int ay = 0; ay < sy; ay++)
						{
							register int ax;
							for (ax = 0; ax < sx; ax++)
							{
								register int b = (*s++) >> 4;
								if (b)
								{
									unsigned char frame_a = (*td) >> 24 & 0xFF;
									unsigned char frame_r = (*td) >> 16 & 0xFF;
									unsigned char frame_g = (*td) >> 8 & 0xFF;
									unsigned char frame_b = (*td) & 0xFF;

									unsigned char da = lookup32[b] >> 24 & 0xFF;
									unsigned char dr = lookup32[b] >> 16 & 0xFF;
									unsigned char dg = lookup32[b] >> 8 & 0xFF;
									unsigned char db = lookup32[b] & 0xFF;

#define BLEND(y, x, a) (y + (((x-y) * a)>>8))
									frame_a = BLEND(frame_a, (unsigned char)(currentforeground.a ^ 0xFF), da) & 0xFF;
									frame_r = BLEND(frame_r, dr, da) & 0xFF;
									frame_g = BLEND(frame_g, dg, da) & 0xFF;
									frame_b = BLEND(frame_b, db, da) & 0xFF;
#undef BLEND
									*td = (frame_a << 24) | (frame_r << 16) | (frame_g << 8) | frame_b;
								}
								++td;
							}
							s += extra_source_stride;
							td += extra_buffer_stride;
						}
					}
					break;
				}
			}
		}
	}
#pragma GCC diagnostic pop
}

void eTextPara::realign(int dir, int markedpos, int scrollpos)	// der code hier ist ein wenig merkwuerdig.
{
	if (markedpos > 0xFFFF)
		markedpos &= 0xFFFF;
	glyphString::iterator begin(glyphs.begin()), c(glyphs.begin()), end(glyphs.begin()), last;
	if ((dir == dirLeft || (dir == dirBidi && !hasRtlParagraph)) && markedpos < 0)
		return;
	while (c != glyphs.end())
	{
		int linelength=0;
		int linespace=area.width();
		int numspaces=0, num=0;
		begin=end;

		ASSERT( end != glyphs.end());

		glyphString::iterator nonspace_end(begin);

			// zeilenende suchen
		do {
			last=end;
			++end;
			if (!(last->flags&GS_ISSPACE) && (end == glyphs.end() || end->flags&(GS_ISSPACE|GS_ISFIRST)))
				nonspace_end = end;
		} while ((end != glyphs.end()) && (!(end->flags&GS_ISFIRST)));
			// end zeigt jetzt auf begin der naechsten zeile

		for (c=begin; c!=nonspace_end; ++c)
		{
			if (dir == dirBlock && c->flags&GS_FIXED)
			{
				numspaces=0;
				num=0;
				linespace=area.width()-c->x;
				linelength=0;
				begin = c;
			}
			if (c->flags&GS_ISSPACE)
				numspaces++;
			linelength+=c->w;
			num++;
		}
		c = end;
		if (dir == dirBidi && !(last->flags & GS_RTL) && markedpos < 0)
			continue;

		// Ensure the marked position is visible.
		bool offset_set = false;
		if (markedpos >= 0)
		{
			if (linelength > area.width())
			{
				eRect bbox;
				if (!getCharacterBBox(markedpos, bbox) && !getCaretBBox(markedpos, bbox))
					continue;
				if (scrollpos == 50)
				{
					int mark_center = bbox.left() + bbox.width() / 2 - area.left();
					int area_center = area.width() / 2;
					// The mark is near the start, leave left aligned.
					if (mark_center < area_center)
						return;
					// The mark is near the end, set right aligned.
					if (mark_center > linelength - area_center)
						dir = dirRight;
					// Center on the mark.
					else
					{
						dir = dirCenter;
						m_offset = area_center - mark_center;
						offset_set = true;
					}
				}
				else
				{
					dir = dirRight;
					offset_set = true;
					int scroll_offset = area.width() * scrollpos / 100;
					if (bbox.left() + m_offset < area.left() + scroll_offset)
					{
						m_offset = area.left() + scroll_offset - bbox.left();
						// The mark is near the start, leave left aligned.
						if (m_offset >= 0)
						{
							m_offset = 0;
							return;
						}
					}
					else if (bbox.right() + m_offset >= area.right() - scroll_offset)
					{
						m_offset = area.right() - scroll_offset - bbox.right();
						// The mark is near the end, set right aligned.
						if (m_offset < area.width() - linelength)
							offset_set = false;
					}
					// else mark is visible, keep current offset
				}
			}
			else if (dir == dirLeft || (dir == dirBidi && !(last->flags & GS_RTL)))
				continue;
		}

		switch (dir)
		{
		case dirCenterIfFits:
			// If the text is larger than the available space,
			// don't re-align but align left.
			if (linelength > area.width())
				return;
			dir = dirCenter;
			[[fallthrough]];
		case dirRight:
		case dirCenter:
		case dirBidi:
		{
			if (!offset_set)
			{
				m_offset=area.width()-linelength;
				if (dir==dirCenter)
					m_offset/=2;
			}
			while (begin != end)
			{
				begin->bbox.moveBy(m_offset,0);
				begin->x += m_offset;
				++begin;
			}
			break;
		}
		case dirBlock:
		{
			if (end == glyphs.end())
			{
				/* last line, use left alignment */
				continue;
			}

			if (!numspaces)
			{
				/* no spaces, use left alignment */
				continue;
			}

			if (last->flags & GS_LF)
			{
				/* line ends with a linefeed, use left alignment */
				continue;
			}

			int off=(linespace-linelength)*256/(numspaces?numspaces:(num-1));
			int curoff=0;

			while (begin != nonspace_end)
			{
				int doadd=0;
				if (begin->flags & GS_ISSPACE)
					doadd=1;
				begin->x+=curoff>>8;
				begin->bbox.moveBy(curoff>>8,0);
				if (doadd)
					curoff+=off;
				++begin;
			}
			curoff = (curoff+255) >> 8;
			while (begin != end) {
				begin->x+=curoff;
				begin->bbox.moveBy(curoff,0);
				++begin;
			}
			break;
		}
		}
	}
	bboxValid=false;
	calc_bbox();
}

bool eTextPara::getCharacterBBox(int position, eRect &box) const
{
	if (position < 0)
		return false;
	if (glyphClusters.empty())
	{
		if (position >= int(glyphs.size()))
			return false;
		box = glyphs[position].bbox;
		return true;
	}
	bool found = false;
	for (size_t i = 0; i < glyphs.size(); ++i)
	{
		const auto &cluster = glyphClusters[i];
		if (position >= cluster.start && position < cluster.end)
		{
			box = found ? box | glyphs[i].bbox : glyphs[i].bbox;
			found = true;
		}
	}
	return found;
}

bool eTextPara::getCaretBBox(int position, eRect &box) const
{
	if (position < 0 || position > characterCount)
		return false;
	if (glyphs.empty())
	{
		box = eRect(area.left(), area.top(), 2, cachedLineHeight);
		return position == 0;
	}
	int character = position == characterCount ? position - 1 : position;
	if (!getCharacterBBox(character, box))
		return false;
	TextCluster cluster{character, character + 1, false};
	for (const auto &entry : glyphClusters)
		if (character >= entry.start && character < entry.end)
		{
			cluster = entry;
			break;
		}
	int offset = box.width() * (position - cluster.start) / (cluster.end - cluster.start);
	int x = cluster.rtl ? box.right() - offset : box.left() + offset;
	box = eRect(x - 1, box.top(), 2, box.height());
	return true;
}

std::vector<eRect> eTextPara::getSelectionBoxes(int position, int length) const
{
	std::vector<eRect> boxes;
	if (position < 0 || length <= 0)
		return boxes;
	size_t first = glyphClusters.empty() ? std::min(size_t(position), glyphs.size()) : 0;
	size_t end = glyphClusters.empty() ? std::min(size_t(position + length), glyphs.size()) : glyphs.size();
	bool adjacent = false;
	int baseline = 0;
	for (size_t i = first; i < end; ++i)
	{
		const auto cluster = glyphClusters.empty() ? TextCluster{int(i), int(i + 1), false} : glyphClusters[i];
		if (cluster.start < position + length && cluster.end > position)
		{
			if (adjacent && baseline == glyphs[i].y)
				boxes.back() |= glyphs[i].bbox;
			else
				boxes.push_back(glyphs[i].bbox);
			baseline = glyphs[i].y;
			adjacent = true;
		}
		else
			adjacent = false;
	}
	return boxes;
}

void eTextPara::setCharacterFlag(int position, int flag)
{
	for (size_t i = 0; i < glyphs.size(); ++i)
	{
		const auto cluster = glyphClusters.empty() ? TextCluster{int(i), int(i + 1), false} : glyphClusters[i];
		if (position >= cluster.start && position < cluster.end)
			glyphs[i].flags |= flag;
	}
}

void eTextPara::clear()
{
	singleLock s(ftlock);

	current_font = 0;
	replacement_font = 0;

	for (unsigned int i = 0; i < glyphs.size(); i++)
	{
		if (glyphs[i].image) FT_Done_Glyph(glyphs[i].image);
		if (glyphs[i].borderimage) FT_Done_Glyph(glyphs[i].borderimage);
	}
	glyphs.clear();
	glyphClusters.clear();
	characterCount = 0;
	hasRtlParagraph = false;
	totalheight = 0;
	lineCount = 0;
}

eAutoInitP0<fontRenderClass> init_fontRenderClass(eAutoInitNumbers::graphic-1, "Font Render Class");
