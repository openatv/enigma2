#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <linux/dvb/ca.h>

#include <lib/base/eerror.h>

#ifndef CA_SET_PID
/**
 * CA_SET_PID and ca_pid struct removed on 4.14 kernel
 * Check commit         833ff5e7feda1a042b83e82208cef3d212ca0ef1
**/
struct ca_pid {
	unsigned int pid;
	int index;              /* -1 == disable*/
};
#define CA_SET_PID _IOW('o', 135, struct ca_pid)
#endif

enum ca_descr_data_type {
	CA_DATA_IV,
	CA_DATA_KEY,
};

enum ca_descr_parity {
	CA_PARITY_EVEN,
	CA_PARITY_ODD,
};

struct ca_descr_data {
	unsigned int index;
	enum ca_descr_parity parity;
	enum ca_descr_data_type data_type;
	unsigned int length;
	unsigned char *data;
};


#define CA_SET_DESCR_DATA _IOW('o', 137, struct ca_descr_data)

int descrambler_set_key(int desc_fd, int index, int parity, unsigned char *data)
{
	struct ca_descr_data d;

	d.index = index;
	d.parity = (enum ca_descr_parity)parity;
	d.data_type = CA_DATA_KEY;
	d.length = 16;
	d.data = data;

	if (ioctl(desc_fd, CA_SET_DESCR_DATA, &d) == -1) {
		eWarning("[CI descrambler] set key failed");
		return -1;
	}

	d.index = index;
	d.parity = (enum ca_descr_parity)parity;
	d.data_type = CA_DATA_IV;
	d.length = 16;
	d.data = data + 16;

	if (ioctl(desc_fd, CA_SET_DESCR_DATA, &d) == -1) {
		eWarning("[CI descrambler] set iv failed");
		return -1;
	}

	return 0;
}

int descrambler_set_pid(int desc_fd, int index, int enable, int pid)
{
	struct ca_pid p;
	unsigned int flags = 0x80;

	if (index)
		flags |= 0x40;

	if (enable)
		flags |= 0x20;

	p.pid = pid;
	p.index = flags;

	if (ioctl(desc_fd, CA_SET_PID, &p) == -1) {
		eWarning("[CI descrambler] set pid failed");
		return -1;
	}

	return 0;
}

int descrambler_init(void)
{
	int desc_fd;
	const char *filename = "/dev/dvb/adapter0/ca0";

	desc_fd = open(filename, O_RDWR);
	if (desc_fd == -1) {
		eWarning("[CI descrambler] can not open %s", filename);
	}

	return desc_fd;
}

void descrambler_deinit(int desc_fd)
{
	close(desc_fd);
}
