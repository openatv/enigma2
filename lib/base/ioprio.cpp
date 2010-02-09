#include <lib/base/ioprio.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <getopt.h>
#include <unistd.h>
#include <sys/ptrace.h>
#include <asm/unistd.h>

#include <lib/base/eerror.h>

extern "C" int sys_ioprio_set(int, int, int);
extern "C" int sys_ioprio_get(int, int);

#ifndef __NR_ioprio_set
	#if defined(__i386__)
		#define __NR_ioprio_set		289
		#define __NR_ioprio_get		290
	#elif defined(__ppc__) || defined(__powerpc__)
		#define __NR_ioprio_set		273
		#define __NR_ioprio_get		274
	#elif defined(__x86_64__)
		#define __NR_ioprio_set		251
		#define __NR_ioprio_get		252
	#elif defined(__ia64__)
		#define __NR_ioprio_set		1274
		#define __NR_ioprio_get		1275
	#elif defined(__mips__)
		#define __NR_ioprio_set		4284
		#define __NR_ioprio_get		4285
	#else
		#error "Unsupported arch"
	#endif
#endif

#if defined(_syscall3) && defined(_syscall2)

_syscall3(int, ioprio_set, int, which, int, who, int, ioprio);
_syscall2(int, ioprio_get, int, which, int, who);

#else

static inline int ioprio_set(int which, int who, int ioprio)
{
	return syscall(__NR_ioprio_set, which, who, ioprio);
}

static inline int ioprio_get(int which, int who)
{
	return syscall(__NR_ioprio_get, which, who);
}

#endif

#define IOPRIO_CLASS_SHIFT	13

enum {
	IOPRIO_WHO_PROCESS = 1,
	IOPRIO_WHO_PGRP,
	IOPRIO_WHO_USER,
};

const char *to_prio[] = { "none", "realtime", "best-effort", "idle", };

void setIoPrio(int prio_class, int prio)
{
	if (prio_class < 0 || prio_class > 3)
	{
		eDebug("prio class(%d) out of valid range (0..3)", prio_class);
		return;
	}
	if (prio < 0 || prio > 7)
	{
		eDebug("prio level(%d) out of range (0..7)", prio);
		return;
	}
	if (ioprio_set(IOPRIO_WHO_PROCESS, 0 /*pid 0 .. current process*/, prio | prio_class << IOPRIO_CLASS_SHIFT) == -1)
		eDebug("setIoPrio failed (%m) !");
	else
		eDebug("setIoPrio %s level %d ok", to_prio[prio_class], prio);
}

void printIoPrio()
{
	int pid = 0, ioprio = ioprio_get(IOPRIO_WHO_PROCESS, pid);

	eDebug("pid=%d, %d", pid, ioprio);

	if (ioprio == -1)
		eDebug("ioprio_get(%m)");
	else {
		int ioprio_class = ioprio >> IOPRIO_CLASS_SHIFT;
		ioprio = ioprio & 0xff;
		eDebug("%s: prio %d", to_prio[ioprio_class], ioprio);
	}
}
