#include <lib/base/message.h>
#include <unistd.h>
#include <lib/base/eerror.h>

eMessagePump::eMessagePump(int mt): content(1024*1024), ismt(mt)
{
	pipe(fd);
}

eMessagePump::~eMessagePump()
{	
	if (ismt)
		content.lock(); // blocks until all messages are processed.
	close(fd[0]);
	close(fd[1]);
}

int eMessagePump::send(const void *data, int len)
{
	int wr = ::write(fd[1], data, len);
	if (ismt && wr > 0)
		content.lock(wr);
	return wr<0;
}

int eMessagePump::recv(void *data, int len)
{
	unsigned char*dst=(unsigned char*)data;
	int recv=::read(fd[0], dst, len);
	if (recv > 0 && ismt)
		content.unlock(recv);
	return recv;
}

int eMessagePump::getInputFD() const
{
	return fd[1];
}

int eMessagePump::getOutputFD() const
{
	return fd[0];
}
