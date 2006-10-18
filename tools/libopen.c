#define _GNU_SOURCE
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <fcntl.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

#undef DEBUG

int open64(const char *pathname, int flags, ...)
{
	static int (*libc_open64) (const char* pathname, int flags, ...);
	int fd=-1;
	if (!libc_open64)
	{
		void *handle;
		char *error;
		handle = dlopen("/lib/libc.so.6", RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_open64 = dlsym(handle, "open64");
		if ((error = dlerror()) != NULL) {
			fprintf(stderr, "%s\n", error);
			exit(1);
		}
	}
	fd = libc_open64(pathname, flags);
	if (fd >= 0)
	{
		int fd_flags = fcntl(fd, F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(fd, F_SETFD, fd_flags);
		}
#ifdef DEBUG
		fprintf(stdout, "open64 %s, flags %d returned fd %d\n", pathname, flags, fd);
#endif
	}
	return fd;
}

int open(const char *pathname, int flags, ...)
{
	static int (*libc_open) (const char* pathname, int flags, ...);
	int fd=-1;
	if (!libc_open)
	{
		void *handle;
		char *error;
		handle = dlopen("/lib/libc.so.6", RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_open = dlsym(handle, "open");
		if ((error = dlerror()) != NULL) {
			fprintf(stderr, "%s\n", error);
			exit(1);
		}
	}
	fd = libc_open(pathname, flags);
	if (fd >= 0)
	{
		int fd_flags = fcntl(fd, F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(fd, F_SETFD, fd_flags);
		}
#ifdef DEBUG
		fprintf(stdout, "open %s, flags %d returned fd %d\n", pathname, flags, fd);
#endif
	}
	return fd;
}

FILE *fopen64(const char *pathname, const char *mode)
{
	static FILE *(*libc_fopen64) (const char* pathname, const char *mode);
	FILE *f=0;
	if (!libc_fopen64)
	{
		void *handle;
		char *error;
		handle = dlopen("/lib/libc.so.6", RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_fopen64 = dlsym(handle, "fopen64");
		if ((error = dlerror()) != NULL) {
			fprintf(stderr, "%s\n", error);
			exit(1);
		}
	}
	f = libc_fopen64(pathname, mode);
	if (f)
	{
		int fd = fileno(f);
		int fd_flags = fcntl(fd, F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(fd, F_SETFD, fd_flags);
		}
#ifdef DEBUG
		fprintf(stdout, "fopen64 %s, mode %s returned FILE* %p fd %d\n", pathname, mode, f, fd);
#endif
	}
	return f;
}

FILE *fopen(const char *pathname, const char *mode)
{
	static FILE *(*libc_fopen) (const char* pathname, const char *mode);
	FILE *f=0;
	if (!libc_fopen)
	{
		void *handle;
		char *error;
		handle = dlopen("/lib/libc.so.6", RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_fopen = dlsym(handle, "fopen");
		if ((error = dlerror()) != NULL) {
			fprintf(stderr, "%s\n", error);
			exit(1);
		}
	}
	f = libc_fopen(pathname, mode);
	if (f)
	{
		int fd = fileno(f);
		int fd_flags = fcntl(fd, F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(fd, F_SETFD, fd_flags);
		}
#ifdef DEBUG
		fprintf(stdout, "fopen %s, mode %s returned FILE* %p fd %d\n", pathname, mode, f, fd);
#endif
	}
	return f;
}

int socket(int domain, int type, int protocol)
{
	static int (*libc_socket) (int domain, int type, int protocol);
	int fd=-1;
	if (!libc_socket)
	{
		void *handle;
		char *error;
		handle = dlopen("/lib/libc.so.6", RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_socket = dlsym(handle, "socket");
		if ((error = dlerror()) != NULL) {
			fprintf(stderr, "%s\n", error);
			exit(1);
		}
	}
	fd = libc_socket(domain, type, protocol);
	if (fd >= 0)
	{
		int fd_flags = fcntl(fd, F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(fd, F_SETFD, fd_flags);
		}
#ifdef DEBUG
		fprintf(stdout, "socket fd %d\n", fd);
#endif
	}
	return fd;
}

int pipe(int modus[2])
{
	static int (*libc_pipe) (int modus[2]);
	int ret=-1;
	if (!libc_pipe)
	{
		void *handle;
		char *error;
		handle = dlopen("/lib/libc.so.6", RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_pipe = dlsym(handle, "pipe");
		if ((error = dlerror()) != NULL) {
			fprintf(stderr, "%s\n", error);
			exit(1);
		}
	}
	ret = libc_pipe(modus);
	if (!ret)
	{
		int fd_flags = fcntl(modus[0], F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(modus[0], F_SETFD, fd_flags);
		}
		fd_flags = fcntl(modus[1], F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(modus[1], F_SETFD, fd_flags);
		}
#ifdef DEBUG
		fprintf(stdout, "pipe fds[%d, %d]\n", modus[0], modus[1]);
#endif
	}
	return ret;
}

