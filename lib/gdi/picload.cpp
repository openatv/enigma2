#include <lib/gdi/picload.h>
#include "picexif.h"
#include <lib/python/python.h>

#include <png.h>

#include <fcntl.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

extern "C" {
#include <jpeglib.h>
#include <gif_lib.h>
//#include "transupp.h"
}
#include <setjmp.h>

unsigned char *pic_buffer=NULL;

static unsigned char *simple_resize(unsigned char * orgin, int ox, int oy, int dx, int dy)
{
	unsigned char *cr, *p, *l;
	int i, j, k, ip;
	cr = new unsigned char[dx * dy * 3]; 
	if (cr == NULL)
	{
		printf("[RESIZE] Error: malloc\n");
		return(orgin);
	}
	l = cr;

	for (j = 0; j < dy; j++,l += dx * 3)
	{
		p = orgin + (j * oy / dy * ox * 3);
		for (i = 0, k = 0; i < dx; i++, k += 3)
		{
			ip = i * ox / dx * 3;
			l[k] = p[ip];
			l[k+1] = p[ip + 1];
			l[k+2] = p[ip + 2];
		}
	}
	delete [] orgin;
	return(cr);
}

static unsigned char *color_resize(unsigned char * orgin, int ox, int oy, int dx, int dy)
{
	unsigned char *cr, *p, *q;
	int i, j, k, l, xa, xb, ya, yb;
	int sq, r, g, b;
	cr = new unsigned char[dx * dy * 3];
	if (cr == NULL)
	{
		printf("[RESIZE] Error: malloc\n");
		return(orgin);
	}
	p = cr;

	for (j = 0; j < dy; j++)
	{
		for (i = 0; i < dx; i++, p += 3)
		{
			xa = i * ox / dx;
			ya = j * oy / dy;
			xb = (i + 1) * ox / dx; 
			if (xb >= ox)
				xb = ox - 1;
			yb = (j + 1) * oy / dy; 
			if (yb >= oy)
				yb = oy - 1;
			for (l = ya, r = 0, g = 0, b = 0, sq = 0; l <= yb; l++)
			{
				q = orgin + ((l * ox + xa) * 3);
				for (k = xa; k <= xb; k++, q += 3, sq++)
				{
					r += q[0]; g += q[1]; b += q[2];
				}
			}
			p[0] = r / sq; p[1] = g / sq; p[2] = b / sq;
		}
	}
	delete [] orgin;
	return(cr);
}

//-------------------------------------------------------------------

struct r_jpeg_error_mgr
{
	struct jpeg_error_mgr pub;
	jmp_buf envbuffer;
};

void jpeg_cb_error_exit(j_common_ptr cinfo)
{
	struct r_jpeg_error_mgr *mptr;
	mptr = (struct r_jpeg_error_mgr *) cinfo->err;
	(*cinfo->err->output_message) (cinfo);
	longjmp(mptr->envbuffer, 1);
}

static int jpeg_save(unsigned char *image_buffer, const char * filename, int quality, int image_height, int image_width)
{
 	struct jpeg_compress_struct cinfo;
 	struct jpeg_error_mgr jerr;
 	FILE * outfile;		/* target file */
 	JSAMPROW row_pointer[1];/* pointer to JSAMPLE row[s] */
 	int row_stride;		/* physical row width in image buffer */
 
 	cinfo.err = jpeg_std_error(&jerr);
 	jpeg_create_compress(&cinfo);
 
 	if ((outfile = fopen(filename, "wb")) == NULL) 
	{
		eDebug("[JPEG] can't open %s", filename);
		return -1;
	}
 	jpeg_stdio_dest(&cinfo, outfile);
 
 	cinfo.image_width = image_width;
 	cinfo.image_height = image_height;
 	cinfo.input_components = 3;
 	cinfo.in_color_space = JCS_RGB;
 	jpeg_set_defaults(&cinfo);
 	jpeg_set_quality(&cinfo, quality, TRUE );
 	jpeg_start_compress(&cinfo, TRUE);
 	row_stride = image_width * 3;
 	while (cinfo.next_scanline < cinfo.image_height) 
	{
 		row_pointer[0] = & image_buffer[cinfo.next_scanline * row_stride];
 		(void) jpeg_write_scanlines(&cinfo, row_pointer, 1);
 	}
 	jpeg_finish_compress(&cinfo);
 	fclose(outfile);
 	jpeg_destroy_compress(&cinfo);
 	return 0;
}


static int jpeg_load(const char *filename, int *x, int *y)
{
	struct jpeg_decompress_struct cinfo;
	struct jpeg_decompress_struct *ciptr = &cinfo;
	struct r_jpeg_error_mgr emgr;
	FILE *fh;

	if (!(fh = fopen(filename, "rb")))
		return 0;

	ciptr->err = jpeg_std_error(&emgr.pub);
	emgr.pub.error_exit = jpeg_cb_error_exit;
	if (setjmp(emgr.envbuffer) == 1)
	{
		jpeg_destroy_decompress(ciptr);
		fclose(fh);
		return 0;
	}

	jpeg_create_decompress(ciptr);
	jpeg_stdio_src(ciptr, fh);
	jpeg_read_header(ciptr, TRUE);
	ciptr->out_color_space = JCS_RGB;
	ciptr->scale_denom = 1;

	jpeg_start_decompress(ciptr);
	
	*x=ciptr->output_width;
	*y=ciptr->output_height;

	if(ciptr->output_components == 3)
	{
		JSAMPLE *lb = (JSAMPLE *)(*ciptr->mem->alloc_small)((j_common_ptr) ciptr, JPOOL_PERMANENT, ciptr->output_width * ciptr->output_components);
		pic_buffer = new unsigned char[ciptr->output_height * ciptr->output_width * ciptr->output_components];
		unsigned char *bp = pic_buffer;

		while (ciptr->output_scanline < ciptr->output_height)
		{
			jpeg_read_scanlines(ciptr, &lb, 1);
			memcpy(bp, lb, ciptr->output_width * ciptr->output_components);
			bp += ciptr->output_width * ciptr->output_components;
		}
	}
	jpeg_finish_decompress(ciptr);
	jpeg_destroy_decompress(ciptr);
	fclose(fh);
	return 1;
}

//---------------------------------------------------------------------------------------------

#define BMP_TORASTER_OFFSET 10
#define BMP_SIZE_OFFSET 18
#define BMP_BPP_OFFSET 28
#define BMP_RLE_OFFSET 30
#define BMP_COLOR_OFFSET 54

#define fill4B(a) ((4 - ((a) % 4 )) & 0x03)

struct color {
	unsigned char red;
	unsigned char green;
	unsigned char blue;
};

static void fetch_pallete(int fd, struct color pallete[], int count)
{
	unsigned char buff[4];
	lseek(fd, BMP_COLOR_OFFSET, SEEK_SET);
	for (int i = 0; i < count; i++)
	{
		read(fd, buff, 4);
		pallete[i].red = buff[2];
		pallete[i].green = buff[1];
		pallete[i].blue = buff[0];
	}
}

static int bmp_load(const char *filename,  int *x, int *y)
{
	unsigned char buff[4];
	struct color pallete[256];

	int fd = open(filename, O_RDONLY);
	if (fd == -1) return 0;
	if (lseek(fd, BMP_SIZE_OFFSET, SEEK_SET) == -1) return 0;
	read(fd, buff, 4);
	*x = buff[0] + (buff[1] << 8) + (buff[2] << 16) + (buff[3] << 24);
	read(fd, buff, 4);
	*y = buff[0] + (buff[1] << 8) + (buff[2] << 16) + (buff[3] << 24);
	if (lseek(fd, BMP_TORASTER_OFFSET, SEEK_SET) == -1) return 0;
	read(fd, buff, 4);
	int raster = buff[0] + (buff[1] << 8) + (buff[2] << 16) + (buff[3] << 24);
	if (lseek(fd, BMP_BPP_OFFSET, SEEK_SET) == -1) return 0;
	read(fd, buff, 2);
	int bpp = buff[0] + (buff[1] << 8);

	pic_buffer = new unsigned char[(*x) * (*y) * 3];
	unsigned char *wr_buffer = pic_buffer + (*x) * ((*y) - 1) * 3;
	
	switch (bpp)
	{
		case 4:
		{
			int skip = fill4B((*x) / 2 + (*x) % 2);
			fetch_pallete(fd, pallete, 16);
			lseek(fd, raster, SEEK_SET);
			unsigned char * tbuffer = new unsigned char[*x / 2 + 1];
			if (tbuffer == NULL)
				return 0;
			for (int i = 0; i < *y; i++) 
			{
				read(fd, tbuffer, (*x) / 2 + *x % 2);
				int j;
				for (j = 0; j < (*x) / 2; j++)
				{
					unsigned char c1 = tbuffer[j] >> 4;
					unsigned char c2 = tbuffer[j] & 0x0f;
					*wr_buffer++ = pallete[c1].red;
					*wr_buffer++ = pallete[c1].green;
					*wr_buffer++ = pallete[c1].blue;
					*wr_buffer++ = pallete[c2].red;
					*wr_buffer++ = pallete[c2].green;
					*wr_buffer++ = pallete[c2].blue;
				}
				if ((*x) % 2)
				{
					unsigned char c1 = tbuffer[j] >> 4;
					*wr_buffer++ = pallete[c1].red;
					*wr_buffer++ = pallete[c1].green;
					*wr_buffer++ = pallete[c1].blue;
				}
				if (skip)
					read(fd, buff, skip);
				wr_buffer -= (*x) * 6;
			}
			break;
		}
		case 8:
		{
			int skip = fill4B(*x);
			fetch_pallete(fd, pallete, 256);
			lseek(fd, raster, SEEK_SET);
			unsigned char * tbuffer = new unsigned char[*x];
			if (tbuffer == NULL)
				return 0;
			for (int i = 0; i < *y; i++)
			{
				read(fd, tbuffer, *x);
				for (int j = 0; j < *x; j++)
				{
					wr_buffer[j * 3] = pallete[tbuffer[j]].red;
					wr_buffer[j * 3 + 1] = pallete[tbuffer[j]].green;
					wr_buffer[j * 3 + 2] = pallete[tbuffer[j]].blue;
				}
				if (skip)
					read(fd, buff, skip);
				wr_buffer -= (*x) * 3;
			}
			break;
		}
		case 24:
		{
			int skip = fill4B((*x) * 3);
			lseek(fd, raster, SEEK_SET);
			for (int i = 0; i < (*y); i++)
			{
				read(fd, wr_buffer, (*x) * 3);
				for (int j = 0; j < (*x) * 3 ; j = j + 3)
				{
					unsigned char c = wr_buffer[j];
					wr_buffer[j] = wr_buffer[j + 2];
					wr_buffer[j + 2] = c;
				}
				if (skip)
					read(fd, buff, skip);
				wr_buffer -= (*x) * 3;
			}
			break;
		}
		default:
			return 0;
	}

	close(fd);
	return 1;
}

//---------------------------------------------------------------------------------------------

static int png_load(const char *filename,  int *x, int *y)
{
	static const png_color_16 my_background = {0, 0, 0, 0, 0};

	png_structp png_ptr;
	png_infop info_ptr;
	png_uint_32 width, height;
	unsigned int i;
	int bit_depth, color_type, interlace_type;
	int number_passes, pass;
	png_byte * fbptr;
	FILE * fh;

	if (!(fh = fopen(filename, "rb"))) return 0;

	png_ptr = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	if (png_ptr == NULL)
		return 0;
	info_ptr = png_create_info_struct(png_ptr);
	if (info_ptr == NULL)
	{
		png_destroy_read_struct(&png_ptr, (png_infopp)NULL, (png_infopp)NULL);
		fclose(fh); 
		return 0;
	}

	if (setjmp(png_ptr->jmpbuf))
	{
		png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);
		fclose(fh); 
		return 0;
	}

	png_init_io(png_ptr, fh);

	png_read_info(png_ptr, info_ptr);
	png_get_IHDR(png_ptr, info_ptr, &width, &height, &bit_depth, &color_type, &interlace_type, NULL, NULL);

	if (color_type == PNG_COLOR_TYPE_PALETTE)
	{
		png_set_palette_to_rgb(png_ptr);
		png_set_background(png_ptr, (png_color_16 *)&my_background, PNG_BACKGROUND_GAMMA_SCREEN, 0, 1.0);
	}

	if (color_type == PNG_COLOR_TYPE_GRAY || color_type == PNG_COLOR_TYPE_GRAY_ALPHA)
	{
		png_set_gray_to_rgb(png_ptr);
		png_set_background(png_ptr, (png_color_16 *)&my_background, PNG_BACKGROUND_GAMMA_SCREEN, 0, 1.0);
	}

	if (color_type & PNG_COLOR_MASK_ALPHA)
		png_set_strip_alpha(png_ptr);

	if (bit_depth < 8)	png_set_packing(png_ptr);
	if (bit_depth == 16)	png_set_strip_16(png_ptr);

	number_passes = png_set_interlace_handling(png_ptr);
	png_read_update_info(png_ptr, info_ptr);

	if (width * 3 != png_get_rowbytes(png_ptr, info_ptr))
	{
		eDebug("[PNG] Error processing");
		return 0;
	}

	if (width * height > 1000000) // 1000x1000 or equiv.
	{
		eDebug("[png_load] image size is %d x %d, which is \"too large\".", width, height);
		png_read_end(png_ptr, info_ptr);
		png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);
		fclose(fh);
		return 0;
	}

	pic_buffer = new unsigned char[width * height * 3];
	*x=width;
	*y=height;

	for(pass = 0; pass < number_passes; pass++)
	{
		fbptr = (png_byte *)pic_buffer;
		for (i = 0; i < height; i++, fbptr += width * 3)
			png_read_row(png_ptr, fbptr, NULL);
	}
	png_read_end(png_ptr, info_ptr);
	png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);
	fclose(fh);
	return 1;
}

//-------------------------------------------------------------------

inline void m_rend_gif_decodecolormap(unsigned char *cmb, unsigned char *rgbb, ColorMapObject *cm, int s, int l)
{
	GifColorType *cmentry;
	int i;
	for (i = 0; i < l; i++)
	{
		cmentry = &cm->Colors[cmb[i]];
		*(rgbb++) = cmentry->Red;
		*(rgbb++) = cmentry->Green;
		*(rgbb++) = cmentry->Blue;
	}
}

static int gif_load(const char *filename, int *x, int *y)
{
	int px, py, i, j, ibxs;
	unsigned char *fbptr;
	unsigned char *lb=NULL;
	unsigned char *slb=NULL;
	GifFileType *gft;
	GifRecordType rt;
	GifByteType *extension;
	ColorMapObject *cmap;
	int cmaps;
	int extcode;
	
	gft = DGifOpenFileName(filename);
	if (gft == NULL) 
		return 0;
	do
	{
		if (DGifGetRecordType(gft, &rt) == GIF_ERROR)
			goto ERROR_R;
		switch(rt)
		{
			case IMAGE_DESC_RECORD_TYPE:
				if (DGifGetImageDesc(gft) == GIF_ERROR)
					goto ERROR_R;
				*x = px = gft->Image.Width;
				*y = py = gft->Image.Height;
				pic_buffer = new unsigned char[px * py * 3];
				lb = (unsigned char *)malloc(px * 3);
				slb = (unsigned char *) malloc(px);

				if (lb != NULL && slb != NULL)
				{
					cmap = (gft->Image.ColorMap ? gft->Image.ColorMap : gft->SColorMap);
					cmaps = cmap->ColorCount;

					ibxs = ibxs * 3;
					fbptr = pic_buffer;
					if (!(gft->Image.Interlace))
					{
						for (i = 0; i < py; i++, fbptr += px * 3)
						{
							if (DGifGetLine(gft, slb, px) == GIF_ERROR)
								goto ERROR_R;
							m_rend_gif_decodecolormap(slb, lb, cmap, cmaps, px);
							memcpy(fbptr, lb, px * 3);
						}
					}
					else
					{
						for (j = 0; j < 4; j++)
						{
							fbptr = pic_buffer;
							for (i = 0; i < py; i++, fbptr += px * 3)
							{
								if (DGifGetLine(gft, slb, px) == GIF_ERROR)
									goto ERROR_R;
								m_rend_gif_decodecolormap(slb, lb, cmap, cmaps, px);
								memcpy(fbptr, lb, px * 3);
							}
						}
					}
				}
				if (lb)
				{
					free(lb);
					lb=NULL;
				}
				if (slb)
				{
					free(slb);
					slb=NULL;
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

	DGifCloseFile(gft);
	return 1;
ERROR_R:
	eDebug("[GIF] Error");
	if (lb) 	free(lb);
	if (slb) 	free(slb);
	DGifCloseFile(gft);
	return 0;
}

//---------------------------------------------------------------------------------------------

PyObject *getExif(const char *filename)
{
	ePyObject list;
	Cexif exif;
	if(exif.DecodeExif(filename))
	{
		if(exif.m_exifinfo->IsExif)
		{
			int pos=0;
			char tmp[256];
			list = PyList_New(22);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->Version));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->CameraMake));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->CameraModel));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->DateTime));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->Comments));
			PyList_SET_ITEM(list, pos++,  PyString_FromFormat("%d x %d", exif.m_exifinfo->Width, exif.m_exifinfo->Height));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->Orientation));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->MeteringMode));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->ExposureProgram));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->LightSource));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->FlashUsed));
			PyList_SET_ITEM(list, pos++,  PyString_FromFormat("%d", exif.m_exifinfo->CompressionLevel));
			PyList_SET_ITEM(list, pos++,  PyString_FromFormat("%d", exif.m_exifinfo->ISOequivalent));
			sprintf(tmp, "%.2f", exif.m_exifinfo->Xresolution);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.2f", exif.m_exifinfo->Yresolution);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif.m_exifinfo->ResolutionUnit));
			sprintf(tmp, "%.2f", exif.m_exifinfo->Brightness);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.5f sec.", exif.m_exifinfo->ExposureTime);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.5f", exif.m_exifinfo->ExposureBias);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.5f", exif.m_exifinfo->Distance);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.5f", exif.m_exifinfo->CCDWidth);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.2f", exif.m_exifinfo->ApertureFNumber);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
		}
		else
		{
			list = PyList_New(1);
			PyList_SET_ITEM(list, 0, PyString_FromString(exif.m_szLastError));
		}
		exif.ClearExif();
	}
	else
	{
		list = PyList_New(1);
		PyList_SET_ITEM(list, 0, PyString_FromString(exif.m_szLastError));
	}

	return list ? (PyObject*)list : (PyObject*)PyList_New(0);
}

//---------------------------------------------------------------------------------------------
enum {F_NONE, F_PNG, F_JPEG, F_BMP, F_GIF};

static int pic_id(const char *name)
{
	unsigned char id[10];
	int fd = open(name, O_RDONLY); 
	if (fd == -1) 
		return F_NONE;
	read(fd, id, 10);
	close(fd);

	if(id[1] == 'P' && id[2] == 'N' && id[3] == 'G')
		return F_PNG;
	else if(id[6] == 'J' && id[7] == 'F' && id[8] == 'I' && id[9] == 'F')
		return F_JPEG;
	else if(id[0] == 0xff && id[1] == 0xd8 && id[2] == 0xff) 
		return F_JPEG;
	else if(id[0] == 'B' && id[1] == 'M' )
		return F_BMP;
	else if(id[0] == 'G' && id[1] == 'I' && id[2] == 'F')
		return F_GIF;
	return F_NONE;
}

int loadPic(ePtr<gPixmap> &result, std::string filename, int w, int h, int aspect, int resize_mode, int rotate, int background, std::string cachefile)
{
	result = 0;
	int ox=0, oy=0, imx, imy;
	pic_buffer=NULL;
	bool cache=false;

	if(cachefile.length())
	{
		cache = true;
		if(jpeg_load(cachefile.c_str(), &ox, &oy))
			eDebug("[CACHEPIC] x-size=%d, y-size=%d", ox, oy);
	}

	if(pic_buffer==NULL)
	{
		switch(pic_id(filename.c_str()))
		{
			case F_PNG:	png_load(filename.c_str(), &ox, &oy); break;
			case F_JPEG:	jpeg_load(filename.c_str(), &ox, &oy); break;
			case F_BMP:	bmp_load(filename.c_str(), &ox, &oy); break;
			case F_GIF:	gif_load(filename.c_str(), &ox, &oy); break;
			default:
				eDebug("[PIC] <format not supportet>");
				return 0;
		}
	
		eDebug("[FULLPIC] x-size=%d, y-size=%d", ox, oy);

		if(pic_buffer==NULL)
			return 0;

		double aspect_ratio;
		switch(aspect)
		{
			case 1:		aspect_ratio = 1.778 / ((double)720/576); break; //16:9
			case 2:		aspect_ratio = 1.600 / ((double)720/576); break; //16:10
			//case 3:	aspect_ratio = 1.250 / ((double)720/576); break; //5:4
			default:	aspect_ratio = 1.333 / ((double)720/576); //4:3
		}

		if((aspect_ratio * oy * w / ox) <= h)
		{
			imx = w;
			imy = (int)(aspect_ratio*oy*w/ox);
		}
		else
		{
			imx = (int)((1.0/aspect_ratio)*ox*h/oy);
			imy = h;
		}

		if(resize_mode)	pic_buffer = color_resize(pic_buffer, ox, oy, imx, imy);
		else		pic_buffer = simple_resize(pic_buffer, ox, oy, imx, imy);

		ox = imx;
		oy = imy;
		
		if(cache)
		{
			jpeg_save(pic_buffer, cachefile.c_str(), 50, oy, ox);
			eDebug("[SAVEPIC] x-size=%d, y-size=%d", ox, oy);
		}
		
	}

	
	result=new gPixmap(eSize(w, h), 32);
	gSurface *surface = result->surface;
	int a=0, b=0;
	int nc=0, oc=0;
	int o_y=0, u_y=0, v_x=0, h_x=0;
	unsigned char clear[4] = {0x00,0x00,0x00,0x00};
	if(background)	clear[3]=0xFF;
	unsigned char *tmp_buffer = new unsigned char[4];

	if(oy < h)
	{
		o_y=(h-oy)/2;
		u_y=h-oy-o_y;
	}
	if(ox < w)
	{
		v_x=(w-ox)/2;
		h_x=w-ox-v_x;
	}
	
	//eDebug("o_y=%d u_y=%d v_x=%d h_x=%d", o_y, u_y, v_x, h_x);

	if(oy < h)
		for(a=0; a<(o_y*ox)+1; a++, nc+=4)
		{
			memcpy(tmp_buffer, clear, sizeof(clear));
			tmp_buffer=((unsigned char *)(surface->data)) + nc;
		}
	
	for(a=0; a<oy; a++)
	{
		if(ox < w)
			for(b=0; b<v_x; b++, nc+=4)
			{
				memcpy(tmp_buffer, clear, sizeof(clear));
				tmp_buffer=((unsigned char *)(surface->data)) + nc;
			}

		for(b=0; b<(ox*3); b+=3, nc+=4)
		{
			tmp_buffer[3]=0xFF;
			tmp_buffer[2]=pic_buffer[oc++];
			tmp_buffer[1]=pic_buffer[oc++];
			tmp_buffer[0]=pic_buffer[oc++];

			tmp_buffer=((unsigned char *)(surface->data)) + nc;
		}
		
		if(ox < w)
			for(b=0; b<h_x; b++, nc+=4)
			{
				memcpy(tmp_buffer, clear, sizeof(clear));
				tmp_buffer=((unsigned char *)(surface->data)) + nc;
			}
	}

	if(oy < h)
		for(a=0; a<(u_y*ox)+1; a++, nc+=4)
		{
			memcpy(tmp_buffer, clear, sizeof(clear));
			tmp_buffer=((unsigned char *)(surface->data)) + nc;
		}
	
	//eDebug("[PIC] buffer=%d, nc=%d oc=%d ox=%d, oy=%d",w*h*4, nc, oc, ox, oy);
	
	surface->clut.data=0;
	surface->clut.colors=0;
	surface->clut.start=0;
	
	delete [] pic_buffer;

	return 0;
}
