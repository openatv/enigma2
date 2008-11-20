#include <png.h>	// must be included before Python.h because of setjmp
#include <fcntl.h>

#include <lib/gdi/picload.h>
#include <lib/gdi/picexif.h>

extern "C" {
#include <jpeglib.h>
#include <gif_lib.h>
}

extern const uint32_t crc32_table[256];

DEFINE_REF(ePicLoad);

static std::string getSize(const char* file)
{
	struct stat64 s;
	if (stat64(file, &s) < 0)
		return "";
	char tmp[20];
	snprintf(tmp, 20, "%ld kB",(long)s.st_size / 1024);
	return tmp;
}

static unsigned char *conv24to32(unsigned char *orgin, int size, unsigned char alpha = 0xFF)
{
	int s, d;
	unsigned char *cr = new unsigned char[size * 4];
	if (cr == NULL)
	{
		eDebug("[Picload] Error malloc");
		return(orgin);
	}

	for (s = 0, d = 0 ; s < (size * 3); s += 3, d += 4 )
	{
		cr[d] = orgin[s];
		cr[d+1] = orgin[s + 1];
		cr[d+2] = orgin[s + 2];
		cr[d+3] = alpha;
	}
	delete [] orgin;
	return(cr);
}

static unsigned char *simple_resize(unsigned char *orgin, int ox, int oy, int dx, int dy)
{
	unsigned char *cr, *p, *l;
	int i, j, k, ip;
	cr = new unsigned char[dx * dy * 3];
	if (cr == NULL)
	{
		eDebug("[Picload] Error malloc");
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
		eDebug("[Picload] Error malloc");
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

static unsigned char *bmp_load(const char *file,  int *x, int *y)
{
	unsigned char buff[4];
	struct color pallete[256];

	int fd = open(file, O_RDONLY);
	if (fd == -1) return NULL;
	if (lseek(fd, BMP_SIZE_OFFSET, SEEK_SET) == -1) return NULL;
	read(fd, buff, 4);
	*x = buff[0] + (buff[1] << 8) + (buff[2] << 16) + (buff[3] << 24);
	read(fd, buff, 4);
	*y = buff[0] + (buff[1] << 8) + (buff[2] << 16) + (buff[3] << 24);
	if (lseek(fd, BMP_TORASTER_OFFSET, SEEK_SET) == -1) return NULL;
	read(fd, buff, 4);
	int raster = buff[0] + (buff[1] << 8) + (buff[2] << 16) + (buff[3] << 24);
	if (lseek(fd, BMP_BPP_OFFSET, SEEK_SET) == -1) return NULL;
	read(fd, buff, 2);
	int bpp = buff[0] + (buff[1] << 8);

	unsigned char *pic_buffer = new unsigned char[(*x) * (*y) * 3];
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
				return NULL;
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
				return NULL;
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
			return NULL;
	}

	close(fd);
	return(pic_buffer);
}

//---------------------------------------------------------------------

static unsigned char *png_load(const char *file, int *ox, int *oy)
{
	static const png_color_16 my_background = {0, 0, 0, 0, 0};

	png_uint_32 width, height;
	unsigned int i;
	int bit_depth, color_type, interlace_type;
	png_byte *fbptr;
	FILE *fh;

	if (!(fh = fopen(file, "rb")))
		return NULL;

	png_structp png_ptr = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	if (png_ptr == NULL)
		return NULL;
	png_infop info_ptr = png_create_info_struct(png_ptr);
	if (info_ptr == NULL)
	{
		png_destroy_read_struct(&png_ptr, (png_infopp)NULL, (png_infopp)NULL);
		fclose(fh);
		return NULL;
	}

	if (setjmp(png_ptr->jmpbuf))
	{
		png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);
		fclose(fh);
		return NULL;
	}

	png_init_io(png_ptr, fh);

	png_read_info(png_ptr, info_ptr);
	png_get_IHDR(png_ptr, info_ptr, &width, &height, &bit_depth, &color_type, &interlace_type, NULL, NULL);

	if ((color_type == PNG_COLOR_TYPE_PALETTE)||(color_type == PNG_COLOR_TYPE_GRAY && bit_depth < 8)||(png_get_valid(png_ptr, info_ptr, PNG_INFO_tRNS)))
		png_set_expand(png_ptr);
	if (bit_depth == 16)
		png_set_strip_16(png_ptr);
	if (color_type == PNG_COLOR_TYPE_GRAY || color_type == PNG_COLOR_TYPE_GRAY_ALPHA)
		png_set_gray_to_rgb(png_ptr);

	int number_passes = png_set_interlace_handling(png_ptr);
	png_read_update_info(png_ptr, info_ptr);

	if (width * 3 != png_get_rowbytes(png_ptr, info_ptr))
	{
		eDebug("[Picload] Error processing");
		png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);
		fclose(fh);
		return NULL;
	}

	unsigned char *pic_buffer = new unsigned char[height * width * 3];
	*ox=width;
	*oy=height;

	for(int pass = 0; pass < number_passes; pass++)
	{
		fbptr = (png_byte *)pic_buffer;
		for (i = 0; i < height; i++, fbptr += width * 3)
			png_read_row(png_ptr, fbptr, NULL);
	}
	png_read_end(png_ptr, info_ptr);
	png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);
	fclose(fh);
	return(pic_buffer);
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

static unsigned char *jpeg_load(const char *file, int *ox, int *oy)
{
	struct jpeg_decompress_struct cinfo;
	struct jpeg_decompress_struct *ciptr = &cinfo;
	struct r_jpeg_error_mgr emgr;
	FILE *fh;
	unsigned char *pic_buffer=NULL;

	if (!(fh = fopen(file, "rb")))
		return NULL;

	ciptr->err = jpeg_std_error(&emgr.pub);
	emgr.pub.error_exit = jpeg_cb_error_exit;
	if (setjmp(emgr.envbuffer) == 1)
	{
		jpeg_destroy_decompress(ciptr);
		fclose(fh);
		return NULL;
	}

	jpeg_create_decompress(ciptr);
	jpeg_stdio_src(ciptr, fh);
	jpeg_read_header(ciptr, TRUE);
	ciptr->out_color_space = JCS_RGB;
	ciptr->scale_denom = 1;

	jpeg_start_decompress(ciptr);
	
	*ox=ciptr->output_width;
	*oy=ciptr->output_height;

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
	return(pic_buffer);
}


static int jpeg_save(const char * filename, int ox, int oy, unsigned char *pic_buffer)
{
 	struct jpeg_compress_struct cinfo;
 	struct jpeg_error_mgr jerr;
 	FILE * outfile;		
 	JSAMPROW row_pointer[1];
 	int row_stride;		
 
 	cinfo.err = jpeg_std_error(&jerr);
 	jpeg_create_compress(&cinfo);
 
 	if ((outfile = fopen(filename, "wb")) == NULL) 
	{
		eDebug("[Picload] jpeg can't open %s", filename);
		return 1;
	}
	eDebug("[Picload] save Thumbnail... %s",filename);

 	jpeg_stdio_dest(&cinfo, outfile);
 
 	cinfo.image_width = ox;
 	cinfo.image_height = oy;
 	cinfo.input_components = 3;
 	cinfo.in_color_space = JCS_RGB;
 	jpeg_set_defaults(&cinfo);
 	jpeg_set_quality(&cinfo, 70, TRUE );
 	jpeg_start_compress(&cinfo, TRUE);
 	row_stride = ox * 3;
 	while (cinfo.next_scanline < cinfo.image_height) 
	{
 		row_pointer[0] = & pic_buffer[cinfo.next_scanline * row_stride];
 		(void) jpeg_write_scanlines(&cinfo, row_pointer, 1);
 	}
 	jpeg_finish_compress(&cinfo);
 	fclose(outfile);
 	jpeg_destroy_compress(&cinfo);
 	return 0;
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

static unsigned char *gif_load(const char *file, int *ox, int *oy)
{
	unsigned char *pic_buffer = NULL;
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
	
	gft = DGifOpenFileName(file);
	if (gft == NULL) 
		return NULL;
	do
	{
		if (DGifGetRecordType(gft, &rt) == GIF_ERROR)
			goto ERROR_R;
		switch(rt)
		{
			case IMAGE_DESC_RECORD_TYPE:
				if (DGifGetImageDesc(gft) == GIF_ERROR)
					goto ERROR_R;
				*ox = px = gft->Image.Width;
				*oy = py = gft->Image.Height;
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
	return(pic_buffer);
ERROR_R:
	eDebug("[Picload] <Error gif>");
	if (lb) 	free(lb);
	if (slb) 	free(slb);
	DGifCloseFile(gft);
	return NULL;
}

//---------------------------------------------------------------------------------------------

ePicLoad::ePicLoad()
	:msg_thread(this,1), msg_main(eApp,1)
{
	CONNECT(msg_thread.recv_msg, ePicLoad::gotMessage);
	CONNECT(msg_main.recv_msg, ePicLoad::gotMessage);
	
	threadrunning = false;
	m_filepara = NULL;
	m_conf.max_x = 0;
	m_conf.max_y = 0;
	m_conf.aspect_ratio = 1.066400; //4:3
	m_conf.usecache = false;
	m_conf.resizetype = 1;
	memset(m_conf.background,0x00,sizeof(m_conf.background));
	m_conf.thumbnailsize = 180;
}

void ePicLoad::waitFinished()
{
	msg_thread.send(Message(Message::quit));
	kill();
}

ePicLoad::~ePicLoad()
{
	if (threadrunning)
		waitFinished();
	if(m_filepara != NULL)
		delete m_filepara;
}

void ePicLoad::thread_finished()
{
	threadrunning=false;
}

void ePicLoad::thread()
{
	hasStarted();
	threadrunning=true;
	nice(4);
	runLoop();
}

void ePicLoad::decodePic()
{
	eDebug("[Picload] decode picture... %s",m_filepara->file);
	
	switch(m_filepara->id)
	{
		case F_PNG:	m_filepara->pic_buffer = png_load(m_filepara->file, &m_filepara->ox, &m_filepara->oy);	break;
		case F_JPEG:	m_filepara->pic_buffer = jpeg_load(m_filepara->file, &m_filepara->ox, &m_filepara->oy);	break;
		case F_BMP:	m_filepara->pic_buffer = bmp_load(m_filepara->file, &m_filepara->ox, &m_filepara->oy);	break;
		case F_GIF:	m_filepara->pic_buffer = gif_load(m_filepara->file, &m_filepara->ox, &m_filepara->oy);	break;
	}
	
	if(m_filepara->pic_buffer != NULL)
	{
		resizePic();
	}
}

void ePicLoad::decodeThumb()
{
	eDebug("[Picload] get Thumbnail... %s",m_filepara->file);

	bool exif_thumbnail = false;
	bool cachefile_found = false;
	std::string cachefile = "";
	std::string cachedir = "/.Thumbnails";
	
	if(m_filepara->id == F_JPEG)
	{
		Cexif *exif = new Cexif;
		if(exif->DecodeExif(m_filepara->file, 1))
		{
			if(exif->m_exifinfo->IsExif)
			{
				if(exif->m_exifinfo->Thumnailstate==2)
				{
					m_filepara->file = strdup(THUMBNAILTMPFILE);
					exif_thumbnail = true;
					eDebug("[Picload] Exif Thumbnail found");
				}
				m_filepara->addExifInfo(exif->m_exifinfo->CameraMake);
				m_filepara->addExifInfo(exif->m_exifinfo->CameraModel);
				m_filepara->addExifInfo(exif->m_exifinfo->DateTime);
				char buf[20];
				snprintf(buf, 20, "%d x %d", exif->m_exifinfo->Width, exif->m_exifinfo->Height);
				m_filepara->addExifInfo(buf);
			}
			exif->ClearExif();
		}
		delete exif;
	}
	
	if((! exif_thumbnail) && m_conf.usecache)
	{
		if(FILE *f=fopen(m_filepara->file, "rb"))
		{
			int c;
			int count = 1024*100;
			unsigned long crc32 = 0;
			char crcstr[9];*crcstr=0;

			while ((c=getc(f))!=EOF)
			{
				crc32 = crc32_table[((crc32) ^ (c)) & 0xFF] ^ ((crc32) >> 8);
				if(--count < 0) break;
			}
	
			fclose(f);
			crc32 = ~crc32;
			sprintf(crcstr, "%08lX", crc32);
		
			cachedir = m_filepara->file;
			unsigned int pos = cachedir.find_last_of("/");
			if (pos != std::string::npos)
				cachedir = cachedir.substr(0, pos) + "/.Thumbnails";
			
			cachefile = cachedir + std::string("/pc_") + crcstr;
			if(!access(cachefile.c_str(), R_OK))
			{
				cachefile_found = true;
				m_filepara->file = strdup(cachefile.c_str());
				m_filepara->id = F_JPEG;
				eDebug("[Picload] Cache File found");
			}
		}
	}

	switch(m_filepara->id)
	{
		case F_PNG:	m_filepara->pic_buffer = png_load(m_filepara->file, &m_filepara->ox, &m_filepara->oy);	break;
		case F_JPEG:	m_filepara->pic_buffer = jpeg_load(m_filepara->file, &m_filepara->ox, &m_filepara->oy);	break;
		case F_BMP:	m_filepara->pic_buffer = bmp_load(m_filepara->file, &m_filepara->ox, &m_filepara->oy);	break;
		case F_GIF:	m_filepara->pic_buffer = gif_load(m_filepara->file, &m_filepara->ox, &m_filepara->oy);	break;
	}
	
	if(exif_thumbnail)
		::unlink(THUMBNAILTMPFILE);
	
	if(m_filepara->pic_buffer != NULL)
	{
		//save cachefile
		if(m_conf.usecache && (! exif_thumbnail) && (! cachefile_found))
		{
			if(access(cachedir.c_str(), R_OK))
				::mkdir(cachedir.c_str(), 0755);
			
			//resize for Thumbnail
			int imx, imy;
			if (m_filepara->ox <= m_filepara->oy)
			{
				imy = m_conf.thumbnailsize;
				imx = (int)( (m_conf.thumbnailsize * ((double)m_filepara->ox)) / ((double)m_filepara->oy) );
			}
			else
			{
				imx = m_conf.thumbnailsize;
				imy = (int)( (m_conf.thumbnailsize * ((double)m_filepara->oy)) / ((double)m_filepara->ox) );
			}

			m_filepara->pic_buffer = color_resize(m_filepara->pic_buffer, m_filepara->ox, m_filepara->oy, imx, imy);
			m_filepara->ox = imx;
			m_filepara->oy = imy;

			if(jpeg_save(cachefile.c_str(), m_filepara->ox, m_filepara->oy, m_filepara->pic_buffer))
				eDebug("[Picload] error saving cachefile");
		}

		resizePic();
	}
}

void ePicLoad::resizePic()
{
	int imx, imy;

	if((m_conf.aspect_ratio * m_filepara->oy * m_filepara->max_x / m_filepara->ox) <= m_filepara->max_y)
	{
		imx = m_filepara->max_x;
		imy = (int)(m_conf.aspect_ratio * m_filepara->oy * m_filepara->max_x / m_filepara->ox);
	}
	else
	{
		imx = (int)((1.0/m_conf.aspect_ratio) * m_filepara->ox * m_filepara->max_y / m_filepara->oy);
		imy = m_filepara->max_y;
	}
		
	if(m_conf.resizetype)
		m_filepara->pic_buffer = color_resize(m_filepara->pic_buffer, m_filepara->ox, m_filepara->oy, imx, imy);
	else
		m_filepara->pic_buffer = simple_resize(m_filepara->pic_buffer, m_filepara->ox, m_filepara->oy, imx, imy);

	m_filepara->ox = imx;
	m_filepara->oy = imy;
}

void ePicLoad::gotMessage(const Message &msg)
{
	switch (msg.type)
	{
		case Message::decode_Pic:
			decodePic();
			msg_main.send(Message(Message::decode_finished));
			break;
		case Message::decode_Thumb:
			decodeThumb();
			msg_main.send(Message(Message::decode_finished));
			break;
		case Message::quit: // called from decode thread
			eDebug("[Picload] decode thread ... got quit msg");
			quit(0);
			break;
		case Message::decode_finished: // called from main thread
			//eDebug("[Picload] decode finished... %s", m_filepara->file);
			if(m_filepara->callback)
			{
				PictureData(m_filepara->picinfo.c_str());
			}
			else
			{
				if(m_filepara != NULL)
				{
					delete m_filepara;
					m_filepara = NULL;
				}
			}
			break;
		default:
			eDebug("unhandled thread message");
	}
}

int ePicLoad::startThread(int what, const char *file, int x, int y, bool async)
{
	if(async && threadrunning && m_filepara != NULL)
	{
		eDebug("[Picload] thread running");
		m_filepara->callback = false;
		return 1;
	}
	
	if(m_filepara != NULL)
	{
		delete m_filepara;
		m_filepara = NULL;
	}
	
	int file_id = -1;
	unsigned char id[10];
	int fd = ::open(file, O_RDONLY);
	if (fd == -1) return 1;
	::read(fd, id, 10);
	::close(fd);

	if(id[1] == 'P' && id[2] == 'N' && id[3] == 'G')			file_id = F_PNG;
	else if(id[6] == 'J' && id[7] == 'F' && id[8] == 'I' && id[9] == 'F')	file_id = F_JPEG;
	else if(id[0] == 0xff && id[1] == 0xd8 && id[2] == 0xff) 		file_id = F_JPEG;
	else if(id[0] == 'B' && id[1] == 'M' )					file_id = F_BMP;
	else if(id[0] == 'G' && id[1] == 'I' && id[2] == 'F')			file_id = F_GIF;
	
	if(file_id < 0)
	{
		eDebug("[Picload] <format not supportet>");
		return 1;
	}

	m_filepara = new Cfilepara(file, file_id, getSize(file));
	x > 0 ? m_filepara->max_x = x : m_filepara->max_x = m_conf.max_x;
	y > 0 ? m_filepara->max_y = y : m_filepara->max_y = m_conf.max_y;
	
	if(m_filepara->max_x <= 0 || m_filepara->max_y <= 0)
	{
		delete m_filepara;
		m_filepara = NULL;
		eDebug("[Picload] <error in Para>");
		return 1;
	}
	
	if (async) {
		if(what==1)
			msg_thread.send(Message(Message::decode_Pic));
		else
			msg_thread.send(Message(Message::decode_Thumb));
		run();
	}
	else if (what == 1)
		decodePic();
	else
		decodeThumb();
	return 0;
}

RESULT ePicLoad::startDecode(const char *file, int x, int y, bool async)
{
	return startThread(1, file, x, y, async);
}

RESULT ePicLoad::getThumbnail(const char *file, int x, int y, bool async)
{
	return startThread(0, file, x, y, async);
}

PyObject *ePicLoad::getInfo(const char *filename)
{
	ePyObject list;
	
	Cexif *exif = new Cexif;
	if(exif->DecodeExif(filename))
	{
		if(exif->m_exifinfo->IsExif)
		{
			char tmp[256];
			int pos=0;
			list = PyList_New(23);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(filename));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->Version));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->CameraMake));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->CameraModel));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->DateTime));
			PyList_SET_ITEM(list, pos++,  PyString_FromFormat("%d x %d", exif->m_exifinfo->Width, exif->m_exifinfo->Height));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->FlashUsed));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->Orientation));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->Comments));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->MeteringMode));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->ExposureProgram));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->LightSource));
			PyList_SET_ITEM(list, pos++,  PyString_FromFormat("%d", exif->m_exifinfo->CompressionLevel));
			PyList_SET_ITEM(list, pos++,  PyString_FromFormat("%d", exif->m_exifinfo->ISOequivalent));
			sprintf(tmp, "%.2f", exif->m_exifinfo->Xresolution);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.2f", exif->m_exifinfo->Yresolution);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			PyList_SET_ITEM(list, pos++,  PyString_FromString(exif->m_exifinfo->ResolutionUnit));
			sprintf(tmp, "%.2f", exif->m_exifinfo->Brightness);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.5f sec.", exif->m_exifinfo->ExposureTime);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.5f", exif->m_exifinfo->ExposureBias);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.5f", exif->m_exifinfo->Distance);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.5f", exif->m_exifinfo->CCDWidth);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
			sprintf(tmp, "%.2f", exif->m_exifinfo->ApertureFNumber);
			PyList_SET_ITEM(list, pos++,  PyString_FromString(tmp));
		}
		else
		{
			list = PyList_New(2);
			PyList_SET_ITEM(list, 0, PyString_FromString(filename));
			PyList_SET_ITEM(list, 1, PyString_FromString(exif->m_szLastError));
		}
		exif->ClearExif();
	}
	else
	{
		list = PyList_New(2);
		PyList_SET_ITEM(list, 0, PyString_FromString(filename));
		PyList_SET_ITEM(list, 1, PyString_FromString(exif->m_szLastError));
	}
	delete exif;

	return list ? (PyObject*)list : (PyObject*)PyList_New(0);
}

int ePicLoad::getData(ePtr<gPixmap> &result)
{
	result = 0;
	if(m_filepara->pic_buffer == NULL) return 0;
	
	m_filepara->pic_buffer = conv24to32(m_filepara->pic_buffer, m_filepara->ox * m_filepara->oy);
	
	result=new gPixmap(eSize(m_filepara->max_x, m_filepara->max_y), 32);
	gSurface *surface = result->surface;
	int a=0, b=0;
	int nc=0, oc=0;
	int o_y=0, u_y=0, v_x=0, h_x=0;

	unsigned char *tmp_buffer=((unsigned char *)(surface->data));
	
	if(m_filepara->oy < m_filepara->max_y)
	{
		o_y = (m_filepara->max_y - m_filepara->oy) / 2;
		u_y = m_filepara->max_y - m_filepara->oy - o_y;
	}
	if(m_filepara->ox < m_filepara->max_x)
	{
		v_x = (m_filepara->max_x - m_filepara->ox) / 2;
		h_x = m_filepara->max_x - m_filepara->ox - v_x;
	}
	
	if(m_filepara->oy < m_filepara->max_y)
	{
		for(a=0; a<(o_y*m_filepara->ox); a++, nc+=4)
		{
			tmp_buffer=((unsigned char *)(surface->data)) + nc;
			memcpy(tmp_buffer, m_conf.background, sizeof(m_conf.background));
		}
	}
	
	for(a=0; a<m_filepara->oy; a++)
	{
		if(m_filepara->ox < m_filepara->max_x)
		{
			for(b=0; b<v_x; b++, nc+=4)
			{
				tmp_buffer=((unsigned char *)(surface->data)) + nc;
				memcpy(tmp_buffer, m_conf.background, sizeof(m_conf.background));
			}
		}

		for(b=0; b<(m_filepara->ox*4); b+=4, nc+=4)
		{
			tmp_buffer=((unsigned char *)(surface->data)) + nc;
			tmp_buffer[2] = m_filepara->pic_buffer[oc++];
			tmp_buffer[1] = m_filepara->pic_buffer[oc++];
			tmp_buffer[0] = m_filepara->pic_buffer[oc++];
			tmp_buffer[3] = m_filepara->pic_buffer[oc++];
		}
		
		if(m_filepara->ox < m_filepara->max_x)
		{
			for(b=0; b<h_x; b++, nc+=4)
			{
				tmp_buffer=((unsigned char *)(surface->data)) + nc;
				memcpy(tmp_buffer, m_conf.background, sizeof(m_conf.background));
			}
		}
	}
	
	if(m_filepara->oy < m_filepara->max_y)
	{
		for(a=0; a<(u_y*m_filepara->ox); a++, nc+=4)
		{
			tmp_buffer=((unsigned char *)(surface->data)) + nc;
			memcpy(tmp_buffer, m_conf.background, sizeof(m_conf.background));
		}
	}
	
	surface->clut.data=0;
	surface->clut.colors=0;
	surface->clut.start=0;

	delete m_filepara;
	m_filepara = NULL;

	return 0;
}

RESULT ePicLoad::setPara(PyObject *val)
{
	if (!PySequence_Check(val))
		return 0;
	if (PySequence_Size(val) < 7)
		return 0;
	else {
		ePyObject fast = PySequence_Fast(val, "");
		m_conf.max_x		= PyInt_AsLong( PySequence_Fast_GET_ITEM(fast, 0));
		m_conf.max_y		= PyInt_AsLong( PySequence_Fast_GET_ITEM(fast, 1));
		m_conf.aspect_ratio	= (double)PyInt_AsLong( PySequence_Fast_GET_ITEM(fast, 2)) / PyInt_AsLong(PySequence_Fast_GET_ITEM(fast, 3));
		m_conf.usecache		= PyInt_AsLong( PySequence_Fast_GET_ITEM(fast, 4));
		m_conf.resizetype	= PyInt_AsLong( PySequence_Fast_GET_ITEM(fast, 5));
		const char *bg_str	= PyString_AsString( PySequence_Fast_GET_ITEM(fast, 6));
	
		if(bg_str[0] == '#' && strlen(bg_str)==9)
		{
			int bg = strtoul(bg_str+1, NULL, 16);
			m_conf.background[0] = bg&0xFF;		//BB
			m_conf.background[1] = (bg>>8)&0xFF;	//GG
			m_conf.background[2] = (bg>>16)&0xFF;	//RR
			m_conf.background[3] = bg>>24;		//AA
		}
		eDebug("[Picload] setPara max-X=%d max-Y=%d aspect_ratio=%lf cache=%d resize=%d bg=#%02X%02X%02X%02X", m_conf.max_x, m_conf.max_y, m_conf.aspect_ratio, (int)m_conf.usecache, (int)m_conf.resizetype, m_conf.background[3], m_conf.background[2], m_conf.background[1], m_conf.background[0]);
	}
	return 1;
}

//------------------------------------------------------------------------------------

//for old plugins
SWIG_VOID(int) loadPic(ePtr<gPixmap> &result, std::string filename, int x, int y, int aspect, int resize_mode, int rotate, int background, std::string cachefile)
{
	long asp1, asp2;
	result = 0;
	eDebug("deprecated loadPic function used!!! please use the non blocking version! you can see demo code in Pictureplayer plugin... this function is removed in the near future!");
	ePicLoad mPL;

	switch(aspect)
	{
		case 1:		asp1 = 16*576, asp2 = 9*720; break; //16:9
		case 2:		asp1 = 16*576, asp2 = 10*720; break; //16:10
		case 3:		asp1 = 5*576, asp2 = 4*720; break; //5:4
		default:	asp1 = 4*576, asp2 = 3*720; break; //4:3
	}

	ePyObject tuple = PyTuple_New(7);
	PyTuple_SET_ITEM(tuple, 0,  PyLong_FromLong(x));
	PyTuple_SET_ITEM(tuple, 1,  PyLong_FromLong(y));
	PyTuple_SET_ITEM(tuple, 2,  PyLong_FromLong(asp1));
	PyTuple_SET_ITEM(tuple, 3,  PyLong_FromLong(asp2));
	PyTuple_SET_ITEM(tuple, 4,  PyLong_FromLong(0));
	PyTuple_SET_ITEM(tuple, 5,  PyLong_FromLong(resize_mode));
	if(background)
		PyTuple_SET_ITEM(tuple, 6,  PyString_FromString("#ff000000"));
	else
		PyTuple_SET_ITEM(tuple, 6,  PyString_FromString("#00000000"));

	mPL.setPara(tuple);

	if(!mPL.startDecode(filename.c_str(), 0, 0, false))
		mPL.getData(result);

	return 0;
}
