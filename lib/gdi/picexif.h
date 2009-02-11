#ifndef __exif_h__
#define __exif_h__

#include <stdlib.h>
#include <memory.h>
#include <string.h>
#include <stdio.h>

#define MAX_COMMENT 1000
#define MAX_SECTIONS 20
#define THUMBNAILTMPFILE "/tmp/.thumbcache"

typedef struct tag_ExifInfo {
	char  Version        [5];
	char  CameraMake     [32];
	char  CameraModel    [40];
	char  DateTime       [20];
	char  Orientation    [20];
	char  MeteringMode   [30];
	char  Comments[MAX_COMMENT];
	char  FlashUsed      [20];
	char  IsColor        [5];
	char  ResolutionUnit [20];
	char  ExposureProgram[30];
	char  LightSource    [20];
	float Xresolution;
	float Yresolution;
	float Brightness;
	float ExposureTime;
	float ExposureBias;
	float Distance;
	float CCDWidth;
	float FocalplaneXRes;
	float FocalplaneYRes;
	float FocalplaneUnits;
	float FocalLength;
	float ApertureFNumber;
	int   Height, Width;
	int   CompressionLevel;
	int   ISOequivalent;
	int   Process;
	int   Orient;
	//unsigned char *ThumbnailPointer;
	//unsigned ThumbnailSize;
	bool  IsExif;
	int Thumnailstate;
} EXIFINFO;

static const int BytesPerFormat[] = {0,1,1,2,4,8,1,1,2,4,8,4,8};

class Cexif
{
	typedef struct tag_Section_t{
	unsigned char* Data;
	int Type;
	unsigned Size;
	} Section_t;
public:
	EXIFINFO* m_exifinfo;
	char m_szLastError[256];
	Cexif();
	~Cexif();
	bool DecodeExif(const char *filename, int Thumb=0);
	void ClearExif();
protected:
	bool process_EXIF(unsigned char * CharBuf, unsigned int length);
	void process_COM (const unsigned char * Data, int length);
	void process_SOFn (const unsigned char * Data, int marker);
	int Get16u(void * Short);
	int Get16m(void * Short);
	long Get32s(void * Long);
	unsigned long Get32u(void * Long);
	double ConvertAnyFormat(void * ValuePtr, int Format);
	bool ProcessExifDir(unsigned char * DirStart, unsigned char * OffsetBase, unsigned ExifLength, EXIFINFO * const pInfo, unsigned 	char ** const LastExifRefdP);
	int ExifImageWidth;
	int MotorolaOrder;
	Section_t Sections[MAX_SECTIONS];
	int SectionsRead;
	bool freeinfo;
};

#endif// __exif_h__
