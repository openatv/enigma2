#include <png.h>
#include <stdio.h>
#include <lib/gdi/epng.h>
#include <unistd.h>

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
	
	eDebug("%s: %dx%dx%d png, %d", filename, (int)width, (int)height, (int)bit_depth, color_type);
	
	if (color_type != 6)
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
		png_read_end(png_ptr, end_info);
	} else
		result=0;

	png_destroy_read_struct(&png_ptr, &info_ptr,&end_info);
	fclose(fp);
	return 0;
}

int savePNG(const char *filename, gPixmap *pixmap)
{
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

	png_set_IHDR(png_ptr, info_ptr, surface->x, surface->y, surface->bpp, 
		surface->clut.data ? PNG_COLOR_TYPE_PALETTE : PNG_COLOR_TYPE_GRAY, 
		PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);
	if (surface->clut.data)
	{
		png_color palette[surface->clut.colors];
		png_byte trans[surface->clut.colors];
		for (int i=0; i<surface->clut.colors; ++i)
		{
			palette[i].red=surface->clut.data[i].r;
			palette[i].green=surface->clut.data[i].g;
			palette[i].blue=surface->clut.data[i].b;
			trans[i]=255-surface->clut.data[i].a;
		}
		png_set_PLTE(png_ptr, info_ptr, palette, surface->clut.colors);
		png_set_tRNS(png_ptr, info_ptr, trans, surface->clut.colors, 0);
	}
	png_write_info(png_ptr, info_ptr);
	png_set_packing(png_ptr);
	png_byte *row_pointers[surface->y];
	for (int i=0; i<surface->y; ++i)
		row_pointers[i]=((png_byte*)surface->data)+i*surface->stride;
	png_write_image(png_ptr, row_pointers);
	png_write_end(png_ptr, info_ptr);
	png_destroy_write_struct(&png_ptr, &info_ptr);
	fclose(fp);
	eDebug("wrote png ! fine !");
	return 0;
}
