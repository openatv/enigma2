#include <lib/base/cfile.h>
#include <lib/base/eerror.h>
#include <lib/gdi/picexif.h>
#define PNG_SKIP_SETJMP_CHECK
#include <png.h>

#define M_SOF0  0xC0
#define M_SOF1  0xC1
#define M_SOF2  0xC2
#define M_SOF3  0xC3
#define M_SOF5  0xC5
#define M_SOF6  0xC6
#define M_SOF7  0xC7
#define M_SOF9  0xC9
#define M_SOF10 0xCA
#define M_SOF11 0xCB
#define M_SOF13 0xCD
#define M_SOF14 0xCE
#define M_SOF15 0xCF
#define M_SOI   0xD8
#define M_EOI   0xD9
#define M_SOS   0xDA
#define M_JFIF  0xE0
#define M_EXIF  0xE1
#define M_COM   0xFE

#define NUM_FORMATS   12
#define FMT_BYTE       1
#define FMT_STRING     2
#define FMT_USHORT     3
#define FMT_ULONG      4
#define FMT_URATIONAL  5
#define FMT_SBYTE      6
#define FMT_UNDEFINED  7
#define FMT_SSHORT     8
#define FMT_SLONG      9
#define FMT_SRATIONAL 10
#define FMT_SINGLE    11
#define FMT_DOUBLE    12

#define TAG_EXIF_VERSION      0x9000
#define TAG_EXIF_OFFSET       0x8769
#define TAG_INTEROP_OFFSET    0xa005
#define TAG_MAKE              0x010F
#define TAG_MODEL             0x0110
#define TAG_ORIENTATION       0x0112
#define TAG_XRESOLUTION       0x011A
#define TAG_YRESOLUTION       0x011B
#define TAG_RESOLUTIONUNIT    0x0128
#define TAG_EXPOSURETIME      0x829A
#define TAG_FNUMBER           0x829D
#define TAG_SHUTTERSPEED      0x9201
#define TAG_APERTURE          0x9202
#define TAG_BRIGHTNESS        0x9203
#define TAG_MAXAPERTURE       0x9205
#define TAG_FOCALLENGTH       0x920A
#define TAG_DATETIME_ORIGINAL 0x9003
#define TAG_USERCOMMENT       0x9286
#define TAG_SUBJECT_DISTANCE  0x9206
#define TAG_FLASH             0x9209
#define TAG_FOCALPLANEXRES    0xa20E
#define TAG_FOCALPLANEYRES    0xa20F
#define TAG_FOCALPLANEUNITS   0xa210
#define TAG_EXIF_IMAGEWIDTH   0xA002
#define TAG_EXIF_IMAGELENGTH  0xA003
#define TAG_EXPOSURE_BIAS     0x9204
#define TAG_WHITEBALANCE      0x9208
#define TAG_METERING_MODE     0x9207
#define TAG_EXPOSURE_PROGRAM  0x8822
#define TAG_ISO_EQUIVALENT    0x8827
#define TAG_COMPRESSION_LEVEL 0x9102
#define TAG_THUMBNAIL_OFFSET  0x0201
#define TAG_THUMBNAIL_LENGTH  0x0202


Cexif::Cexif()
{
	m_exifinfo = NULL;
	Data = NULL;
}

Cexif::~Cexif()
{
}

void Cexif::ClearExif()
{
	if (Data)
		free(Data);
	if (m_exifinfo)
		delete m_exifinfo;
}

bool Cexif::DecodeExif(const char * filename, int Thumb, int fileType)
{
	m_exifinfo = new EXIFINFO;
	memset(m_exifinfo, 0, sizeof(EXIFINFO));
	m_exifinfo->Thumnailstate = Thumb;
	m_szLastError[0] = '\0';

	bool rc;
	if (fileType == F_JPEG)
		rc = DecodeExifJpeg(filename);
	else if (fileType == F_PNG)
		rc = DecodeExifPNG(filename);
	else {
		eDebug("[DecodeEXIF]: unsupported filetype %d", fileType);
		return false;
	}
	// eDebug("[DecodeEXIF]: file parser rc=%d, %s", rc, m_szLastError);
	return rc;
}

bool Cexif::DecodeExifJpeg(const char * filename)
{
	eDebug("[EXIF] getting exif from JPEG");
	int HaveCom = 0;
	CFile hFile(filename, "rb");
	if (!hFile) {
		strcpy(m_szLastError, "Cannot open image file: %m");
		return false;
	}
	int a = fgetc(hFile);

	if (a != 0xff || fgetc(hFile) != M_SOI) {
		strcpy(m_szLastError, "Not a JPEG file");
		return false;
	}

	for (;;)
	{
		int marker = 0;
		unsigned int ll, lh, itemlen;

		for (a = 0; a < 7; a++)
		{
			marker = fgetc(hFile);
			if (marker != 0xff)
				break;
		}

		if (marker == 0xff)
		{
			strcpy(m_szLastError, "Too many padding unsigned chars!");
			return false;
		}

		lh = fgetc(hFile);
		ll = fgetc(hFile);

		itemlen = (lh << 8) | ll;
		if (itemlen < 2)
		{
			strcpy(m_szLastError, "Marker too short");
			return false;
		}

		if (Data)
			free(Data);
		itemlen -= 2;
		Data = (unsigned char *)malloc(itemlen);
		if (Data == NULL)
		{
			strcpy(m_szLastError, "Could not allocate memory");
			return false;
		}

		if (fread(Data, 1, itemlen, hFile) != itemlen)
		{
			strcpy(m_szLastError, "Premature end of file?");
			return false;
		}

		switch(marker)
		{
		case M_SOS:
			return true;
		case M_EOI:
			eDebug("[Cexif] No image in jpeg!\n");
			return false;
		case M_COM:
			if (!HaveCom)
			{
				process_COM(Data, itemlen);
				HaveCom = 1;
			}
			break;
		case M_JFIF:
			break;
		case M_EXIF:
			if (memcmp(Data, "Exif", 4) == 0)
				m_exifinfo->IsExif = process_EXIF(Data, itemlen);
			break;
		case M_SOF0:
		case M_SOF1:
		case M_SOF2:
		case M_SOF3:
		case M_SOF5:
		case M_SOF6:
		case M_SOF7:
		case M_SOF9:
		case M_SOF10:
		case M_SOF11:
		case M_SOF13:
		case M_SOF14:
		case M_SOF15:
			process_SOFn(Data, marker);
			break;
		default:
			break;
		}
	}

	return true;
}

bool Cexif::DecodeExifPNG(const char * filename)
{
	png_uint_32 width, height;
	int bit_depth, color_type, channels;
	CFile hFile(filename, "rb");

	if (!hFile) {
		strcpy(m_szLastError, "Cannot open image file: %m");
		return false;
	}

	eDebug("[EXIF] getting exif from PNG");
	strcpy(m_szLastError, "Cannot get PNG EXIF data");
	png_structp png_ptr = png_create_read_struct(PNG_LIBPNG_VER_STRING, NULL, NULL, NULL);
	if (png_ptr == NULL)
		return false;
	png_infop info_ptr = png_create_info_struct(png_ptr);
	if (info_ptr == NULL) {
		png_destroy_read_struct(&png_ptr, (png_infopp)NULL, (png_infopp)NULL);
		return false;
	}

	if (setjmp(png_jmpbuf(png_ptr))) {
		png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);
		return false;
	}

	png_init_io(png_ptr, hFile);
	png_read_info(png_ptr, info_ptr);
	png_get_IHDR(png_ptr, info_ptr, &width, &height, &bit_depth, &color_type, NULL, NULL, NULL);
	channels = png_get_channels(png_ptr, info_ptr);

	png_byte *row = (unsigned char*) malloc(width * channels*bit_depth/8);
	for (png_uint_32 i = 0; i < height; i++)
		png_read_row(png_ptr, row, NULL);
	png_read_end(png_ptr, info_ptr);

	png_textp text_ptr;
	int num_text;
	if (png_get_text(png_ptr, info_ptr, &text_ptr, &num_text)) {
		// eDebug("[PNGtext] %d text chunks", num_text);
		for (int i = 0; i< num_text; i++) {
			char * s = text_ptr[i].text;
			if (!strcmp(text_ptr[i].key, "Raw profile type exif")) {
				int size;
				// eDebug("Found exif key");
				if (sscanf(s, "\nexif\n%d\n", &size) == 1) {
					s = strchr(s, '\n');
					s++;
					s = strchr(s, '\n');
					s++;
					s = strchr(s, '\n');
					s++;
					unsigned char *Data = (unsigned char *)malloc(size);
					unsigned char * d = Data;
					while (*s && *(s + 1)) {
						int x = *s++;
						int y = *s++;
						if (x > 0x39)
							x += 9;
						if (y > 0x39)
							y += 9;
						*d++ = ((x & 0xf) << 4) | (y & 0xf);
						if (*s == '\n')
							s++;
					}
					m_szLastError[0] = '\0';
					m_exifinfo->IsExif = process_EXIF(Data, size);
				}
			}
			else if (!strcmp(text_ptr[i].key, "exif:ImageWidth"))
				m_exifinfo->Width  = atoi(s);
			else if (!strcmp(text_ptr[i].key, "exif:ImageLength"))
				m_exifinfo->Height = atoi(s);
			//else
			//	eDebug("[PNGtext] %d compression=%d len=%d key=%s text=%s",
			//		i, text_ptr[i].compression,
			//		text_ptr[i].text_length,
			//		text_ptr[i].key,
			//		s);
		}
	}
	png_destroy_read_struct(&png_ptr, &info_ptr, (png_infopp)NULL);

	return true;
}


bool Cexif::process_EXIF(unsigned char * CharBuf, unsigned int length)
{
	m_exifinfo->Comments[0] = '\0';
	ExifImageWidth = 0;

	static const unsigned char ExifHeader[] = "Exif\0\0";
	if (memcmp(CharBuf+0, ExifHeader, 6))
	{
		strcpy(m_szLastError, "Incorrect Exif header");
		return false;
	}

	if (memcmp(CharBuf+6, "II", 2) == 0)
		MotorolaOrder = 0;
	else if (memcmp(CharBuf+6, "MM", 2) == 0)
		MotorolaOrder = 1;
	else
	{
		strcpy(m_szLastError, "Invalid Exif alignment marker");
		return false;
	}

	if (Get16u(CharBuf+8) != 0x2a)
	{
		strcpy(m_szLastError, "Invalid Exif start (1)");
		return false;
	}
	int FirstOffset = Get32u(CharBuf+10);
	if (FirstOffset < 8 || FirstOffset > 16)
	{
		strcpy(m_szLastError, "Suspicious offset of first IFD value");
		return false;
	}
	unsigned char * LastExifRefd = CharBuf;

	if (!ProcessExifDir(CharBuf+14, CharBuf+6, length-6, &LastExifRefd))
		return false;

	if (m_exifinfo->FocalplaneXRes != 0)
		m_exifinfo->CCDWidth = (float)(ExifImageWidth * m_exifinfo->FocalplaneUnits / m_exifinfo->FocalplaneXRes);

	return true;
}

int Cexif::Get16m(void * Short)
{
	return (((unsigned char *)Short)[0] << 8) | ((unsigned char *)Short)[1];
}

int Cexif::Get16u(void * Short)
{
	if (MotorolaOrder)
		return (((unsigned char *)Short)[0] << 8) | ((unsigned char *)Short)[1];
	else
		return (((unsigned char *)Short)[1] << 8) | ((unsigned char *)Short)[0];
}

long Cexif::Get32s(void * Long)
{
	if (MotorolaOrder)
        	return  ((( char *)Long)[0] << 24) | (((unsigned char *)Long)[1] << 16) | (((unsigned char *)Long)[2] << 8 ) | (((unsigned char *)Long)[3] << 0 );
	else
        	return  ((( char *)Long)[3] << 24) | (((unsigned char *)Long)[2] << 16) | (((unsigned char *)Long)[1] << 8 ) | (((unsigned char *)Long)[0] << 0 );
}

unsigned long Cexif::Get32u(void * Long)
{
	return (unsigned long)Get32s(Long) & 0xffffffff;
}

bool Cexif::ProcessExifDir(unsigned char * DirStart, unsigned char * OffsetBase, unsigned ExifLength, unsigned char ** const LastExifRefdP )
{
	int de, a, NumDirEntries;
	unsigned ThumbnailOffset = 0;
	unsigned ThumbnailSize = 0;

	NumDirEntries = Get16u(DirStart);

	if ((DirStart+2+NumDirEntries*12) > (OffsetBase+ExifLength))
	{
		strcpy(m_szLastError, "Illegally sized directory");
		return false;
	}

	for (de=0; de<NumDirEntries; de++)
	{
		int Tag, Format, Components;
		unsigned char * ValuePtr;
		int BytesCount;
		unsigned char * DirEntry;

		DirEntry = DirStart+2+12*de;
		Tag = Get16u(DirEntry);
		Format = Get16u(DirEntry+2);
		Components = Get32u(DirEntry+4);

		if ((Format-1) >= NUM_FORMATS)
		{
			strcpy(m_szLastError, "Illegal format code in EXIF dir");
			return false;
		}

		BytesCount = Components * BytesPerFormat[Format];

        	if (BytesCount > 4)
		{
			unsigned OffsetVal;
			OffsetVal = Get32u(DirEntry+8);
        		if (OffsetVal+BytesCount > ExifLength)
			{
				strcpy(m_szLastError, "Illegal pointer offset value in EXIF");
				return false;
        		}
        		ValuePtr = OffsetBase+OffsetVal;
        	}
		else ValuePtr = DirEntry+8;

	        if (*LastExifRefdP < ValuePtr+BytesCount)
			*LastExifRefdP = ValuePtr+BytesCount;

        	switch(Tag)
		{
		case TAG_MAKE:
			strncpy(m_exifinfo->CameraMake, (char*)ValuePtr, 31);
			break;
		case TAG_MODEL:
			strncpy(m_exifinfo->CameraModel, (char*)ValuePtr, 39);
			break;
		case TAG_EXIF_VERSION:
			strncpy(m_exifinfo->Version, (char*)ValuePtr, 4);
			break;
		case TAG_DATETIME_ORIGINAL:
			strncpy(m_exifinfo->DateTime, (char*)ValuePtr, 19);
			break;
		case TAG_USERCOMMENT:
			a = BytesCount-1;
			while (a >= 0 && ValuePtr[a] == ' ')
				ValuePtr[a--] = '\0';
			if (memcmp(ValuePtr, "ASCII", 5) == 0)
			{
				for (a=5; a<10; a++)
				{
					char c = (char)ValuePtr[a];
					if (c != '\0' && c != ' ')
					{
						strncpy(m_exifinfo->Comments, (char*)ValuePtr+a, 199);
						break;
					}
				}

			}
			else
				strncpy(m_exifinfo->Comments, (char*)ValuePtr, 199);
			break;
		case TAG_FNUMBER:
			m_exifinfo->ApertureFNumber = (float)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_APERTURE:
		case TAG_MAXAPERTURE:
			if (m_exifinfo->ApertureFNumber == 0)
			{
				//m_exifinfo->ApertureFNumber = (float)exp(ConvertAnyFormat(ValuePtr, Format)*log(2)*0.5);
			}
			break;
		case TAG_BRIGHTNESS:
			m_exifinfo->Brightness = (float)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_FOCALLENGTH:
			m_exifinfo->FocalLength = (float)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_SUBJECT_DISTANCE:
			m_exifinfo->Distance = (float)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_EXPOSURETIME:
			m_exifinfo->ExposureTime = (float)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_SHUTTERSPEED:
			if (m_exifinfo->ExposureTime == 0)
			{
				//m_exifinfo->ExposureTime = (float) (1/exp(ConvertAnyFormat(ValuePtr, Format)*log(2)));
			}
			break;
		case TAG_FLASH:
			strcpy(m_exifinfo->FlashUsed, ((int)ConvertAnyFormat(ValuePtr, Format) & 7) ? "fire" : "not fired");
			break;
		case TAG_ORIENTATION:
			m_exifinfo->Orient = (int)ConvertAnyFormat(ValuePtr, Format);
			switch((int)ConvertAnyFormat(ValuePtr, Format))
			{
			case 1:	strcpy(m_exifinfo->Orientation, "Top-Left"); break;
			case 2:	strcpy(m_exifinfo->Orientation, "Top-Right"); break;
			case 3:	strcpy(m_exifinfo->Orientation, "Bottom-Right"); break;
			case 4:	strcpy(m_exifinfo->Orientation, "Bottom-Left"); break;
			case 5:	strcpy(m_exifinfo->Orientation, "Left-Top"); break;
			case 6:	strcpy(m_exifinfo->Orientation, "Right-Top"); break;
			case 7:	strcpy(m_exifinfo->Orientation, "Right-Bottom"); break;
			case 8:	strcpy(m_exifinfo->Orientation, "Left-Bottom"); break;
			default:strcpy(m_exifinfo->Orientation, "Undefined"); break;
			}
			break;
		case TAG_EXIF_IMAGELENGTH:
		case TAG_EXIF_IMAGEWIDTH:
			a = (int)ConvertAnyFormat(ValuePtr, Format);
			if (ExifImageWidth < a)
				ExifImageWidth = a;
			break;
		case TAG_FOCALPLANEXRES:
			m_exifinfo->FocalplaneXRes = (float)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_FOCALPLANEYRES:
			m_exifinfo->FocalplaneYRes = (float)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_RESOLUTIONUNIT:
			switch((int)ConvertAnyFormat(ValuePtr, Format))
			{
				case 2: strcpy(m_exifinfo->ResolutionUnit, "inches"); break;
				case 3: strcpy(m_exifinfo->ResolutionUnit, "centimeters"); break;
				default:strcpy(m_exifinfo->ResolutionUnit, "reserved");
			}
			break;
		case TAG_FOCALPLANEUNITS:
			switch((int)ConvertAnyFormat(ValuePtr, Format))
			{
				case 1: m_exifinfo->FocalplaneUnits = 1.0f; break;
				case 2: m_exifinfo->FocalplaneUnits = 1.0f; break;
				case 3: m_exifinfo->FocalplaneUnits = 0.3937007874f; break;
				case 4: m_exifinfo->FocalplaneUnits = 0.03937007874f; break;
				case 5: m_exifinfo->FocalplaneUnits = 0.00003937007874f;
			}
			break;
		case TAG_EXPOSURE_BIAS:
			m_exifinfo->ExposureBias = (float) ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_WHITEBALANCE:
			switch((int)ConvertAnyFormat(ValuePtr, Format))
			{
				case 0:  strcpy(m_exifinfo->LightSource, "unknown"); break;
				case 1:  strcpy(m_exifinfo->LightSource, "Daylight"); break;
				case 2:  strcpy(m_exifinfo->LightSource, "Fluorescent"); break;
				case 3:  strcpy(m_exifinfo->LightSource, "Tungsten"); break;
				case 17: strcpy(m_exifinfo->LightSource, "Standard light A"); break;
				case 18: strcpy(m_exifinfo->LightSource, "Standard light B"); break;
				case 19: strcpy(m_exifinfo->LightSource, "Standard light C"); break;
				case 20: strcpy(m_exifinfo->LightSource, "D55"); break;
				case 21: strcpy(m_exifinfo->LightSource, "D65"); break;
				case 22: strcpy(m_exifinfo->LightSource, "D75"); break;
				default: strcpy(m_exifinfo->LightSource, "other"); break;
			}
			break;
		case TAG_METERING_MODE:
			switch((int)ConvertAnyFormat(ValuePtr, Format))
			{
				case 0: strcpy(m_exifinfo->MeteringMode, "unknown"); break;
				case 1: strcpy(m_exifinfo->MeteringMode, "Average"); break;
				case 2: strcpy(m_exifinfo->MeteringMode, "Center-Weighted-Average"); break;
				case 3: strcpy(m_exifinfo->MeteringMode, "Spot"); break;
				case 4: strcpy(m_exifinfo->MeteringMode, "MultiSpot"); break;
				case 5: strcpy(m_exifinfo->MeteringMode, "Pattern"); break;
				case 6: strcpy(m_exifinfo->MeteringMode, "Partial"); break;
				default:strcpy(m_exifinfo->MeteringMode, "other"); break;
			}
			break;
		case TAG_EXPOSURE_PROGRAM:
			switch((int)ConvertAnyFormat(ValuePtr, Format))
			{
				case 0: strcpy(m_exifinfo->ExposureProgram, "not defined"); break;
				case 1: strcpy(m_exifinfo->ExposureProgram, "Manual"); break;
				case 2: strcpy(m_exifinfo->ExposureProgram, "Normal program"); break;
				case 3: strcpy(m_exifinfo->ExposureProgram, "Aperture priority"); break;
				case 4: strcpy(m_exifinfo->ExposureProgram, "Shutter priority"); break;
				case 5: strcpy(m_exifinfo->ExposureProgram, "Creative program"); break;
				case 6: strcpy(m_exifinfo->ExposureProgram, "Action program"); break;
				case 7: strcpy(m_exifinfo->ExposureProgram, "Portrait mode"); break;
				case 8: strcpy(m_exifinfo->ExposureProgram, "Landscape mode"); break;
				default:strcpy(m_exifinfo->ExposureProgram, "reserved"); break;
			}
			break;
		case TAG_ISO_EQUIVALENT:
			m_exifinfo->ISOequivalent = (int)ConvertAnyFormat(ValuePtr, Format);
			if (m_exifinfo->ISOequivalent < 50)
				m_exifinfo->ISOequivalent *= 200;
			break;
		case TAG_COMPRESSION_LEVEL:
			m_exifinfo->CompressionLevel = (int)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_XRESOLUTION:
			m_exifinfo->Xresolution = (float)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_YRESOLUTION:
			m_exifinfo->Yresolution = (float)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_THUMBNAIL_OFFSET:
			ThumbnailOffset = (unsigned)ConvertAnyFormat(ValuePtr, Format);
			break;
		case TAG_THUMBNAIL_LENGTH:
			ThumbnailSize = (unsigned)ConvertAnyFormat(ValuePtr, Format);
			break;
		//default:
		//	eDebug("[picexif] unsupported tag %d format %d: %d components %d bytes)", Tag, Format, Components, BytesCount);
		}

		if (Tag == TAG_EXIF_OFFSET || Tag == TAG_INTEROP_OFFSET)
		{
			unsigned char * SubdirStart;
			SubdirStart = OffsetBase + Get32u(ValuePtr);
			if (SubdirStart < OffsetBase || SubdirStart > OffsetBase+ExifLength)
			{
				strcpy(m_szLastError, "Illegal subdirectory link");
				return false;
			}
			ProcessExifDir(SubdirStart, OffsetBase, ExifLength, LastExifRefdP);
			continue;
		}
	}

	unsigned char * SubdirStart;
	unsigned Offset;
	Offset = Get16u(DirStart+2+12*NumDirEntries);
	if (Offset)
	{
		SubdirStart = OffsetBase + Offset;
		if (SubdirStart < OffsetBase || SubdirStart > OffsetBase+ExifLength)
		{
			strcpy(m_szLastError, "Illegal subdirectory link");
			return false;
		}
		ProcessExifDir(SubdirStart, OffsetBase, ExifLength, LastExifRefdP);
        }

	if (ThumbnailSize && ThumbnailOffset && m_exifinfo->Thumnailstate)
	{
		if (ThumbnailSize + ThumbnailOffset <= ExifLength)
		{
			if (FILE *tf = fopen(THUMBNAILTMPFILE, "w"))
			{
				fwrite(OffsetBase + ThumbnailOffset, ThumbnailSize, 1, tf);
				fclose(tf);
				m_exifinfo->Thumnailstate = 2;
			}
		}
	}

	return true;
}

double Cexif::ConvertAnyFormat(void * ValuePtr, int Format)
{
	double Value = 0;

	switch(Format)
	{
		case FMT_SBYTE:		Value = *(signed char *)ValuePtr;	break;
		case FMT_BYTE:		Value = *(unsigned char *)ValuePtr;	break;
		case FMT_USHORT:	Value = Get16u(ValuePtr);		break;
		case FMT_ULONG:		Value = Get32u(ValuePtr);		break;
		case FMT_URATIONAL:
		case FMT_SRATIONAL:
		{
			int Num = Get32s(ValuePtr);
			int Den = Get32s(4+(char *)ValuePtr);
			if (Den == 0)
				Value = 0;
			else
				Value = (double)Num/Den;
			break;
		}
		case FMT_SSHORT:	Value = (signed short)Get16u(ValuePtr);	break;
		case FMT_SLONG:		Value = Get32s(ValuePtr);		break;
		case FMT_SINGLE:	Value = (double)*(float *)ValuePtr;	break;
		case FMT_DOUBLE:	Value = *(double *)ValuePtr;		break;
	}
	return Value;
}

void Cexif::process_COM (const unsigned char * Data, int length)
{
	char *Comment = m_exifinfo->Comments;

	if (length > MAX_COMMENT)
		length = MAX_COMMENT;

	for (int a = 0; a < length; a++)
	{
		char ch = (char) Data[a];
		if (ch == '\r' && Data[a+1] == '\n')
			continue;
		if (ch < 0x20 && ch != '\n' && ch != '\t')
			ch = '?';
		*Comment++ = ch;
	}
	*Comment = '\0';
}

void Cexif::process_SOFn (const unsigned char * Data, int marker)
{
	m_exifinfo->BitsPerColor = Data[0];
	m_exifinfo->Height = Get16m((void*)(Data+1));
	m_exifinfo->Width  = Get16m((void*)(Data+3));
	strcpy(m_exifinfo->IsColor, Data[5] == 3 ? "yes" : "no"); // color components
	m_exifinfo->Process = marker;
}

