#ifndef __DESCR_H_
#define __DESCR_H_

#include <lib/dvb_ci/dvbci.h>

int descrambler_init(int slot, uint8_t ca_demux_id);
void descrambler_deinit(int desc_fd);
int descrambler_set_key(int& desc_fd, eDVBCISlot *slot, int parity, unsigned char *data);
int descrambler_set_pid(int desc_fd, int index, int enable, int pid);

#endif
