#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <linux/dvb/ca.h>

#include <lib/dvb_ci/descrambler.h>

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

struct vu_ca_descr_data {
	int slot_id;
	int fix1; // = 0x6f7c
	int demux_id;
	int tunernum;
	int use_count;
	int program_number;
	int reserved1;
	int fix2; // = 0x1 -> add pids
	int video_pid;
	int audio_pid;
	int reserved2;
	int fix3; // = 0x12345678
	int reserved3;
	int key_register;
	int use_aes; // 0x2 for AES
	unsigned char key[16];
	unsigned char iv[16];
	int audio_number;
	int audio_pids[16];
};


#define CA_SET_DESCR_DATA _IOW('o', 137, struct ca_descr_data)

int descrambler_set_key(int& desc_fd, eDVBCISlot *slot, int parity, unsigned char *data)
{
	bool vuIoctlSuccess = false;

	if (slot->getTunerNum() > 7) // might be VU box with 2 FBC tuners -> try to use VU ioctl
	{
		struct vu_ca_descr_data d;

		d.slot_id = slot->getSlotID();
		d.fix1 = 0x6f7c;
		d.demux_id = slot->getCADemuxID();
		d.tunernum = slot->getTunerNum();
		d.use_count = slot->getUseCount();
		d.program_number = slot->getProgramNumber();
		d.fix2 = 0x1;
		d.video_pid = slot->getVideoPid();
		d.audio_pid = slot->getAudioPid();
		d.fix3 = 0x12345678;
		d.key_register = parity;
		d.use_aes = 0x2; // AES
		memcpy(d.key, data, 16);
		memcpy(d.iv, data + 16, 16);
		d.audio_number = slot->getAudioNumber();
		memcpy(d.audio_pids, slot->getAudioPids(), 16*4);

		unsigned int ret = ioctl(slot->getFd(), 0x10, &d);
		if (ret == 0)
		{
			vuIoctlSuccess = true;
			descrambler_deinit(desc_fd); // don't set pids for VU ioctl
			desc_fd = -1;
		}
		eDebug("[CI%d] descrambler_set_key vu ret %u", slot->getSlotID(), ret);
	}

	if (!vuIoctlSuccess)
	{
		struct ca_descr_data d;

		if (desc_fd < 0)
			return -1;

		d.index = slot->getSlotID();
		d.parity = (enum ca_descr_parity)parity;
		d.data_type = CA_DATA_KEY;
		d.length = 16;
		d.data = data;

		if (ioctl(desc_fd, CA_SET_DESCR_DATA, &d) == -1) {
			eWarning("[CI%d descrambler] set key failed", slot->getSlotID());
			return -1;
		}

		d.index = slot->getSlotID();
		d.parity = (enum ca_descr_parity)parity;
		d.data_type = CA_DATA_IV;
		d.length = 16;
		d.data = data + 16;

		if (ioctl(desc_fd, CA_SET_DESCR_DATA, &d) == -1) {
			eWarning("[CI%d descrambler] set iv failed", slot->getSlotID());
			return -1;
		}
	}

	return 0;
}

int descrambler_set_pid(int desc_fd, int index, int enable, int pid)
{
	struct ca_pid p;
	unsigned int flags = 0x80;

	if (desc_fd < 0)
		return -1;

	if (index)
		flags |= 0x40;

	if (enable)
		flags |= 0x20;

	p.pid = pid;
	p.index = flags;

	if (ioctl(desc_fd, CA_SET_PID, &p) == -1) {
		eWarning("[CI%d descrambler] set pid failed", index);
		return -1;
	}

	return 0;
}

int descrambler_init(int slot, uint8_t ca_demux_id)
{
	int desc_fd;

	std::string filename = "/dev/dvb/adapter0/ca" + std::to_string(ca_demux_id);

	desc_fd = open(filename.c_str(), O_RDWR);
	if (desc_fd == -1) {
		eWarning("[CI%d descrambler] can not open %s", slot, filename.c_str());
	}
	eDebug("[CI%d descrambler] using ca device %s", slot, filename.c_str());

	return desc_fd;
}

void descrambler_deinit(int desc_fd)
{
	if (desc_fd >= 0)
		close(desc_fd);
	desc_fd = -1;
}
