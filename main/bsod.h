#ifndef __main_bsod_h
#define __main_bsod_h

void bsodLogInit();
void bsodCatchSignals();
void bsodFatal(const char *component);

#endif
