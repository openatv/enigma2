#pragma once

#include <lib/gui/epixmap.h>
#include <lib/gdi/erect.h>
#include <lib/gdi/gpixmap.h>
#include <lib/gdi/font.h>
#include <vector>
#include <string>

/*
 * eCanvas - dual-path drawing canvas
 *
 * Software path  : when the active DC is NOT hardware-accelerated, eCanvas
 *                  falls back to the classic gPixmap software buffer approach.
 * GPU / GLES path: when the active DC IS hardware-accelerated (gEGLDC),
 *                  drawing commands are collected during clear/fillRect/etc.
 *                  calls and replayed at evtPaint time directly through the
 *                  hardware gPainter - zero CPU copies, fully GPU-native.
 *
 * The API is identical to the original eCanvas, so all SWIG / Python bindings
 * remain untouched.  Platform detection happens at paint time, so a single
 * binary runs correctly on both software and hardware-accelerated boxes.
 */

class eCanvas : public ePixmap
{
public:
	eCanvas(eWidget *parent);

	void setSize(eSize size);

	void clear(gRGB color);
	void fillRect(eRect rect, gRGB color);
	void drawLine(int x0, int y0, int x1, int y1, gRGB color);
	void writeText(eRect where, gRGB fg, gRGB bg, gFont *font, const char *string, int flags);
	void drawRotatedLine(int ox, int oy, int x0, int y0, int x1, int y1, float angle, bool cw, gRGB color);

	/* eWidget interface */
	int event(int event, void *data = nullptr, void *data2 = nullptr) override;

private:
	/* --- command recording ------------------------------------------------ */
	enum OpType
	{
		OP_CLEAR,
		OP_FILL_RECT,
		OP_LINE,
		OP_ROTATED_LINE,
		OP_TEXT,
	};

	struct CanvasOp
	{
		OpType type;

		gRGB  color;   /* OP_CLEAR / OP_FILL_RECT / OP_LINE / OP_ROTATED_LINE */
		gRGB  fg, bg;  /* OP_TEXT */

		eRect rect;    /* OP_FILL_RECT / OP_TEXT */

		/* OP_LINE */
		int x0, y0, x1, y1;

		/* OP_ROTATED_LINE */
		int ox, oy;
		float angle;
		bool cw;

		/* OP_TEXT */
		ePtr<gFont> font;
		std::string text;
		int flags;
	};

	std::vector<CanvasOp> m_ops;
	eSize m_canvas_size;          /* last setSize() value */

	/* helpers */
	void replayOps(gPainter &painter) const;
	void softwarePaint(gPainter &outer_painter);
};
