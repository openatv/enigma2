#include <lib/python/connections.h>

PSignal1<void,int> testsignal;

void connect(Slot1<void, int> &slot, PyObject *fnc)
{
	printf("CONNECT !\n");
}

