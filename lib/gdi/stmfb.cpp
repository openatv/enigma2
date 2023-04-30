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
#include <lib/base/ebase.h>

static int fb_fd;

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
}

void stmfb_accel_fill(
		int dst_addr, int dst_width, int dst_height, int dst_stride,
		int x, int y, int width, int height,
		unsigned long color)
{
//	printf("unimplemented bcm_accel_fill\n");
}
