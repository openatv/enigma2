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
	typedef int (*FUNC_PTR) (const char* pathname, int flags, ...);
	static FUNC_PTR libc_open64;
	int fd=-1;
	if (!libc_open64)
	{
		void *handle;
		char *error;
		handle = dlopen(LIBC_SO, RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_open64 = (FUNC_PTR) dlsym(handle, "open64");
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

#if _FILE_OFFSET_BITS != 64
int open(const char *pathname, int flags, ...)
{
	typedef int (*FUNC_PTR) (const char* pathname, int flags, ...);
	static FUNC_PTR libc_open;
	int fd=-1;
	if (!libc_open)
	{
		void *handle;
		char *error;
		handle = dlopen(LIBC_SO, RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_open = (FUNC_PTR) dlsym(handle, "open");
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
#endif

FILE *fopen64(const char *pathname, const char *mode)
{
	typedef FILE *(*FUNC_PTR) (const char* pathname, const char *mode);
	static FUNC_PTR libc_fopen64;
	FILE *f=0;
	if (!libc_fopen64)
	{
		void *handle;
		char *error;
		handle = dlopen(LIBC_SO, RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_fopen64 = (FUNC_PTR) dlsym(handle, "fopen64");
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

#if _FILE_OFFSET_BITS != 64
FILE *fopen(const char *pathname, const char *mode)
{
	typedef FILE *(*FUNC_PTR) (const char* pathname, const char *mode);
	static FUNC_PTR libc_fopen;
	FILE *f=0;
	if (!libc_fopen)
	{
		void *handle;
		char *error;
		handle = dlopen(LIBC_SO, RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_fopen = (FUNC_PTR) dlsym(handle, "fopen");
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
#endif

int socket(int domain, int type, int protocol)
{
	typedef int (*FUNC_PTR) (int domain, int type, int protocol);
	static FUNC_PTR libc_socket;
	int fd=-1;
	if (!libc_socket)
	{
		void *handle;
		char *error;
		handle = dlopen(LIBC_SO, RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_socket = (FUNC_PTR) dlsym(handle, "socket");
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

int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen)
{
	typedef int (*FUNC_PTR) (int sockfd, struct sockaddr *addr, socklen_t *addrlen);
	static FUNC_PTR libc_accept;
	int fd;

	if (!libc_accept)
	{
		void *handle;
		char *error;
		handle = dlopen(LIBC_SO, RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_accept = (FUNC_PTR) dlsym(handle, "accept");
		if ((error = dlerror()) != NULL) {
			fprintf(stderr, "%s\n", error);
			exit(1);
		}
	}
	fd = libc_accept(sockfd, addr, addrlen);
	if (fd >= 0)
	{
		int fd_flags = fcntl(fd, F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(fd, F_SETFD, fd_flags);
		}
#ifdef DEBUG
		fprintf(stdout, "accept fd %d\n", fd);
#endif
	}
	return fd;
}

int socketpair(int d, int type, int protocol, int sv[2])
{
	typedef int (*FUNC_PTR) (int d, int type, int protocol, int sv[2]);
	static FUNC_PTR libc_socketpair;
	int ret=-1;
	if (!libc_socketpair)
	{
		void *handle;
		char *error;
		handle = dlopen(LIBC_SO, RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_socketpair = (FUNC_PTR) dlsym(handle, "socketpair");
		if ((error = dlerror()) != NULL) {
			fprintf(stderr, "%s\n", error);
			exit(1);
		}
	}
	ret = libc_socketpair(d, type, protocol, sv);
	if (!ret)
	{
		int fd_flags = fcntl(sv[0], F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(sv[0], F_SETFD, fd_flags);
		}
		fd_flags = fcntl(sv[1], F_GETFD, 0);
		if (fd_flags >= 0)
		{
			fd_flags |= FD_CLOEXEC;
			fcntl(sv[1], F_SETFD, fd_flags);
		}
#ifdef DEBUG
		fprintf(stdout, "socketpair fd %d %d\n", sv[0], sv[1]);
#endif
	}
	return ret;
}

int pipe(int modus[2])
{
	typedef int (*FUNC_PTR) (int modus[2]);
	static FUNC_PTR libc_pipe;
	int ret=-1;
	if (!libc_pipe)
	{
		void *handle;
		char *error;
		handle = dlopen(LIBC_SO, RTLD_LAZY);
		if (!handle)
		{
			fputs(dlerror(), stderr);
			exit(1);
		}
		libc_pipe = (FUNC_PTR) dlsym(handle, "pipe");
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

