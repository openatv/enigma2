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
#include <linux/stmfb.h>


#include <lib/base/ebase.h>

static int fb_fd;
static int exec_list(void);

int stmfb_accel_init(void)
{
	fb_fd = open("/dev/fb0", O_RDWR);
	if (fb_fd < 0)
	{
		perror("/dev/fb0");
		return 1;
	}
	eDebug("STMFB accel interface available\n");
	return 0;
}

void stmfb_accel_close(void)
{
	close(fb_fd);
}

void stmfb_accel_blit(
		int src_addr, int src_width, int src_height, int src_stride, int src_format,
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int src_x, int src_y, int width, int height,
		int dst_x, int dst_y, int dwidth, int dheight)
{
	STMFBIO_BLT_DATA bltData;
	memset(&bltData, 0, sizeof(STMFBIO_BLT_DATA));

	bltData.operation  = BLT_OP_COPY;
	bltData.srcOffset  = (src_addr - dst_addr) + (1920*1080*4);
	bltData.srcPitch   = src_stride;
	bltData.src_left   = src_x;
	bltData.src_top    = src_y;
	bltData.src_right  = src_x + width;
	bltData.src_bottom = src_y + height;
	bltData.srcFormat  = SURF_BGRA8888;

	bltData.dstOffset  = 1920*1080*4;
	bltData.dstPitch   = dst_stride;
	bltData.dst_left   = dst_x;
	bltData.dst_top    = dst_y;
	bltData.dst_right  = dst_x + dwidth;
	bltData.dst_bottom = dst_y + dheight;
	bltData.dstFormat  = SURF_BGRA8888;

	if (ioctl(fb_fd, STMFBIO_BLT, &bltData ) < 0)
	{
		eDebug("Error ioctl FBIO_BLIT");
	}
}

void stmfb_accel_fill(
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int x, int y, int width, int height,
		unsigned long color)
{
//	printf("unimplemented bcm_accel_fill\n");
}
