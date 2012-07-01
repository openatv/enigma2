#ifndef __LIB_BASE_IOPRIO_H_
#define __LIB_BASE_IOPRIO_H_

void setIoPrio(int prio_class, int prio=7);
void printIoPrio();

enum {
	IOPRIO_CLASS_NONE,
	IOPRIO_CLASS_RT,
	IOPRIO_CLASS_BE,
	IOPRIO_CLASS_IDLE,
};

#endif // __LIB_BASE_IOPRIO_H_
