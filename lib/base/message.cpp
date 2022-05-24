#include <lib/base/message.h>
#include <unistd.h>
#include <lib/base/eerror.h>

eMessagePumpMT::eMessagePumpMT():
	content(1024*1024)
{
	if (pipe(fd) == -1)
	{
		eDebug("[eMessagePumpMT] failed to create pipe (%m)");
	}
}

eMessagePumpMT::~eMessagePumpMT()
{
	content.lock(); // blocks until all messages are processed.
	close(fd[0]);
	close(fd[1]);
}

int eMessagePumpMT::send(const void *data, int len)
{
	int wr = ::write(fd[1], data, len);
	if (wr > 0)
		content.lock(wr);
	return wr<0;
}

int eMessagePumpMT::recv(void *data, int len)
{
	unsigned char*dst=(unsigned char*)data;
	int recv=::read(fd[0], dst, len);
	if (recv > 0)
		content.unlock(recv);
	return recv;
}
