#ifndef __wrappers_h
#define __wrappers_h
#include <string>

ssize_t singleRead(int fd, void *buf, size_t count);
ssize_t timedRead(int fd, void *buf, size_t count, int initialtimeout, int interbytetimeout);
ssize_t readLine(int fd, char** buffer, size_t* bufsize);
ssize_t writeAll(int fd, const void *buf, size_t count);
int Select(int maxfd, fd_set *readfds, fd_set *writefds, fd_set *exceptfds, struct timeval *timeout);
int Connect(const char *hostname, int port, int timeoutsec);
std::string base64encode(const std::string str);
std::string base64decode(const std::string hash);
std::string readLink(const std::string &link);
bool contains(const std::string &str, const std::string &substr);
bool endsWith(const std::string &str, const std::string &suffix);
bool startsWith(const std::string &str, const std::string &prefix);

#endif
