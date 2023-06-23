/*
	Neutrino-GUI  -   DBoxII-Project
	
	$Id: color.h 2013/10/12 mohousch Exp $

	Copyright (C) 2001 Steffen Hehn 'McClean'
	Homepage: http://dbox.cyberphoria.org/

	Kommentar:

	Diese GUI wurde von Grund auf neu programmiert und sollte nun vom
	Aufbau und auch den Ausbaumoeglichkeiten gut aussehen. Neutrino basiert
	auf der Client-Server Idee, diese GUI ist also von der direkten DBox-
	Steuerung getrennt. Diese wird dann von Daemons uebernommen.


	License: GPL

	This program is free software; you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation; either version 2 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program; if not, write to the Free Software
	Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
*/


#ifndef __color__
#define __color__

#include <stdint.h>
#include "gpixmap.h"

// gradient mode
enum {
	DARK2LIGHT,
	LIGHT2DARK,
	DARK2LIGHT2DARK,
	LIGHT2DARK2LIGHT
};

// gradient intensity
enum {
	INT_LIGHT,
	INT_NORMAL,
	INT_EXTENDED
};

// gradient type
enum {
	GRADIENT_COLOR2TRANSPARENT,
	GRADIENT_ONECOLOR,
	GRADIENT_COLOR2COLOR
};


//
int convertSetupColor2RGB(unsigned char r, unsigned char g, unsigned char b);
int convertSetupAlpha2Alpha(unsigned char alpha);

//
typedef struct {
	uint8_t r;
	uint8_t g;
	uint8_t b;
} RgbColor;

typedef struct {
	float h;
	float s;
	float v;
} HsvColor;

uint8_t limitChar(int c);
uint8_t getBrightnessRGB(uint32_t color);
uint32_t changeBrightnessRGBRel(uint32_t color, int br, bool transp=true);
uint32_t changeBrightnessRGB(uint32_t color, uint8_t br, bool transp=true);
uint32_t Hsv2SysColor(HsvColor *hsv, uint8_t tr=0xFF);
uint8_t SysColor2Hsv(uint32_t color, HsvColor *hsv);
void Hsv2Rgb(HsvColor *hsv, RgbColor *rgb);
void Rgb2Hsv(RgbColor *rgb, HsvColor *hsv);

uint32_t* gradientColorToTransparent(const gRGB &grad_col, uint32_t *gradientBuf, int bSize, int mode, int intensity = INT_LIGHT);

uint32_t* gradientOneColor(const gRGB &grad_col, uint32_t *gradientBuf, int bSize, int mode, int intensity = INT_LIGHT, uint8_t v_min = 0x40, uint8_t v_max = 0xE0, uint8_t s = 0xC0);

uint32_t* gradientColorToColor(const gRGB &start_grad_col, const gRGB &end_grad_col, uint32_t *gradientBuf, int bSize, int mode = DARK2LIGHT, int intensity = INT_LIGHT);

//
inline uint32_t make16color(__u32 rgb)
{
        return 0xFF000000 | rgb;
}

// for lua until 
inline uint32_t make16Color(unsigned int rgb)
{
	uint32_t col = 0xFF000000 | rgb;
	
        return col;
}

inline uint32_t convertSetupColor2Color(unsigned char r, unsigned char g, unsigned char b, unsigned char alpha)
{
	int color = convertSetupColor2RGB(r, g, b);
	int tAlpha = (alpha ? (convertSetupAlpha2Alpha(alpha)) : 0);

	if(!alpha) 
		tAlpha = 0xFF;

	uint32_t col = ((tAlpha << 24) & 0xFF000000) | color;
	
	return col;
}

#endif


