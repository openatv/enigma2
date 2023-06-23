/*
	Neutrino-GUI  -   DBoxII-Project
 
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

#include <stdio.h>
#include <math.h>

#include <lib/gdi/color.h>

#ifndef FLT_EPSILON
#define FLT_EPSILON 1E-5
#endif

int convertSetupColor2RGB(const unsigned char r, const unsigned char g, const unsigned char b)
{
	unsigned char red =	(int)r * 255 / 100;
	unsigned char green =	(int)g * 255 / 100;
	unsigned char blue =	(int)b * 255 / 100;

	return (red << 16) | (green << 8) | blue;
}

int convertSetupAlpha2Alpha(unsigned char alpha)
{
	if(alpha == 0) 
		return 0xFF;
	else if(alpha >= 100) 
		return 0;
	
	int a = 100 - alpha;
	int ret = a * 0xFF / 100;
	
	return ret;
}

uint8_t limitChar(int c)
{
	uint8_t ret;
	
	if (c < 0) 
		ret = 0;
	else if (c > 0xFF) 
		ret = 0xFF;
	else 
		ret = (uint8_t)c;
	
	return ret;
}

uint8_t getBrightnessRGB(uint32_t color)
{
	RgbColor rgb;
	rgb.r  = (uint8_t)((color & 0x00FF0000) >> 16);
	rgb.g  = (uint8_t)((color & 0x0000FF00) >>  8);
	rgb.b  = (uint8_t) (color & 0x000000FF);

	return rgb.r > rgb.g ? (rgb.r > rgb.b ? rgb.r : rgb.b) : (rgb.g > rgb.b ? rgb.g : rgb.b);
}

uint32_t changeBrightnessRGBRel(uint32_t color, int br, bool transp)
{
	int br_ = (int)getBrightnessRGB(color);
	br_ += br;
	if (br_ < 0) br_ = 0;
	if (br_ > 255) br_ = 255;
	return changeBrightnessRGB(color, (uint8_t)br_, transp);
}

uint32_t changeBrightnessRGB(uint32_t color, uint8_t br, bool transp)
{
	HsvColor hsv;
	uint8_t tr = SysColor2Hsv(color, &hsv);
	hsv.v = (float)br / (float)255;
	if (!transp)
		tr = 0xFF;
	return Hsv2SysColor(&hsv, tr);
}

uint32_t Hsv2SysColor(HsvColor *hsv, uint8_t tr)
{
	RgbColor rgb;
	Hsv2Rgb(hsv, &rgb);
	return (((tr    << 24) & 0xFF000000) |
		((rgb.r << 16) & 0x00FF0000) |
		((rgb.g <<  8) & 0x0000FF00) |
		((rgb.b      ) & 0x000000FF));
}

uint8_t SysColor2Hsv(uint32_t color, HsvColor *hsv)
{
	uint8_t tr;
	RgbColor rgb;
	tr     = (uint8_t)((color & 0xFF000000) >> 24);
	rgb.r  = (uint8_t)((color & 0x00FF0000) >> 16);
	rgb.g  = (uint8_t)((color & 0x0000FF00) >>  8);
	rgb.b  = (uint8_t) (color & 0x000000FF);
	Rgb2Hsv(&rgb, hsv);
	return tr;
}

void Hsv2Rgb(HsvColor *hsv, RgbColor *rgb)
{
	float f_H = hsv->h;
	float f_S = hsv->s;
	float f_V = hsv->v;
	if (fabsf(f_S) < FLT_EPSILON) {
		rgb->r = (uint8_t)(f_V * 255);
		rgb->g = (uint8_t)(f_V * 255);
		rgb->b = (uint8_t)(f_V * 255);

	} else {
		float f_R;
		float f_G;
		float f_B;
		float hh = f_H;
		if (hh >= 360) hh = 0;
		hh /= 60;
		int i = (int)hh;
		float ff = hh - (float)i;
		float p = f_V * (1 - f_S);
		float q = f_V * (1 - (f_S * ff));
		float t = f_V * (1 - (f_S * (1 - ff)));

		switch (i) {
			case 0:
				f_R = f_V; f_G = t; f_B = p;
				break;
			case 1:
				f_R = q; f_G = f_V; f_B = p;
				break;
			case 2:
				f_R = p; f_G = f_V; f_B = t;
				break;
			case 3:
				f_R = p; f_G = q; f_B = f_V;
				break;
			case 4:
				f_R = t; f_G = p; f_B = f_V;
				break;
			case 5:
			default:
				f_R = f_V; f_G = p; f_B = q;
				break;
		}
		rgb->r = (uint8_t)(f_R * 255);
		rgb->g = (uint8_t)(f_G * 255);
		rgb->b = (uint8_t)(f_B * 255);
	}
}

void Rgb2Hsv(RgbColor *rgb, HsvColor *hsv)
{
	float f_R = (float)rgb->r / (float)255;
	float f_G = (float)rgb->g / (float)255;
	float f_B = (float)rgb->b / (float)255;

	float min = f_R < f_G ? (f_R < f_B ? f_R : f_B) : (f_G < f_B ? f_G : f_B);
	float max = f_R > f_G ? (f_R > f_B ? f_R : f_B) : (f_G > f_B ? f_G : f_B);
	float delta = max - min;

	float f_V = max;
	float f_H = 0;
	float f_S = 0;

	if (fabsf(delta) < FLT_EPSILON) 
	{ 
		//gray
		f_S = 0;
		f_H = 0;
	} 
	else 
	{
		f_S = (delta / max);
		if (f_R >= max)
			f_H = (f_G - f_B) / delta;
		else if (f_G >= max)
			f_H = 2 + (f_B - f_R) / delta;
		else
			f_H = 4 + (f_R - f_G) / delta;

		f_H *= 60;
		if (f_H < 0)
			f_H += 360;
	}
	hsv->h = f_H;
	hsv->s = f_S;
	hsv->v = f_V;
}

uint32_t* gradientColorToTransparent(const gRGB &grad_col, uint32_t *gradientBuf, int bSize, int /*mode*/, int /*intensity*/)
{
	if (gradientBuf == NULL) 
	{
		gradientBuf = (uint32_t*) malloc(bSize * sizeof(uint32_t));
		
		if (gradientBuf == NULL) 
		{
			return NULL;
		}
	}

	uint32_t col = grad_col.argb();
	col^=0xFF000000;
	
	memset((void*)gradientBuf, '\0', bSize * sizeof(uint32_t));

	int start_box = 0;
	int end_box = bSize;
	uint8_t tr_min = 0xFF;
	uint8_t tr_max = 0x20;
	float factor = (float)(tr_min - tr_max) / (float)(end_box - start_box);

	for (int i = start_box; i < end_box; i++) 
	{

		uint8_t tr = limitChar((int)(factor * (float)i + tr_max) + 1);
		uint8_t r  = (uint8_t)((col & 0x00FF0000) >> 16);
		uint8_t g  = (uint8_t)((col & 0x0000FF00) >>  8);
		uint8_t b  = (uint8_t) (col & 0x000000FF);

		gradientBuf[i] = ((tr << 24) & 0xFF000000) |
			         ((r  << 16) & 0x00FF0000) |
			         ((g  <<  8) & 0x0000FF00) |
			         ( b         & 0x000000FF);
	}

	return gradientBuf;
}

uint32_t* gradientOneColor(const gRGB &grad_col, uint32_t *gradientBuf, int bSize, int mode, int intensity, uint8_t v_min, uint8_t v_max, uint8_t s)
{
	if (gradientBuf == NULL) 
	{
		gradientBuf = (uint32_t*) malloc(bSize * sizeof(uint32_t));
		
		if (gradientBuf == NULL) 
		{
			return NULL;
		}
	}

	uint32_t col = grad_col.argb();
	col^=0xFF000000;
	
	memset((void*)gradientBuf, '\0', bSize * sizeof(uint32_t));

	HsvColor hsv;
	uint8_t min_v = 0, max_v = 0, col_s = 0;
	uint8_t start_v = 0 , end_v = 0;

	uint8_t tr = SysColor2Hsv(col, &hsv);
	bool noSaturation = (hsv.s <= (float)0.05);

	if (intensity == INT_EXTENDED) 
	{
		min_v   = v_min;
		max_v   = v_max;
		col_s   = s;
	}
	else 
	{
		switch (intensity) 
		{
			case INT_LIGHT:
				min_v   = 0x40;
				max_v   = 0xE0;
				col_s   = (noSaturation) ? 0 : 0xC0;
				break;
			case INT_NORMAL:
				min_v   = 0x00;
				max_v   = 0xFF;
				col_s   = (noSaturation) ? 0 : 0xC0;
				break;
		}
	}

	switch (mode) 
	{
		case DARK2LIGHT:
		case DARK2LIGHT2DARK:
			start_v = min_v;
			end_v   = max_v;
			break;
		case LIGHT2DARK:
		case LIGHT2DARK2LIGHT:
			start_v = max_v;
			end_v   = min_v;
			break;
		default:
			return 0;
	}

	int bSize1 = ((mode == DARK2LIGHT2DARK) || (mode == LIGHT2DARK2LIGHT)) ? bSize/2 : bSize;

	int v  = start_v; int v_ = v;
	float factor_v = ((float)end_v - (float)v) / (float)bSize1;

	for (int i = 0; i < bSize1; i++) 
	{
		v = v_ + (int)(factor_v * (float)i);
		hsv.v = (float)limitChar(v) / (float)255;
		hsv.s = (float)col_s / (float)255;
		gradientBuf[i] = Hsv2SysColor(&hsv, tr);
	}

	if ((mode == DARK2LIGHT2DARK) || (mode == LIGHT2DARK2LIGHT)) 
	{
		bSize1 = bSize - bSize1;
		for (int i = 0; i < bSize1; i++) 
		{
			v = v_ + (int)(factor_v * (float)i);
			hsv.v = (float)limitChar(v) / (float)255;
			hsv.s = (float)col_s / (float)255;
			gradientBuf[bSize - i - 1] = Hsv2SysColor(&hsv, tr);
		}
	}

	return gradientBuf;
}

uint32_t* gradientColorToColor(const gRGB &start_grad_col,const gRGB &end_grad_col, uint32_t *gradientBuf, int bSize, int mode, int /*intensity*/)
{
	if (gradientBuf == NULL) 
	{
		gradientBuf = (uint32_t*) malloc(bSize * sizeof(uint32_t));
		
		if (gradientBuf == NULL) 
		{
			return NULL;
		}
	}

	uint32_t start_col = start_grad_col.argb();
	start_col^=0xFF000000;

	uint32_t end_col = end_grad_col.argb();
	end_col^=0xFF000000;
	
	memset((void*)gradientBuf, '\0', bSize * sizeof(uint32_t));

	int start_box = 0;
	int end_box = bSize;

	uint32_t temp_col = end_col;
	end_col =  start_col;
	start_col = temp_col;

	if (mode == DARK2LIGHT)
	{
		temp_col = start_col;
		start_col = end_col;
		end_col = temp_col;
	}

	uint8_t start_tr = (uint8_t)((start_col & 0xFF000000) >> 24);
	uint8_t start_r  = (uint8_t)((start_col & 0x00FF0000) >> 16);
	uint8_t start_g  = (uint8_t)((start_col & 0x0000FF00) >>  8);
	uint8_t start_b  = (uint8_t) (start_col & 0x000000FF);

	uint8_t end_tr = (uint8_t)((end_col & 0xFF000000) >> 24);
	uint8_t end_r  = (uint8_t)((end_col & 0x00FF0000) >> 16);
	uint8_t end_g  = (uint8_t)((end_col & 0x0000FF00) >>  8);
	uint8_t end_b  = (uint8_t) (end_col & 0x000000FF);

	float steps = (float) bSize;

	float trStep = (float)(end_tr - start_tr) / steps;
	float rStep = (float)(end_r - start_r) / steps;
	float gStep = (float)(end_g - start_g) / steps;
	float bStep = (float)(end_b - start_b) / steps;

	for (int i = start_box; i < end_box; i++) 
	{

		uint8_t tr = limitChar((int)((float)start_tr + trStep*(float)i));
		uint8_t r  = limitChar((int)((float)start_r + rStep*(float)i));
		uint8_t g  = limitChar((int)((float)start_g + gStep*(float)i));
		uint8_t b  = limitChar((int)((float)start_b + bStep*(float)i));

		gradientBuf[i] = ((tr << 24) & 0xFF000000) |
			         ((r  << 16) & 0x00FF0000) |
			         ((g  <<  8) & 0x0000FF00) |
			         ( b         & 0x000000FF);
	}

	return gradientBuf;
}






