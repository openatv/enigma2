#ifndef __DESCR_H_
#define __DESCR_H_

int descrambler_init(void);
void descrambler_deinit(int desc_fd);
int descrambler_set_key(int desc_fd, int index, int parity, unsigned char *data);
int descrambler_set_pid(int desc_fd, int index, int enable, int pid);

#endif
