#include <png.h>
#include <stdio.h>
#include <lib/gdi/epng.h>
#include <unistd.h>

extern "C" {
#include <jpeglib.h>
}

int loadPNG(ePtr<gPixmap> &result, const char *filename)
{
	__u8 header[8];
	FILE *fp=fopen(filename, "rb");
	
	if (!fp)
	{
//		eDebug("couldn't open %s", filename );
		return 0;
	}
	if (!fread(header, 8, 1, fp))
	{
		eDebug("couldn't read");
		fclose(fp);
		return 0;
	}
	if (png_sig_cmp(header, 0, 8))
	{
		fclose(fp);
		return 0;
	}
	png_structp png_ptr=png_create_read_struct(PNG_LIBPNG_VER_STRING, 0, 0, 0);
	if (!png_ptr)
	{
		eDebug("no pngptr");
		fclose(fp);
		return 0;
	}
	png_infop info_ptr=png_create_info_struct(png_ptr);
	if (!info_ptr)
	{
		eDebug("no info ptr");
		png_destroy_read_struct(&png_ptr, (png_infopp)0, (png_infopp)0);
		fclose(fp);
		return 0;
	}
	png_infop end_info = png_create_info_struct(png_ptr);
	if (!end_info)
	{
		eDebug("no end");
		png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);
		fclose(fp);
		return 0;
	 }
	if (setjmp(png_ptr->jmpbuf))
	{
		eDebug("das war wohl nix");
		png_destroy_read_struct(&png_ptr, &info_ptr, &end_info);
		fclose(fp);
		result = 0;
		return 0;
	}
	png_init_io(png_ptr, fp);
	png_set_sig_bytes(png_ptr, 8);
	png_set_invert_alpha(png_ptr);
	png_read_info(png_ptr, info_ptr);
	
	png_uint_32 width, height;
	int bit_depth;
	int color_type;
	
	png_get_IHDR(png_ptr, info_ptr, &width, &height, &bit_depth, &color_type, 0, 0, 0);
	
	if (color_type == PNG_COLOR_TYPE_GRAY || color_type & PNG_COLOR_MASK_PALETTE)
	{
		result=new gPixmap(eSize(width, height), bit_depth);
		gSurface *surface = result->surface;
	
		png_bytep *rowptr=new png_bytep[height];
	
		for (unsigned int i=0; i<height; i++)
			rowptr[i]=((png_byte*)(surface->data))+i*surface->stride;
		png_read_rows(png_ptr, rowptr, 0, height);
	
		delete [] rowptr;
	
		if (png_get_valid(png_ptr, info_ptr, PNG_INFO_PLTE))
		{
			png_color *palette;
			int num_palette;
			png_get_PLTE(png_ptr, info_ptr, &palette, &num_palette);
			if (num_palette)
				surface->clut.data=new gRGB[num_palette];
			else
				surface->clut.data=0;
			surface->clut.colors=num_palette;
			
			for (int i=0; i<num_palette; i++)
			{
				surface->clut.data[i].a=0;
				surface->clut.data[i].r=palette[i].red;
				surface->clut.data[i].g=palette[i].green;
				surface->clut.data[i].b=palette[i].blue;
			}
			if (png_get_valid(png_ptr, info_ptr, PNG_INFO_tRNS))
			{
				png_byte *trans;
				png_get_tRNS(png_ptr, info_ptr, &trans, &num_palette, 0);
				for (int i=0; i<num_palette; i++)
					surface->clut.data[i].a=255-trans[i];
			}
		} else
		{
			surface->clut.data=0;
			surface->clut.colors=0;
		}
		surface->clut.start=0;
		png_read_end(png_ptr, end_info);
	} else {
		result=0;
		eDebug("%s: %dx%dx%d png, %d", filename, (int)width, (int)height, (int)bit_depth, color_type);
	}

	png_destroy_read_struct(&png_ptr, &info_ptr,&end_info);
	fclose(fp);
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
	FILE *infile;
	JSAMPARRAY buffer;
	int row_stride;
	infile = fopen(filename, "rb");
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
		fclose(infile);
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
			int x;
			for (x = 0; x < (int)cinfo.output_width; ++x)
			{
				*dst++ = src[2];
				*dst++ = src[1];
				*dst++ = src[0];
				src += 3;
				if (palpha)
					*dst++ = *palpha++;
				else 
					*dst++ = 0xFF;
			}
		}
	}
	(void) jpeg_finish_decompress(&cinfo);
	jpeg_destroy_decompress(&cinfo);
	fclose(infile);
	return 0;
}

int savePNG(const char *filename, gPixmap *pixmap)
{

	eDebug("\33[33m %s \33[0m",filename);
	FILE *fp=fopen(filename, "wb");
	if (!fp)
		return -1;
	
	gSurface *surface = pixmap->surface;
	if (!surface)
		return -2;
	
	png_structp png_ptr=png_create_write_struct(PNG_LIBPNG_VER_STRING, 0, 0, 0);
	if (!png_ptr)
	{
		eDebug("write png, couldnt allocate write struct");
		fclose(fp);
		unlink(filename);
		return -2;
	}
	png_infop info_ptr=png_create_info_struct(png_ptr);
	if (!info_ptr)
	{
		eDebug("info");
		png_destroy_write_struct(&png_ptr, 0);
		fclose(fp);
		unlink(filename);
		return -3;
	}

	png_set_IHDR(png_ptr, info_ptr, surface->x, surface->y, surface->bpp/surface->bypp, 
		PNG_COLOR_TYPE_RGB_ALPHA, 
		PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);

	if (setjmp(png_ptr->jmpbuf))
	{
		eDebug("error :/");
		png_destroy_write_struct(&png_ptr, &info_ptr);
		fclose(fp);
		unlink(filename);
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
		printf("Error: malloc\n");
		return -5;
	}
	for (int i=0; i<surface->y; ++i)
	{
		row_pointer=((png_byte*)surface->data)+i*surface->stride;
		if (surface->bypp == 4)
		{
			memcpy(cr, row_pointer, surface->stride);
			for (int j=0; j<surface->stride; j+=4)
			{
				unsigned char tmp = cr[j];
				cr[j] = cr[j+2];
				cr[j+2]= tmp;
			}
			png_write_row(png_ptr, cr);
		}
		else
			png_write_row(png_ptr, row_pointer);
	}
	delete [] cr;

	png_write_end(png_ptr, info_ptr);
	png_destroy_write_struct(&png_ptr, &info_ptr);
	fclose(fp);
	eDebug("wrote png ! fine !");
	return 0;
}
