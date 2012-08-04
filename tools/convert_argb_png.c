/*
     convert_argb_png.c
     
   compile with:
     
     gcc convert_argb_png.c -o convert_argb_png -lpng -ljpeg
    
   this tool takes a 32bit RGB+A PNG file, for example produced by photoshop,
   and splits the data into RGB and A. The RGB data is then lossy compressed with JPEG,
   the alpha channel is lossless compressed as PNG.

   enigma2 can then pickup those two files, and combine them on load. This gives
   the possibilty to use truecolor RGB pictures without storing them lossless
   (which would be inefficient). 
 */

#include <stdio.h>
#include <stdlib.h>
#include <png.h>
#include <assert.h>
#include <jpeglib.h>

int main(int argc, char **argv)
{
	if (argc != 4)
	{
		fprintf(stderr, "usage: %s <input.png> <output_basename> <jpeg-quality>\n", *argv);
		return 1;
	}

	const char *infile = argv[1];
	const char *outfile = argv[2];
	int jpeg_quality = atoi(argv[3]);

	FILE *fpin = fopen(infile, "rb");
	if (!fpin)
	{
		perror(infile);
		return 1;
	}

	unsigned char header[8];
	fread(header, 1, 8, fpin);
	if (png_sig_cmp(header, 0, 8))
	{
		fprintf(stderr, "this is not a PNG file\n");
		return 1;
	}
	png_structp png_ptr = png_create_read_struct
		(PNG_LIBPNG_VER_STRING, 0, 0, 0);
	assert(png_ptr);

	png_infop info_ptr = png_create_info_struct(png_ptr);
	assert(info_ptr);

	png_infop end_info = png_create_info_struct(png_ptr);
	assert (end_info);

	if (setjmp(png_jmpbuf(png_ptr)))
	{
		png_destroy_read_struct(&png_ptr, &info_ptr, &end_info);
		fclose(fpin);
		fprintf(stderr, "failed.\n");
		return 1;
	}

	png_init_io(png_ptr, fpin);
	png_set_sig_bytes(png_ptr, 8);
	png_read_png(png_ptr, info_ptr, PNG_TRANSFORM_IDENTITY, 0);
	png_bytep * row_pointers = png_get_rows(png_ptr, info_ptr);

	png_uint_32 width, height;
	int bit_depth, color_type;
	png_get_IHDR(png_ptr, info_ptr, &width, &height, 
		&bit_depth, &color_type, 0, 0, 0);

	if (color_type != PNG_COLOR_TYPE_RGB_ALPHA)
	{
		fprintf(stderr, "input PNG must be RGB+Alpha\n");
		return 1;
	}
	if (bit_depth != 8)
	{
		fprintf(stderr, "input bit depth must be 8bit!\n");
		return 1;
	}
	printf("png is %ldx%ld\n", width, height);
	int channels = png_get_channels(png_ptr, info_ptr);
	if (channels != 4)
	{
		fprintf(stderr, "channels must be 4.\n");
		return 1;
	}

		/* now write jpeg */
	struct jpeg_compress_struct cinfo;
	struct jpeg_error_mgr jerr;
	JSAMPROW jrow_pointer[1];
	FILE *outfp;

	char filename[strlen(outfile) + 10];
	strcpy(filename, outfile);
	strcat(filename, ".rgb.jpg");

	outfp = fopen(filename, "wb");
	if (!outfp)
	{
		perror(filename);
		return 1;
	}

	cinfo.err = jpeg_std_error(&jerr);
	jpeg_create_compress(&cinfo);
	jpeg_stdio_dest(&cinfo, outfp);

	cinfo.image_width = width;
	cinfo.image_height = height;
	cinfo.input_components = 3;
	cinfo.in_color_space = JCS_RGB;
	jpeg_set_defaults(&cinfo);
	jpeg_set_quality(&cinfo, jpeg_quality, 1);
	jpeg_start_compress(&cinfo, 1);

	unsigned char *row = malloc(width * 3);
	while (cinfo.next_scanline < cinfo.image_height)
	{
		int x;
		jrow_pointer[0] = row;
		unsigned char *source = row_pointers[cinfo.next_scanline];
		for (x = 0; x < width; ++x)
		{
			row[x * 3 + 0] = source[0];
			row[x * 3 + 1] = source[1];
			row[x * 3 + 2] = source[2];
			source += 4;
		}
		jpeg_write_scanlines(&cinfo, jrow_pointer, 1);
	}

	jpeg_finish_compress(&cinfo);
	fclose(outfp);
	jpeg_destroy_compress(&cinfo);

		/* and write png */
	strcpy(filename, outfile);
	strcat(filename, ".a.png");

	outfp = fopen(filename, "wb");
	if (!outfp)
	{
		perror(filename);
		return 1;
	}

	png_structp png_ptr_w = png_create_write_struct(PNG_LIBPNG_VER_STRING, 0, 0, 0);
	png_infop info_ptr_w = png_create_info_struct(png_ptr_w);
	if (setjmp(png_jmpbuf(png_ptr_w)))
	{
		png_destroy_write_struct(&png_ptr_w, &info_ptr_w);
		fclose(outfp);
		return 1;
	}
	png_init_io(png_ptr_w, outfp);
	png_set_IHDR(png_ptr_w, info_ptr_w, width, height, 8, PNG_COLOR_TYPE_GRAY, PNG_INTERLACE_NONE, PNG_COMPRESSION_TYPE_DEFAULT, PNG_FILTER_TYPE_DEFAULT);

		/* turn RGBA into A, in-place */
	int x, y;
	for (y=0; y < height; ++y)
	{
		unsigned char *source = row_pointers[y];
		unsigned char *dst = source;
		for (x=0; x < width; ++x)
		{
			*dst++ = source[3];
			source += 4;
		}
	}
	png_set_rows(png_ptr_w, info_ptr_w, row_pointers);
	png_write_png(png_ptr_w, info_ptr_w, PNG_TRANSFORM_IDENTITY, 0);
	png_write_end(png_ptr_w, info_ptr_w);
	png_destroy_write_struct(&png_ptr_w, &info_ptr_w);
	return 0;
}
