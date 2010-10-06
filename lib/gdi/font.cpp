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
#ifdef HAVE_FREETYPE2
#define FTC_Image_Cache_New(a,b)	FTC_ImageCache_New(a,b)
#define FTC_Image_Cache_Lookup(a,b,c,d)	FTC_ImageCache_Lookup(a,b,c,d,NULL)
#define FTC_SBit_Cache_New(a,b)		FTC_SBitCache_New(a,b)
#define FTC_SBit_Cache_Lookup(a,b,c,d)	FTC_SBitCache_Lookup(a,b,c,d,NULL)
#endif

#include <lib/base/eerror.h>
#include <lib/gdi/lcd.h>
#include <lib/gdi/grc.h>
#include <lib/base/elock.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

#define HAVE_FRIBIDI
// until we have it in the cdk

#ifdef HAVE_FRIBIDI
#include <fribidi/fribidi.h>
#endif

#include <map>

fontRenderClass *fontRenderClass::instance;

static pthread_mutex_t ftlock=PTHREAD_ADAPTIVE_MUTEX_INITIALIZER_NP;

#ifndef HAVE_FREETYPE2
static FTC_Font cache_current_font=0;
#endif

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
//	eDebug("[FONT] creating new font color cache entry %02x%02x%02x%02x .. %02x%02x%02x%02x", start.a, start.r, start.g, start.b,
//		end.a, end.r, end.g, end.b);
	n.build(16, pal, start, end);
//	for (int i=0; i<16; i++)
//		eDebugNoNewLine("%02x|%02x%02x%02x%02x ", (int)n.lookup[i], pal.data[n.lookup[i]].a, pal.data[n.lookup[i]].r, pal.data[n.lookup[i]].g, pal.data[n.lookup[i]].b);
//	eDebug("");
	return n;
}

fontRenderClass *fontRenderClass::getInstance()
{
	return instance;
}

FT_Error myFTC_Face_Requester(FTC_FaceID	face_id,
															FT_Library	library,
															FT_Pointer	request_data,
															FT_Face*		aface)
{
	return ((fontRenderClass*)request_data)->FTC_Face_Requester(face_id, aface);
}


FT_Error fontRenderClass::FTC_Face_Requester(FTC_FaceID	face_id, FT_Face* aface)
{
	fontListEntry *font=(fontListEntry *)face_id;
	if (!font)
		return -1;
	
//	eDebug("[FONT] FTC_Face_Requester (%s)", font->face.c_str());

	int error;
	if ((error=FT_New_Face(library, font->filename.c_str(), 0, aface)))
	{
		eDebug(" failed: %s", strerror(error));
		return error;
	}
	FT_Select_Charmap(*aface, ft_encoding_unicode);
	return 0;
}																																																																

FTC_FaceID fontRenderClass::getFaceID(const std::string &face)
{
	for (fontListEntry *f=font; f; f=f->next)
	{
		if (f->face == face)
			return (FTC_FaceID)f;
	}
	return 0;
}

FT_Error fontRenderClass::getGlyphBitmap(FTC_Image_Desc *font, FT_ULong glyph_index, FTC_SBit *sbit)
{
	FT_Error res=FTC_SBit_Cache_Lookup(sbitsCache, font, glyph_index, sbit);
	return res;
}

std::string fontRenderClass::AddFont(const std::string &filename, const std::string &name, int scale)
{
	eDebugNoNewLine("[FONT] adding font %s...", filename.c_str());
	fflush(stdout);
	int error;
	fontListEntry *n=new fontListEntry;

	n->scale=scale;
	FT_Face face;
	singleLock s(ftlock);

	if ((error=FT_New_Face(library, filename.c_str(), 0, &face)))
		eFatal(" failed: %s", strerror(error));

	n->filename=filename;
	n->face=name;
	FT_Done_Face(face);

	n->next=font;
	eDebug("OK (%s)", n->face.c_str());
	font=n;

	return n->face;
}

fontRenderClass::fontListEntry::~fontListEntry()
{
}

fontRenderClass::fontRenderClass(): fb(fbClass::getInstance())
{
	instance=this;
	eDebug("[FONT] initializing lib...");
	{
		if (FT_Init_FreeType(&library))
		{
			eDebug("[FONT] initializing failed.");
			return;
		}
	}
	eDebug("[FONT] loading fonts...");
	fflush(stdout);
	font=0;
	
	int maxbytes=4*1024*1024;
	eDebug("[FONT] Intializing font cache, using max. %dMB...", maxbytes/1024/1024);
	fflush(stdout);
	{
		if (FTC_Manager_New(library, 8, 8, maxbytes, myFTC_Face_Requester, this, &cacheManager))
		{
			eDebug("[FONT] initializing font cache failed!");
			return;
		}
		if (!cacheManager)
		{
			eDebug("[FONT] initializing font cache manager error.");
			return;
		}
		if (FTC_SBit_Cache_New(cacheManager, &sbitsCache))
		{
			eDebug("[FONT] initializing font cache sbit failed!");
			return;
		}
		if (FTC_Image_Cache_New(cacheManager, &imageCache))
		{
			eDebug("[FONT] initializing font cache imagecache failed!");
		}
	}
	return;
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
#ifdef HAVE_FREETYPE2
	if ((FTC_Manager_LookupFace(cacheManager, fnt->scaler.face_id, &current_face) < 0) ||
	    (FTC_Manager_LookupSize(cacheManager, &fnt->scaler, &fnt->size) < 0))
#else
	if (FTC_Manager_Lookup_Size(cacheManager, &fnt->font.font, &current_face, &fnt->size)<0)
#endif
	{
		eDebug("FTC_Manager_Lookup_Size failed!");
		return 0;
	}
	int linegap=current_face->size->metrics.height-(current_face->size->metrics.ascender+current_face->size->metrics.descender);
	float height=(current_face->size->metrics.ascender+current_face->size->metrics.descender+linegap)/64.0;
	return height;
}

fontRenderClass::~fontRenderClass()
{
	singleLock s(ftlock);
	while(font)
	{
		fontListEntry *f=font;
		font=font->next;
		delete f;
	}
//	auskommentiert weil freetype und enigma die kritische masse des suckens ueberschreiten. 
//	FTC_Manager_Done(cacheManager);
//	FT_Done_FreeType(library);
}

int fontRenderClass::getFont(ePtr<Font> &font, const std::string &face, int size, int tabwidth)
{
	FTC_FaceID id=getFaceID(face);
	if (!id)
	{
		font = 0;
		return -1;
	}
	font = new Font(this, id, size * ((fontListEntry*)id)->scale / 100, tabwidth);
	return 0;
}

void addFont(const char *filename, const char *alias, int scale_factor, int is_replacement)
{
	fontRenderClass::getInstance()->AddFont(filename, alias, scale_factor);
	if (is_replacement)
		eTextPara::setReplacementFont(alias);
}

DEFINE_REF(Font);

Font::Font(fontRenderClass *render, FTC_FaceID faceid, int isize, int tw): tabwidth(tw)
{
	renderer=render;
#ifdef HAVE_FREETYPE2
	font.face_id = faceid;
	font.width = isize;
	font.height = isize;
	font.flags = FT_LOAD_DEFAULT;
	scaler.face_id = faceid;
	scaler.width = isize;
	scaler.height = isize;
	scaler.pixel = 1;
#else
	font.font.face_id=faceid;
	font.font.pix_width	= isize;
	font.font.pix_height = isize;
	font.image_type = ftc_image_grays;
#endif
	height=isize;
	if (tabwidth==-1)
		tabwidth=8*isize;
//	font.image_type |= ftc_image_flag_autohinted;
}

FT_Error Font::getGlyphBitmap(FT_ULong glyph_index, FTC_SBit *sbit)
{
	return renderer->getGlyphBitmap(&font, glyph_index, sbit);
}

Font::~Font()
{
}

DEFINE_REF(eTextPara);

int eTextPara::appendGlyph(Font *current_font, FT_Face current_face, FT_UInt glyphIndex, int flags, int rflags)
{
	FTC_SBit glyph;
	if (current_font->getGlyphBitmap(glyphIndex, &glyph))
		return 1;

	int nx=cursor.x();

	nx+=glyph->xadvance;

	if (
			(rflags&RS_WRAP) && 
			(nx >= area.right())
		)
	{
		int cnt = 0;
		glyphString::reverse_iterator i(glyphs.rbegin());
			/* find first possibility (from end to begin) to break */
		while (i != glyphs.rend())
		{
			if (i->flags&(GS_CANBREAK|GS_ISFIRST)) /* stop on either space/hyphen/shy or start of line (giving up) */
				break;
			cnt++;
			++i;
		}

			/* if ... */
		if (i != glyphs.rend()  /* ... we found anything */
			&& (i->flags&GS_CANBREAK) /* ...and this is a space/hyphen/soft-hyphen */
			&& (!(i->flags & GS_ISFIRST)) /* ...and this is not an start of line (line with just a single space/hyphen) */
			&& cnt ) /* ... and there are actual non-space characters after this */
		{
				/* if we have a soft-hyphen, and used that for breaking, turn it into a real hyphen */
			if (i->flags & GS_SOFTHYPHEN)
			{
				i->flags &= ~GS_SOFTHYPHEN;
				i->flags |= GS_HYPHEN;
			}
			--i; /* skip the space/hypen/softhyphen */
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
				--lineChars.back();
				++charCount;
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

	int xadvance=glyph->xadvance, kern=0;

	if (previous && use_kerning)
	{
		FT_Vector delta;
		FT_Get_Kerning(current_face, previous, glyphIndex, ft_kerning_default, &delta);
		kern=delta.x>>6;
	}

	pGlyph ng;
	ng.bbox.setLeft( ((flags&GS_ISFIRST)|(cursor.x()-1))+glyph->left );
	ng.bbox.setTop( cursor.y() - glyph->top );
	ng.bbox.setWidth( glyph->width );
	ng.bbox.setHeight( glyph->height );

	xadvance += kern;
	ng.bbox.setWidth(xadvance);

	ng.x = cursor.x()+kern;
	ng.y = cursor.y();
	ng.w = xadvance;
	ng.font = current_font;
	ng.glyph_index = glyphIndex;
	ng.flags = flags;
	glyphs.push_back(ng);
	++charCount;

		/* when we have a SHY, don't xadvance. It will either be the last in the line (when used for breaking), or not displayed. */
	if (!(flags & GS_SOFTHYPHEN))
		cursor += ePoint(xadvance, 0);
	previous = glyphIndex;
	return 0;
}

void eTextPara::calc_bbox()
{
	if (!glyphs.size())
	{
		bboxValid = 0;
		boundBox = eRect();
		return;
	}
	
	bboxValid = 1;

	glyphString::iterator i(glyphs.begin());
	
	boundBox = i->bbox; 
	++i;

	for (; i != glyphs.end(); ++i)
	{
		if (i->flags & (GS_ISSPACE|GS_SOFTHYPHEN))
			continue;
		if ( i->bbox.left() < boundBox.left() )
			boundBox.setLeft( i->bbox.left() );
		if ( i->bbox.top() < boundBox.top() )
			boundBox.setTop( i->bbox.top() );
		if ( i->bbox.right() > boundBox.right() )
			boundBox.setRight( i->bbox.right() );
		if ( i->bbox.bottom() > boundBox.bottom() )
			boundBox.setBottom( i->bbox.bottom() );
	}
//	eDebug("boundBox left = %i, top = %i, right = %i, bottom = %i", boundBox.left(), boundBox.top(), boundBox.right(), boundBox.bottom() );
}

void eTextPara::newLine(int flags)
{
	if (maximum.width()<cursor.x())
		maximum.setWidth(cursor.x());
	cursor.setX(left);
	previous=0;
	int linegap=current_face->size->metrics.height-(current_face->size->metrics.ascender+current_face->size->metrics.descender);

	lineOffsets.push_back(cursor.y());
	lineChars.push_back(charCount);
	charCount=0;

	cursor+=ePoint(0, (current_face->size->metrics.ascender+current_face->size->metrics.descender+linegap)>>6);

	if (maximum.height()<cursor.y())
		maximum.setHeight(cursor.y());
	previous=0;
}

eTextPara::~eTextPara()
{
	clear();
}

void eTextPara::setFont(const gFont *font)
{
	ePtr<Font> fnt, replacement;
	fontRenderClass::getInstance()->getFont(fnt, font->family.c_str(), font->pointSize);
	if (!fnt)
		eWarning("FONT '%s' MISSING!", font->family.c_str());
	fontRenderClass::getInstance()->getFont(replacement, replacement_facename.c_str(), font->pointSize);
	setFont(fnt, replacement);
}

std::string eTextPara::replacement_facename;
std::set<int> eTextPara::forced_replaces;

void eTextPara::setFont(Font *fnt, Font *replacement)
{
	if (!fnt)
		return;
	current_font=fnt;
	replacement_font=replacement;
	singleLock s(ftlock);

			// we ask for replacment_font first becauseof the cache
	if (replacement_font)
	{
#ifdef HAVE_FREETYPE2
		if ((FTC_Manager_LookupFace(fontRenderClass::instance->cacheManager,
					    replacement_font->scaler.face_id,
					    &replacement_face) < 0) ||
		    (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager,
					    &replacement_font->scaler,
					    &replacement_font->size) < 0))
#else
		if (FTC_Manager_Lookup_Size(fontRenderClass::instance->cacheManager, 
				&replacement_font->font.font, &replacement_face, 
				&replacement_font->size)<0)
#endif
		{
			eDebug("FTC_Manager_Lookup_Size failed!");
			return;
		}
	}
	if (current_font)
	{
#ifdef HAVE_FREETYPE2
		if ((FTC_Manager_LookupFace(fontRenderClass::instance->cacheManager,
					    current_font->scaler.face_id,
					    &current_face) < 0) ||
		    (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager,
					    &current_font->scaler,
					    &current_font->size) < 0))
#else
		if (FTC_Manager_Lookup_Size(fontRenderClass::instance->cacheManager, &current_font->font.font, &current_face, &current_font->size)<0)
#endif
		{
			eDebug("FTC_Manager_Lookup_Size failed!");
			return;
		}
	}
#ifndef HAVE_FREETYPE2
	cache_current_font=&current_font->font.font;
#endif
	previous=0;
	use_kerning=FT_HAS_KERNING(current_face);
}

void
shape (std::vector<unsigned long> &string, const std::vector<unsigned long> &text);

int eTextPara::renderString(const char *string, int rflags)
{
	singleLock s(ftlock);
	
	if (!current_font)
		return -1;

#ifdef HAVE_FREETYPE2
	if ((FTC_Manager_LookupFace(fontRenderClass::instance->cacheManager,
 				    current_font->scaler.face_id,
 				    &current_face) < 0) ||
	    (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager,
				    &current_font->scaler,
				    &current_font->size) < 0))
	{
		eDebug("FTC_Manager_Lookup_Size failed!");
		return -1;
	}
#else
	if (&current_font->font.font != cache_current_font)
	{
		if (FTC_Manager_Lookup_Size(fontRenderClass::instance->cacheManager, &current_font->font.font, &current_face, &current_font->size)<0)
		{
			eDebug("FTC_Manager_Lookup_Size failed!");
			return -1;
		}
		cache_current_font=&current_font->font.font;
	}
#endif

	if (!current_face)
		eFatal("eTextPara::renderString: no current_face");
	if (!current_face->size)
		eFatal("eTextPara::renderString: no current_face->size");

	if (cursor.y()==-1)
	{
		cursor=ePoint(area.x(), area.y()+(current_face->size->metrics.ascender>>6));
		left=cursor.x();
	}

	std::vector<unsigned long> uc_string, uc_visual;
	if (string)
		uc_string.reserve(strlen(string));
	
	const char *p = string ? string : "";

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
		}
		uc_string.push_back(unicode);
	}

	std::vector<unsigned long> uc_shape;

		// character -> glyph conversion
	shape(uc_shape, uc_string);
	
		// now do the usual logical->visual reordering
	int size=uc_shape.size();
#ifdef HAVE_FRIBIDI
	FriBidiCharType dir=FRIBIDI_TYPE_ON;
	uc_visual.resize(size);
	// gaaanz lahm, aber anders geht das leider nicht, sorry.
	FriBidiChar array[size], target[size];
	std::copy(uc_shape.begin(), uc_shape.end(), array);
	fribidi_log2vis(array, size, &dir, target, 0, 0, 0);
	uc_visual.assign(target, target+size);
#else
	uc_visual=uc_shape;
#endif

	glyphs.reserve(size);
	
	int nextflags = 0;
	
	for (std::vector<unsigned long>::const_iterator i(uc_visual.begin());
		i != uc_visual.end(); ++i)
	{
		int isprintable=1;
		int flags = nextflags;
		nextflags = 0;
		unsigned long chr = *i;

		if (!(rflags&RS_DIRECT))
		{
			switch (chr)
			{
			case '\\':
			{
				unsigned long c = *(i+1);
				switch (c)
				{
					case 'n':
						i++;
						goto newline;
					case 't':
						i++;
						goto tab;
					case 'r':
						i++;
						goto nprint;
					default:
					;
				}
				break;
			}
			case '\t':
tab:		isprintable=0;
				cursor+=ePoint(current_font->tabwidth, 0);
				cursor-=ePoint(cursor.x()%current_font->tabwidth, 0);
				break;
			case 0x8A:
			case 0xE08A:
			case '\n':
newline:isprintable=0;
				newLine(rflags);
				nextflags|=GS_ISFIRST;
				break;
			case '\r':
			case 0x86: case 0xE086:
			case 0x87: case 0xE087:
nprint:	isprintable=0;
				break;
			case 0xAD: // soft-hyphen
				flags |= GS_SOFTHYPHEN;
				chr = 0x2010; /* hyphen */
				break;
			case 0x2010:
			case '-':
				flags |= GS_HYPHEN;
				break;
			case ' ':
				flags|=GS_ISSPACE;
			default:
				break;
			}
		}
		if (isprintable)
		{
			FT_UInt index = 0;

				/* FIXME: our font doesn't seem to have a hyphen, so use hyphen-minus for it. */
			if (chr == 0x2010)
				chr = '-';

			if (forced_replaces.find(chr) == forced_replaces.end())
				index=(rflags&RS_DIRECT)? chr : FT_Get_Char_Index(current_face, chr);

			if (!index)
			{
				if (replacement_face)
					index=(rflags&RS_DIRECT)? chr : FT_Get_Char_Index(replacement_face, chr);

				if (!index)
					eDebug("unicode U+%4lx not present", chr);
				else
					appendGlyph(replacement_font, replacement_face, index, flags, rflags);
			} else
				appendGlyph(current_font, current_face, index, flags, rflags);
		}
	}
	bboxValid=false;
	calc_bbox();
#ifdef HAVE_FRIBIDI
	if (dir & FRIBIDI_MASK_RTL)
	{
		realign(dirRight);
		doTopBottomReordering=true;
	}
#endif

	if (charCount)
	{
		lineOffsets.push_back(cursor.y());
		lineChars.push_back(charCount);
		charCount=0;
	}

	return 0;
}

void eTextPara::blit(gDC &dc, const ePoint &offset, const gRGB &background, const gRGB &foreground)
{
	singleLock s(ftlock);
	
	if (!current_font)
		return;

#ifdef HAVE_FREETYPE2
	if ((FTC_Manager_LookupFace(fontRenderClass::instance->cacheManager,
 				    current_font->scaler.face_id,
 				    &current_face) < 0) ||
	    (FTC_Manager_LookupSize(fontRenderClass::instance->cacheManager,
				    &current_font->scaler,
				    &current_font->size) < 0))
	{
		eDebug("FTC_Manager_Lookup_Size failed!");
		return;
	}
#else
	if (&current_font->font.font != cache_current_font)
	{
		if (FTC_Manager_Lookup_Size(fontRenderClass::instance->cacheManager, &current_font->font.font, &current_face, &current_font->size)<0)
		{
			eDebug("FTC_Manager_Lookup_Size failed!");
			return;
		}
		cache_current_font=&current_font->font.font;
	}
#endif

	ePtr<gPixmap> target;
	dc.getPixmap(target);
	gSurface *surface = target->surface;

	register int opcode;

	gColor *lookup8, lookup8_invert[16];
	gColor *lookup8_normal=0;

	__u16 lookup16_normal[16], lookup16_invert[16], *lookup16;
	__u32 lookup32_normal[16], lookup32_invert[16], *lookup32;

	if (surface->bpp == 8)
	{
		if (surface->clut.data)
		{
			lookup8_normal=getColor(surface->clut, background, foreground).lookup;
			
			int i;
			for (i=0; i<16; ++i)
				lookup8_invert[i] = lookup8_normal[i^0xF];
			
			opcode=0;
		} else
			opcode=1;
	} else if (surface->bpp == 16)
	{
		opcode=2;
		for (int i=0; i<16; ++i)
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
	} else if (surface->bpp == 32)
	{
		opcode=3;
		for (int i=0; i<16; ++i)
		{
#define BLEND(y, x, a) (y + (((x-y) * a)>>8))

			unsigned char da = background.a, dr = background.r, dg = background.g, db = background.b;
			int sa = i * 16;
			if (sa < 256)
			{
				da = BLEND(background.a, foreground.a, sa) & 0xFF;
				dr = BLEND(background.r, foreground.r, sa) & 0xFF;
				dg = BLEND(background.g, foreground.g, sa) & 0xFF;
				db = BLEND(background.b, foreground.b, sa) & 0xFF;
			}
#undef BLEND
			da ^= 0xFF;
			lookup32_normal[i]=db | (dg << 8) | (dr << 16) | (da << 24);;
		}
		for (int i=0; i<16; ++i)
			lookup32_invert[i]=lookup32_normal[i^0xF];
	} else
	{
		eWarning("can't render to %dbpp", surface->bpp);
		return;
	}

	gRegion area(eRect(0, 0, surface->x, surface->y));
	gRegion clip = dc.getClip() & area;

	int buffer_stride=surface->stride;

	for (unsigned int c = 0; c < clip.rects.size(); ++c)
	{
		std::list<int>::reverse_iterator line_offs_it(lineOffsets.rbegin());
		std::list<int>::iterator line_chars_it(lineChars.begin());
		int line_offs=0;
		int line_chars=0;
		for (glyphString::iterator i(glyphs.begin()); i != glyphs.end(); ++i, --line_chars)
		{
			while(!line_chars)
			{
				line_offs = *(line_offs_it++);
				line_chars = *(line_chars_it++);
			}

			if (i->flags & GS_SOFTHYPHEN)
				continue;

			if (!(i->flags & GS_INVERT))
			{
				lookup8 = lookup8_normal;
				lookup16 = lookup16_normal;
				lookup32 = lookup32_normal;
			} else
			{
				lookup8 = lookup8_invert;
				lookup16 = lookup16_invert;
				lookup32 = lookup32_invert;
			}

			static FTC_SBit glyph_bitmap;
			if (fontRenderClass::instance->getGlyphBitmap(&i->font->font, i->glyph_index, &glyph_bitmap))
				continue;
			int rx=i->x+glyph_bitmap->left + offset.x();
			int ry=(doTopBottomReordering ? line_offs : i->y) - glyph_bitmap->top + offset.y();

			__u8 *d=(__u8*)(surface->data)+buffer_stride*ry+rx*surface->bypp;
			__u8 *s=glyph_bitmap->buffer;
			register int sx=glyph_bitmap->width;
			int sy=glyph_bitmap->height;
			if ((sy+ry) >= clip.rects[c].bottom())
				sy=clip.rects[c].bottom()-ry;
			if ((sx+rx) >= clip.rects[c].right())
				sx=clip.rects[c].right()-rx;
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
				s+=diff*glyph_bitmap->pitch;
				sy-=diff;
				ry+=diff;
				d+=diff*buffer_stride;
			}
			if (sx>0)
			{
				switch(opcode) {
				case 0: // 4bit lookup to 8bit
					for (int ay=0; ay<sy; ay++)
					{
						register __u8 *td=d;
						register int ax;
						for (ax=0; ax<sx; ax++)
						{
							register int b=(*s++)>>4;
							if(b)
								*td++=lookup8[b];
							else
								td++;
						}
						s+=glyph_bitmap->pitch-sx;
						d+=buffer_stride;
					}
					break;
				case 1: // 8bit direct
					for (int ay=0; ay<sy; ay++)
					{
						register __u8 *td=d;
						register int ax;
						for (ax=0; ax<sx; ax++)
						{
							register int b=*s++;
							*td++^=b;
						}
						s+=glyph_bitmap->pitch-sx;
						d+=buffer_stride;
					}
					break;
				case 2: // 16bit
					for (int ay=0; ay<sy; ay++)
					{
						register __u16 *td=(__u16*)d;
						register int ax;
						for (ax=0; ax<sx; ax++)
						{
							register int b=(*s++)>>4;
							if(b)
								*td++=lookup16[b];
							else
								td++;
						}
						s+=glyph_bitmap->pitch-sx;
						d+=buffer_stride;
					}
					break;
				case 3: // 32bit
					for (int ay=0; ay<sy; ay++)
					{
						register __u32 *td=(__u32*)d;
						register int ax;
						for (ax=0; ax<sx; ax++)
						{
							register int b=(*s++)>>4;
							if(b)
								*td++=lookup32[b];
							else
								td++;
						}
						s+=glyph_bitmap->pitch-sx;
						d+=buffer_stride;
					}
				default:
					break;
				}
			}
		}
	}
}

void eTextPara::realign(int dir)	// der code hier ist ein wenig merkwuerdig.
{
	glyphString::iterator begin(glyphs.begin()), c(glyphs.begin()), end(glyphs.begin()), last;
	if (dir==dirLeft)
		return;
	while (c != glyphs.end())
	{
		int linelength=0;
		int numspaces=0, num=0;
		begin=end;
		
		ASSERT( end != glyphs.end());
		
			// zeilenende suchen
		do {
			last=end;
			++end;
		} while ((end != glyphs.end()) && (!(end->flags&GS_ISFIRST)));
			// end zeigt jetzt auf begin der naechsten zeile
		
		for (c=begin; c!=end; ++c)
		{
				// space am zeilenende skippen
			if ((c==last) && (c->flags&GS_ISSPACE))
				continue;

			if (c->flags&GS_ISSPACE)
				numspaces++;
			linelength+=c->w;
			num++;
		}

		switch (dir)
		{
		case dirRight:
		case dirCenter:
		{
			int offset=area.width()-linelength;
			if (dir==dirCenter)
				offset/=2;
			offset+=area.left();
			while (begin != end)
			{
				begin->bbox.moveBy(offset-begin->x,0);
				begin->x=offset;
				offset+=begin->w;
				++begin;
			}
			break;
		}
		case dirBlock:
		{
			if (end == glyphs.end())		// letzte zeile linksbuendig lassen
				continue;
			int spacemode;
			if (numspaces)
				spacemode=1;
			else
				spacemode=0;
			if ((!spacemode) && (num<2))
				break;
			int off=(area.width()-linelength)*256/(spacemode?numspaces:(num-1));
			int curoff=0;
			while (begin != end)
			{
				int doadd=0;
				if ((!spacemode) || (begin->flags&GS_ISSPACE))
					doadd=1;
				begin->x+=curoff>>8;
				begin->bbox.moveBy(curoff>>8,0);
				if (doadd)
					curoff+=off;
				++begin;
			}
			break;
		}
		}
	}
	bboxValid=false;
	calc_bbox();
}

void eTextPara::clear()
{
	singleLock s(ftlock);

	current_font = 0;
	replacement_font = 0;

	glyphs.clear();
}

eAutoInitP0<fontRenderClass> init_fontRenderClass(eAutoInitNumbers::graphic-1, "Font Render Class");
