/*
  Interface to the Dreambox dm800/dm8000 proprietary accel interface.
*/

#include <stdio.h>
#include <stdlib.h>
#include <fcntl.h>
#include <unistd.h>
#include <linux/fb.h>
#include <sys/mman.h>
#include <sys/ioctl.h>
#include <lib/base/eerror.h>

#define FBIO_ACCEL  0x23

static unsigned int displaylist[1024];
static int ptr = 0;
static bool supportblendingflags = true;
static bool accumulateoperations = false;

#define P(x, y) do { displaylist[ptr++] = x; displaylist[ptr++] = y; } while (0)
#define C(x) P(x, 0)

static int fb_fd = -1;
static int exec_list(void);

int bcm_accel_init(void)
{
	fb_fd = open("/dev/fb0", O_RDWR);
	if (fb_fd < 0)
	{
		eDebug("[bcm] /dev/fb0 %m");
		return 1;
	}
	if (exec_list())
	{
		eDebug("[bcm] interface not available - %m");
		close(fb_fd);
		fb_fd = -1;
		return 1;
	}
	/* now test for blending flags support */
	P(0x80, 0);
	if (exec_list())
	{
		supportblendingflags = false;
	}
#ifdef FORCE_NO_BLENDING_ACCELERATION
	/* hardware doesn't allow us to detect whether the opcode is working */
	supportblendingflags = false;
#endif
	return 0;
}

void bcm_accel_close(void)
{
	if (fb_fd >= 0)
	{
		close(fb_fd);
		fb_fd = -1;
	}
}

static int exec_list(void)
{
	int ret;
	struct
	{
		void *ptr;
		int len;
	} l;

	if (fb_fd < 0) return -1;

	l.ptr = displaylist;
	l.len = ptr;
	ret = ioctl(fb_fd, FBIO_ACCEL, &l);
	ptr = 0;
	return ret;
}

bool bcm_accel_has_alphablending()
{
	return supportblendingflags;
}

int bcm_accel_accumulate()
{
#ifdef SUPPORT_ACCUMULATED_ACCELERATION_OPERATIONS
	accumulateoperations = true;
	return 0;
#else
	return -1;
#endif
}

int bcm_accel_sync()
{
	int retval = 0;
	if (accumulateoperations)
	{
		if (ptr)
		{
			eDebug("bcm_accel_sync: ptr %d", ptr);
			retval = exec_list();
		}
		accumulateoperations = false;
	}
	return retval;
}

void bcm_accel_blit(
		int src_addr, int src_width, int src_height, int src_stride, int src_format,
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int src_x, int src_y, int width, int height,
		int dst_x, int dst_y, int dwidth, int dheight,
		int pal_addr, int flags)
{
	if (accumulateoperations)
	{
		if (((sizeof(displaylist) / sizeof(displaylist[0]) - ptr) / 2) < 40)
		{
			eDebug("bcm_accel_blit: not enough space to accumulate");
			bcm_accel_sync();
			bcm_accel_accumulate();
		}
	}

	C(0x43); // reset source
	C(0x53); // reset dest
	C(0x5b);  // reset pattern
	C(0x67); // reset blend
	C(0x75); // reset output

	P(0x0, src_addr); // set source addr
	P(0x1, src_stride);  // set source pitch
	P(0x2, src_width); // source width
	P(0x3, src_height); // height
	switch (src_format)
	{
	case 0:
		P(0x4, 0x7e48888); // format: ARGB 8888
		break;
	case 1:
		P(0x4, 0x12e40008); // indexed 8bit
		P(0x78, 256);
		P(0x79, pal_addr);
		P(0x7a, 0x7e48888);
		break;
	}

	C(0x5); // set source surface (based on last parameters)

	P(0x2e, src_x); // define  rect
	P(0x2f, src_y);
	P(0x30, width);
	P(0x31, height);

	C(0x32); // set this rect as source rect

	P(0x0, dst_addr); // prepare output surface
	P(0x1, dst_stride);
	P(0x2, dst_width);
	P(0x3, dst_height);
	P(0x4, 0x7e48888);

	C(0x69); // set output surface

	P(0x2e, dst_x); // prepare output rect
	P(0x2f, dst_y);
	P(0x30, dwidth);
	P(0x31, dheight);

	C(0x6e); // set this rect as output rect

	if (supportblendingflags && flags) P(0x80, flags); /* blend flags... We'd really like some blending support in the drivers, to avoid punching holes in the osd */

	C(0x77);  // do it

	if (!accumulateoperations) exec_list();
}

void bcm_accel_fill(
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int x, int y, int width, int height,
		unsigned long color)
{
	if (accumulateoperations)
	{
		if (((sizeof(displaylist) / sizeof(displaylist[0]) - ptr) / 2) < 40)
		{
			eDebug("bcm_accel_fill: not enough space to accumulate");
			bcm_accel_sync();
			bcm_accel_accumulate();
		}
	}

	C(0x43); // reset source
	C(0x53); // reset dest
	C(0x5b); // reset pattern
	C(0x67); // reset blend
	C(0x75); // reset output

	// clear dest surface
	P(0x0, 0);
	P(0x1, 0);
	P(0x2, 0);
	P(0x3, 0);
	P(0x4, 0);
	C(0x45);

	// clear src surface
	P(0x0, 0);
	P(0x1, 0);
	P(0x2, 0);
	P(0x3, 0);
	P(0x4, 0);
	C(0x5);

	P(0x2d, color);

	P(0x2e, x); // prepare output rect
	P(0x2f, y);
	P(0x30, width);
	P(0x31, height);
	C(0x6e); // set this rect as output rect

	P(0x0, dst_addr); // prepare output surface
	P(0x1, dst_stride);
	P(0x2, dst_width);
	P(0x3, dst_height);
	P(0x4, 0x7e48888);
	C(0x69); // set output surface

	P(0x6f, 0);
	P(0x70, 0);
	P(0x71, 2);
	P(0x72, 2);
	C(0x73); // select color keying

	C(0x77);  // do it

	if (!accumulateoperations) exec_list();
}
