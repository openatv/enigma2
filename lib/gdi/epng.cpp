#define PNG_SKIP_SETJMP_CHECK
#include <zlib.h>
#include <png.h>
#include <stdio.h>
#include <lib/base/cfile.h>
#include <lib/gdi/epng.h>
#include <unistd.h>

#include <map>
#include <string>
#include <lib/base/elock.h>

extern "C" {
#include <jpeglib.h>
}

/* TODO: I wonder why this function ALWAYS returns 0 */
int loadPNG(ePtr<gPixmap> &result, const char *filename, int accel)
{
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

	result = new gPixmap(eSize(width, height), bit_depth * channels, accel);
	gUnmanagedSurface *surface = result->surface;

	png_bytep *rowptr = new png_bytep[height];
	for (unsigned int i = 0; i < height; i++)
		rowptr[i] = ((png_byte*)(surface->data)) + i * surface->stride;
	png_read_image(png_ptr, rowptr);

	delete [] rowptr;

	int num_palette = -1, num_trans = -1;
	if (color_type == PNG_COLOR_TYPE_PALETTE) {
		if (png_get_valid(png_ptr, info_ptr, PNG_INFO_PLTE)) {
			png_color *palette;
			png_get_PLTE(png_ptr, info_ptr, &palette, &num_palette);
			if (num_palette)
				surface->clut.data = new gRGB[num_palette];
			else
				surface->clut.data = 0;
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
			surface->clut.colors = 0;
		}
		surface->clut.start = 0;
	}
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

int loadJPG(ePtr<gPixmap> &result, const char *filename, ePtr<gPixmap> alpha)
{
	struct jpeg_decompress_struct cinfo;
	struct my_error_mgr jerr;
	JSAMPARRAY buffer;
	int row_stride;
	CFile infile(filename, "rb");
	result = 0;

	if (alpha)
	{
		if (alpha->surface->bpp != 8)
		{
			eWarning("alpha channel for jpg must be 8bit");
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
			eWarning("alpha channel size (%dx%d) must match jpeg size (%dx%d)", alpha->surface->x, alpha->surface->y, cinfo.output_width, cinfo.output_height);
			alpha = 0;
		}
		if (grayscale)
		{
			eWarning("we don't support grayscale + alpha at the moment");
			alpha = 0;
		}
	}

	result = new gPixmap(eSize(cinfo.output_width, cinfo.output_height), grayscale ? 8 : 32);

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
