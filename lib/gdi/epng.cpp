#define PNG_SKIP_SETJMP_CHECK
#include <zlib.h>
#include <png.h>
#include <stdio.h>
#include <lib/base/cfile.h>
#include <lib/base/wrappers.h>
#include <lib/gdi/epng.h>
#include <lib/gdi/pixmapcache.h>
#include <unistd.h>
#include <lib/base/estring.h>

#include <map>
#include <string>
#include <lib/base/elock.h>

extern "C" {
#include <jpeglib.h>
#include <gif_lib.h>
}

#include <nanosvg.h>
#include <nanosvgrast.h>

/* TODO: I wonder why this function ALWAYS returns 0 */
int loadPNG(ePtr<gPixmap> &result, const char *filename, int accel, int cached)
{
	if (cached && (result = PixmapCache::Get(filename)))
		return 0;

	CFile fp(filename, "rb");

	if (!fp)
	{
		eDebug("[ePNG] couldn't open %s", filename );
		return 0;
	}
	{
		__u8 header[8];
		if (!fread(header, 8, 1, fp))
		{
			eDebug("[ePNG] failed to get png header");
			return 0;
		}
		if (png_sig_cmp(header, 0, 8))
		{
			eDebug("[ePNG] header size mismatch");
			return 0;
		}
	}
	png_structp png_ptr = png_create_read_struct(PNG_LIBPNG_VER_STRING, 0, 0, 0);
	if (!png_ptr)
	{
		eDebug("[ePNG] failed to create read struct");
		return 0;
	}
	png_infop info_ptr = png_create_info_struct(png_ptr);
	if (!info_ptr)
	{
		eDebug("[ePNG] failed to create info struct");
		png_destroy_read_struct(&png_ptr, (png_infopp)0, (png_infopp)0);
		return 0;
	}
	png_infop end_info = png_create_info_struct(png_ptr);
	if (!end_info)
	{
		eDebug("[ePNG] failed to create end info struct");
		png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);
		return 0;
	}
	if (setjmp(png_jmpbuf(png_ptr)))
	{
		eDebug("[ePNG] png setjump failed or activated");
		png_destroy_read_struct(&png_ptr, &info_ptr, &end_info);
		result = 0;
		return 0;
	}
	png_init_io(png_ptr, fp);
	png_set_sig_bytes(png_ptr, 8);
	png_read_info(png_ptr, info_ptr);

	png_uint_32 width, height;
	int bit_depth;
	int color_type;
	int interlace_type;
	int channels;
	int trns;

	png_get_IHDR(png_ptr, info_ptr, &width, &height, &bit_depth, &color_type, &interlace_type, 0, 0);
	channels = png_get_channels(png_ptr, info_ptr);
	trns = png_get_valid(png_ptr, info_ptr, PNG_INFO_tRNS);
	//eDebug("[ePNG] %s: before %dx%dx%dbpcx%dchan coltyp=%d", filename, (int)width, (int)height, bit_depth, channels, color_type);

	/*
	 * gPixmaps use 8 bits per channel. rgb pixmaps are stored as abgr.
	 * So convert 1,2 and 4 bpc to 8bpc images that enigma can blit
	 * so add 'empty' alpha channel
	 * Expand G+tRNS to GA, RGB+tRNS to RGBA
	 */
	if (bit_depth == 16)
		png_set_strip_16(png_ptr);
	if (bit_depth < 8)
		png_set_packing (png_ptr);

	if (color_type == PNG_COLOR_TYPE_GRAY && bit_depth < 8)
		png_set_expand_gray_1_2_4_to_8(png_ptr);
	if (color_type == PNG_COLOR_TYPE_GRAY && trns)
		png_set_tRNS_to_alpha(png_ptr);
	if ((color_type == PNG_COLOR_TYPE_GRAY && trns) || color_type == PNG_COLOR_TYPE_GRAY_ALPHA) {
		png_set_gray_to_rgb(png_ptr);
		png_set_bgr(png_ptr);
	}

	if (color_type == PNG_COLOR_TYPE_RGB) {
		if (trns)
			png_set_tRNS_to_alpha(png_ptr);
		else
			png_set_add_alpha(png_ptr, 255, PNG_FILLER_AFTER);
	}

	if (color_type == PNG_COLOR_TYPE_RGB || color_type == PNG_COLOR_TYPE_RGB_ALPHA)
		png_set_bgr(png_ptr);

	// Update the info structures after the transformations take effect
	if (interlace_type != PNG_INTERLACE_NONE)
		png_set_interlace_handling(png_ptr);  // needed before read_update_info()
	png_read_update_info (png_ptr, info_ptr);
	png_get_IHDR(png_ptr, info_ptr, &width, &height, &bit_depth, &color_type, 0, 0, 0);
	channels = png_get_channels(png_ptr, info_ptr);

	result = new gPixmap(width, height, bit_depth * channels, cached ? PixmapCache::PixmapDisposed : NULL, accel);
	gUnmanagedSurface *surface = result->surface;
	
	png_bytep *rowptr = new png_bytep[height];
	for (unsigned int i = 0; i < height; i++)
		rowptr[i] = ((png_byte*)(surface->data)) + i * surface->stride;
	png_read_image(png_ptr, rowptr);

	delete [] rowptr;

	if (color_type == PNG_COLOR_TYPE_RGBA || color_type == PNG_COLOR_TYPE_GA)
		surface->transparent = true;
	else
	{
		png_bytep trans_alpha = NULL;
		int num_trans = 0;
		png_color_16p trans_color = NULL;

		png_get_tRNS(png_ptr, info_ptr, &trans_alpha, &num_trans, &trans_color);
		surface->transparent = (trans_alpha != NULL);
	}
	
	int num_palette = -1, num_trans = -1;
	if (color_type == PNG_COLOR_TYPE_PALETTE) {
		if (png_get_valid(png_ptr, info_ptr, PNG_INFO_PLTE)) {
			png_color *palette;
			png_get_PLTE(png_ptr, info_ptr, &palette, &num_palette);
			if (num_palette) {
				surface->clut.data = new gRGB[num_palette];
				surface->clut.colors = num_palette;

				for (int i = 0; i < num_palette; i++) {
					surface->clut.data[i].a = 0;
					surface->clut.data[i].r = palette[i].red;
					surface->clut.data[i].g = palette[i].green;
					surface->clut.data[i].b = palette[i].blue;
				}

				if (trns) {
					png_byte *trans;
					png_get_tRNS(png_ptr, info_ptr, &trans, &num_trans, 0);
					for (int i = 0; i < num_trans; i++)
						surface->clut.data[i].a = 255 - trans[i];
					for (int i = num_trans; i < num_palette; i++)
						surface->clut.data[i].a = 0;
				}

			}
			else {
				surface->clut.data = 0;
				surface->clut.colors = num_palette;
			}
		}
		else {
			surface->clut.data = 0;
			surface->clut.colors = 0;
		}
		surface->clut.start = 0;
	}

	if (cached)
		PixmapCache::Set(filename, result);

	//eDebug("[ePNG] %s: after  %dx%dx%dbpcx%dchan coltyp=%d cols=%d trans=%d", filename, (int)width, (int)height, bit_depth, channels, color_type, num_palette, num_trans);

	png_read_end(png_ptr, end_info);
	png_destroy_read_struct(&png_ptr, &info_ptr, &end_info);
	return 0;
}

struct my_error_mgr {
	struct jpeg_error_mgr pub;
	jmp_buf setjmp_buffer;
};

typedef struct my_error_mgr * my_error_ptr;

static void
my_error_exit (j_common_ptr cinfo)
{
	my_error_ptr myerr = (my_error_ptr) cinfo->err;
	(*cinfo->err->output_message) (cinfo);
	longjmp(myerr->setjmp_buffer, 1);
}

int loadJPG(ePtr<gPixmap> &result, const char *filename, int cached)
{
	return loadJPG(result, filename, ePtr<gPixmap>(), cached);
}

int loadJPG(ePtr<gPixmap> &result, const char *filename, ePtr<gPixmap> alpha, int cached)
{
	if (cached && (result = PixmapCache::Get(filename)))
		return 0;

	struct jpeg_decompress_struct cinfo = {};
	struct my_error_mgr jerr = {};
	JSAMPARRAY buffer;
	int row_stride;
	CFile infile(filename, "rb");
	result = 0;

	if (alpha)
	{
		if (alpha->surface->bpp != 8)
		{
			eWarning("[loadJPG] alpha channel for jpg must be 8bit");
			alpha = 0;
		}
	}

	if (!infile)
		return -1;
	cinfo.err = jpeg_std_error(&jerr.pub);
	jerr.pub.error_exit = my_error_exit;
	if (setjmp(jerr.setjmp_buffer)) {
		result = 0;
		jpeg_destroy_decompress(&cinfo);
		return -1;
	}
	jpeg_create_decompress(&cinfo);
	jpeg_stdio_src(&cinfo, infile);
	(void) jpeg_read_header(&cinfo, TRUE);
	cinfo.out_color_space = JCS_RGB;
	cinfo.scale_denom = 1;

	(void) jpeg_start_decompress(&cinfo);

	int grayscale = cinfo.output_components == 1;

	if (alpha)
	{
		if (((int)cinfo.output_width != alpha->surface->x) || ((int)cinfo.output_height != alpha->surface->y))
		{
			eWarning("[loadJPG] alpha channel size (%dx%d) must match jpeg size (%dx%d)", alpha->surface->x, alpha->surface->y, cinfo.output_width, cinfo.output_height);
			alpha = 0;
		}
		if (grayscale)
		{
			eWarning("[loadJPG] we don't support grayscale + alpha at the moment");
			alpha = 0;
		}
	}

	result = new gPixmap(cinfo.output_width, cinfo.output_height, grayscale ? 8 : 32, cached ? PixmapCache::PixmapDisposed : NULL);
	result->surface->transparent = false;
	row_stride = cinfo.output_width * cinfo.output_components;
	buffer = (*cinfo.mem->alloc_sarray)((j_common_ptr) &cinfo, JPOOL_IMAGE, row_stride, 1);
	while (cinfo.output_scanline < cinfo.output_height) {
		int y = cinfo.output_scanline;
		(void) jpeg_read_scanlines(&cinfo, buffer, 1);
		unsigned char *dst = ((unsigned char*)result->surface->data) + result->surface->stride * y;
		unsigned char *src = (unsigned char*)buffer[0];
		unsigned char *palpha = alpha ? ((unsigned char*)alpha->surface->data + alpha->surface->stride * y) : 0;
		if (grayscale)
			memcpy(dst, src, cinfo.output_width);
		else
		{
			if (palpha)
			{
				for (int x = (int)cinfo.output_width; x != 0; --x)
				{
					*dst++ = src[2];
					*dst++ = src[1];
					*dst++ = src[0];
					*dst++ = *palpha++;
					src += 3;
				}
			}
			else
			{
				for (int x = (int)cinfo.output_width; x != 0; --x)
				{
					*dst++ = src[2];
					*dst++ = src[1];
					*dst++ = src[0];
					*dst++ = 0xFF;
					src += 3;
				}
			}
		}
	}

	if (cached)
		PixmapCache::Set(filename, result);

	(void) jpeg_finish_decompress(&cinfo);
	jpeg_destroy_decompress(&cinfo);
	return 0;
}

static int savePNGto(FILE *fp, gPixmap *pixmap)
{
	gUnmanagedSurface *surface = pixmap->surface;
	if (!surface)
		return -2;

	png_structp png_ptr = png_create_write_struct(PNG_LIBPNG_VER_STRING, 0, 0, 0);
	if (!png_ptr)
	{
		eDebug("[ePNG] couldn't allocate write struct");
		return -2;
	}
	png_infop info_ptr = png_create_info_struct(png_ptr);
	if (!info_ptr)
	{
		eDebug("[ePNG] failed to allocate info struct");
		png_destroy_write_struct(&png_ptr, 0);
		return -3;
	}

	png_set_IHDR(png_ptr, info_ptr, surface->x, surface->y, surface->bpp/surface->bypp,
		PNG_COLOR_TYPE_RGB_ALPHA,
		PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);

	if (setjmp(png_jmpbuf(png_ptr)))
	{
		eDebug("[ePNG] png setjump failed or activated");
		png_destroy_write_struct(&png_ptr, &info_ptr);
		return -4;
	}
	png_init_io(png_ptr, fp);
	png_set_filter(png_ptr, 0, PNG_FILTER_NONE|PNG_FILTER_SUB|PNG_FILTER_PAETH);
	png_set_compression_level(png_ptr, Z_BEST_COMPRESSION);

	png_write_info(png_ptr, info_ptr);
	png_set_packing(png_ptr);

	png_byte *row_pointer;
	png_byte *cr = new png_byte[surface->y * surface->stride];
	if (cr == NULL)
	{
		eDebug("[ePNG] failed to allocate memory image");
		return -5;
	}
	for (int i = 0; i < surface->y; ++i)
	{
		row_pointer = ((png_byte*)surface->data) + i * surface->stride;
		if (surface->bypp == 4)
		{
			memcpy(cr, row_pointer, surface->stride);
			for (int j = 0; j < surface->stride; j += 4)
			{
				unsigned char tmp = cr[j];
				cr[j] = cr[j+2];
				cr[j+2] = tmp;
			}
			png_write_row(png_ptr, cr);
		}
		else
			png_write_row(png_ptr, row_pointer);
	}
	delete [] cr;

	png_write_end(png_ptr, info_ptr);
	png_destroy_write_struct(&png_ptr, &info_ptr);
	return 0;
}

int loadSVG(ePtr<gPixmap> &result, const char *filename, int cached, int width, int height, float scale, int keepAspect, int align)
{
	result = nullptr;
	int size = 0;

	if (height > 0)
		size = height;
	else if (scale > 0)
		size = (int)(scale * 10);

	char cachefile[strlen(filename) + 10];
	sprintf(cachefile, "%s%d", filename, size);

	if (cached && (result = PixmapCache::Get(cachefile)))
		return 0;

	NSVGimage *image = nullptr;
	NSVGrasterizer *rast = nullptr;
	double xscale = 1.0;
	double yscale = 1.0;
	double tx = 0.0;
	double ty = 0.0;

	image = nsvgParseFromFile(filename, "px", 96.0);
	if (image == nullptr)
		return 0;

	rast = nsvgCreateRasterizer();
	if (rast == nullptr)
	{
		nsvgDelete(image);
		return 0;
	}

	if (width > 0 && height > 0 && keepAspect) {
		double sourceWidth = image->width;
		double sourceHeight = image->height;
		double widthScale = 0, heightScale = 0;
		if (sourceWidth > 0)
			widthScale = (double)width / sourceWidth;
		if (sourceHeight > 0)
			heightScale = (double)height / sourceHeight;

		double scale = std::min(widthScale, heightScale);
		yscale = scale;
		xscale = scale;
		int new_width = (int)(image->width * xscale);
		int new_height = (int)(image->height * scale);
		if (align == 2) tx = width - new_width; // Right alignment
		else if (align == 4) tx = (int)(((double)(width - new_width))/2); // Center alignment
		ty = (int)(((double)(height - new_height))/2);
	} else {
		if (height > 0)
			yscale = ((double) height) / image->height;

		if (width > 0)
		{
			xscale = ((double) width) / image->width;
			if (height <= 0)
			{
				yscale = xscale;
				height = (int)(image->height * yscale);
			}
		}
		else if (height > 0)
		{
			xscale = yscale;
			width = (int)(image->width * xscale);
		}
		else if (scale > 0)
		{
			xscale = (double) scale;
			yscale = (double) scale;
			width = (int)(image->width * scale);
			height = (int)(image->height * scale);
		}
		else
		{
			width = (int)image->width;
			height = (int)image->height;
		}
	}

	result = new gPixmap(width, height, 32, cached ? PixmapCache::PixmapDisposed : NULL, -1);
	if (result == nullptr)
	{
		nsvgDeleteRasterizer(rast);
		nsvgDelete(image);
		return 0;
	}

	eDebug("[ePNG] loadSVG %s %dx%d from %dx%d", filename, width, height, (int)image->width, (int)image->height);
	// Rasterizes SVG image, returns RGBA image (non-premultiplied alpha)
	nsvgRasterizeFull(rast, image, tx, ty, xscale, yscale, (unsigned char*)result->surface->data, width, height, width * 4, 1);

	if (cached)
		PixmapCache::Set(cachefile, result);

	nsvgDeleteRasterizer(rast);
	nsvgDelete(image);

	return 0;
}

int loadImage(ePtr<gPixmap> &result, const char *filename, int accel, int width, int height, int cached, float scale, int keepAspect, int align)
{
	if (endsWith(filename, ".png"))
		return loadPNG(result, filename, accel, cached == -1 ? 1 : cached);
	else if (endsWith(filename, ".svg"))
		return loadSVG(result, filename, cached == -1 ? 1 : cached, width, height, scale, keepAspect, align);
	else if (endsWith(filename, ".jpg"))
		return loadJPG(result, filename, cached == -1 ? 0 : cached);
	else if (endsWith(filename, ".gif"))
		return loadGIF(result, filename, accel, cached == -1 ? 0 : cached);
	return 0;
}

int savePNG(const char *filename, gPixmap *pixmap)
{
	int result;
	{
		eDebug("[ePNG] saving to %s",filename);
		CFile fp(filename, "wb");
		if (!fp)
			return -1;
		result = savePNGto(fp, pixmap);
	}
	if (result != 0)
		::unlink(filename);
	return result;
}

static void loadGIFFile(GifFile* filepara)
{
	unsigned char *pic_buffer = NULL;
	int px, py, i, j;
	unsigned char *fbptr;
	unsigned char *slb=NULL;
	GifFileType *gft;
	GifRecordType rt;
	GifByteType *extension;
	ColorMapObject *cmap;
	int cmaps;
	int extcode;

#if !defined(GIFLIB_MAJOR) || ( GIFLIB_MAJOR < 5)
	gft = DGifOpenFileName(filepara->file);
#else
	{
		int err;
		gft = DGifOpenFileName(filepara->file, &err);
	}
#endif
	if (gft == NULL)
		return;
	do
	{
		if (DGifGetRecordType(gft, &rt) == GIF_ERROR)
			goto ERROR_R;
		switch(rt)
		{
			case IMAGE_DESC_RECORD_TYPE:
				if (DGifGetImageDesc(gft) == GIF_ERROR)
					goto ERROR_R;
				filepara->ox = px = gft->Image.Width;
				filepara->oy = py = gft->Image.Height;
				pic_buffer = new unsigned char[px * py];
				filepara->pic_buffer = pic_buffer;
				slb = pic_buffer;

				if (pic_buffer != NULL)
				{
					cmap = (gft->Image.ColorMap ? gft->Image.ColorMap : gft->SColorMap);
					cmaps = cmap->ColorCount;
					filepara->palette_size = cmaps;
					filepara->palette = new gRGB[cmaps];
					for (i = 0; i != cmaps; ++i)
					{
						filepara->palette[i].a = 0;
						filepara->palette[i].r = cmap->Colors[i].Red;
						filepara->palette[i].g = cmap->Colors[i].Green;
						filepara->palette[i].b = cmap->Colors[i].Blue;
					}

					fbptr = pic_buffer;
					if (!(gft->Image.Interlace))
					{
						for (i = 0; i < py; i++, fbptr += px * 3)
						{
							if (DGifGetLine(gft, slb, px) == GIF_ERROR)
								goto ERROR_R;
							slb += px;
						}
					}
					else
					{
						for (j = 0; j < 4; j++)
						{
							slb = pic_buffer;
							for (i = 0; i < py; i++)
							{
								if (DGifGetLine(gft, slb, px) == GIF_ERROR)
									goto ERROR_R;
								slb += px;
							}
						}
					}
				}
				break;
			case EXTENSION_RECORD_TYPE:
				if (DGifGetExtension(gft, &extcode, &extension) == GIF_ERROR)
					goto ERROR_R;
				while (extension != NULL)
					if (DGifGetExtensionNext(gft, &extension) == GIF_ERROR)
						goto ERROR_R;
				break;
			default:
				break;
		}
	}
	while (rt != TERMINATE_RECORD_TYPE);

#if !defined(GIFLIB_MAJOR) || ( GIFLIB_MAJOR < 5) || (GIFLIB_MAJOR == 5 && GIFLIB_MINOR == 0)
	DGifCloseFile(gft);
#else
	{
		int err;
		DGifCloseFile(gft, &err);
	}
#endif
	return;
ERROR_R:
	eDebug("[loadGIFFile] <Error gif>");
#if !defined(GIFLIB_MAJOR) || ( GIFLIB_MAJOR < 5) || (GIFLIB_MAJOR == 5 && GIFLIB_MINOR == 0)
	DGifCloseFile(gft);
#else
	{
		int err;
		DGifCloseFile(gft, &err);
	}
#endif
}

int loadGIF(ePtr<gPixmap> &result, const char *filename, int accel,int cached)
{

	if (cached && (result = PixmapCache::Get(filename)))
		return 0;

	GifFile * m_filepara = new GifFile(filename);

	loadGIFFile(m_filepara);

	if(m_filepara->pic_buffer == NULL)
	{
		delete m_filepara;
		m_filepara = NULL;
		result = 0;
		return 0;
	}

	result = new gPixmap(m_filepara->ox, m_filepara->oy, 8, cached ? PixmapCache::PixmapDisposed : NULL, accel);
	gUnmanagedSurface *surface = result->surface;
	surface->clut.data = m_filepara->palette;
	surface->clut.colors = m_filepara->palette_size;
	m_filepara->palette = NULL; // transfer ownership
	int extra_stride = surface->stride - surface->x;

	unsigned char *tmp_buffer=((unsigned char *)(surface->data));
	unsigned char *origin = m_filepara->pic_buffer;

	gColor background;
	gRGB bg(0,0,0,255);
	//gRGB bg(m_conf.background);
	background = surface->clut.findColor(bg);

	for(int a = m_filepara->oy; a > 0; --a)
	{

		memcpy(tmp_buffer, origin, m_filepara->ox);
		tmp_buffer += m_filepara->ox;
		origin += m_filepara->ox;
		tmp_buffer += extra_stride;
	}

	if (cached)
		PixmapCache::Set(filename, result);

	delete m_filepara;
	m_filepara = NULL;
	return 0;
}

