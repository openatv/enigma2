#include <lib/mmi/socket_mmi.h>

#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <lib/base/ebase.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>
#include <lib/dvb_ci/dvbci_session.h>

#define MAX_LENGTH_BYTES 4
#define MIN_LENGTH_BYTES 1
//#define MMIDEBUG

eSocket_UI *eSocket_UI::instance;

eSocket_UI::eSocket_UI()
	:eMMI_UI(1)
{
	ASSERT(!instance);
	instance = this;
	CONNECT(handler.mmi_progress, eMMI_UI::processMMIData);
}

eSocket_UI *eSocket_UI::getInstance()
{
	return instance;
}

void eSocket_UI::setInit(int slot)
{
	//NYI
}

void eSocket_UI::setReset(int slot)
{
	//NYI
}

int eSocket_UI::startMMI(int slot)
{
	unsigned char buf[]={0x9F,0x80,0x22,0x00};  // ENTER MMI
	if (handler.send_to_mmisock( buf, 4 ))
	{
		eDebug("eSocket_UI::startMMI failed");
		return -1;
	}
	return 0;
}

int eSocket_UI::stopMMI(int slot)
{
	unsigned char buf[]={0x9F,0x88,0x00,0x00};  // CLOSE MMI
	if (handler.send_to_mmisock( buf, 4 ))
	{
		eDebug("eSocket_UI::stopMMI failed");
		return -1;
	}
	return 0;
}

int eSocket_UI::answerMenu(int slot, int answer)
{
	unsigned char data[]={0x9f,0x88,0x0B,0x01,0x00};
	data[4] = answer & 0xff;
	if (handler.send_to_mmisock( data, 5 ))
	{
		eDebug("eSocket_UI::answerMenu failed");
		return -1;
	}
	return 0;
}

int eSocket_UI::answerEnq(int slot, char *answer)
{
	unsigned int len = strlen(answer);
	unsigned char data[4+len+MAX_LENGTH_BYTES];
	data[0] = 0x9f;
	data[1] = 0x88;
	data[2] = 0x08;
	int LengthBytes=eDVBCISession::buildLengthField(data+3, len+1);
	data[3+LengthBytes] = 0x01;
	memcpy(data+4+LengthBytes, answer, len);
	if (handler.send_to_mmisock( data, len+4+LengthBytes ))
	{
		eDebug("eSocket_UI::answerEnq failed");
		return -1;
	}
	return 0;
}

int eSocket_UI::cancelEnq(int slot)
{
	unsigned char data[]={0x9f,0x88,0x08,0x01,0x00};
	if (handler.send_to_mmisock( data, 5 ))
	{
		eDebug("eSocket_UI::cancelEnq failed");
		return -1;
	}
	return 0;
}

int eSocket_UI::getState(int slot)
{
	return handler.connected() ? 2 : 0;
}

int eSocket_UI::getMMIState(int slot)
{
	return handler.connected();
}

//FIXME: correct "run/startlevel"
eAutoInitP0<eSocket_UI> init_socketui(eAutoInitNumbers::rc, "Socket MMI");

int eSocketMMIHandler::send_to_mmisock( void* buf, size_t len)
{
	int ret = write(connfd, buf, len);
	if ( ret < 0 )
		eDebug("[eSocketMMIHandler] write (%m)");
	else if ( (uint)ret != len )
		eDebug("[eSocketMMIHandler] only %d bytes sent.. %d bytes should be sent", ret, len );
	else
		return 0;
	return ret;
}

eSocketMMIHandler::eSocketMMIHandler()
	:buffer(512), connfd(-1), connsn(0), sockname("/tmp/mmi.socket"), name(0)
{
	memset(&servaddr, 0, sizeof(struct sockaddr_un));
	servaddr.sun_family = AF_UNIX;
	unlink(sockname);
	strcpy(servaddr.sun_path, sockname);
	clilen = sizeof(servaddr.sun_family) + strlen(servaddr.sun_path);
	if ((listenfd = socket(AF_UNIX, SOCK_STREAM, 0)) < 0)
	{
		eDebug("[eSocketMMIHandler] socket (%m)");
		return;
	}

	int val = 1;
	if (setsockopt(listenfd, SOL_SOCKET, SO_REUSEADDR, &val, sizeof(val)) == -1)
		eDebug("[eSocketMMIHandler] SO_REUSEADDR (%m)");
	else if ((val = fcntl(listenfd, F_GETFL)) == -1)
		eDebug("[eSocketMMIHandler] F_GETFL (%m)");
	else if (fcntl(listenfd, F_SETFL, val | O_NONBLOCK) == -1)
		eDebug("[eSocketMMIHandler] F_SETFL (%m)");
	else if (bind(listenfd, (struct sockaddr *) &servaddr, clilen) == -1)
		eDebug("[eSocketMMIHandler] bind (%m)");
	else if (listen(listenfd, 0) == -1)
		eDebug("[eSocketMMIHandler] listen (%m)");
	else {
		listensn = new eSocketNotifier( eApp, listenfd, POLLIN );
		listensn->start();
		CONNECT( listensn->activated, eSocketMMIHandler::listenDataAvail );
		eDebug("[eSocketMMIHandler] created successfully");
		return;
	}

	close(listenfd);
	listenfd = -1;
}

#define CMD_SET_NAME "\x01\x02\x03\x04"

void eSocketMMIHandler::listenDataAvail(int what)
{
	if (what & POLLIN) {
		if ( connsn ) {
			eDebug("[eSocketMMIHandler] connsn != NULL");
			return;
		}
		connfd = accept(listenfd, (struct sockaddr *) &servaddr, (socklen_t *) &clilen);
		if (connfd == -1) {
			eDebug("[eSocketMMIHandler] accept (%m)");
			return;
		}

		int val;
		if ((val = fcntl(connfd, F_GETFL)) == -1)
			eDebug("[eSocketMMIHandler] F_GETFL (%m)");
		else if (fcntl(connfd, F_SETFL, val | O_NONBLOCK) == -1)
			eDebug("[eSocketMMIHandler] F_SETFL (%m)");
		else {
			connsn = new eSocketNotifier( eApp, connfd, POLLIN|POLLHUP|POLLERR );
			CONNECT( connsn->activated, eSocketMMIHandler::connDataAvail );
			return;
		}

		close(connfd);
		connfd = -1;
	}
}

void eSocketMMIHandler::connDataAvail(int what)
{
	if (what & (POLLIN | POLLPRI | POLLRDNORM | POLLRDBAND)) {
		char msgbuffer[4096];
		ssize_t length = read(connfd, msgbuffer, sizeof(msgbuffer));

		if (length == -1) {
			if (errno != EAGAIN) {
				eDebug("[eSocketMMIHandler] read (%m)");
				what |= POLLERR;
			}
		} else if (length == 0){
			what |= POLLHUP;
		} else if ((!name) && (length > 4) && (!memcmp(msgbuffer, CMD_SET_NAME, 4))) {
			length -= 4;
			delete [] name;
			name = new char[length + 1];
			memcpy(name, &msgbuffer[4], length);
			name[length] = '\0';
			eDebug("MMI NAME %s", name);
		} else {
			int len = length;
			unsigned char *data = (unsigned char*)msgbuffer;
			int clear = 1;
	// If a new message starts, then the previous message
	// should already have been processed. Otherwise the
	// previous message was incomplete and should therefore
	// be deleted.
			if ((len >= 1) && (data[0] != 0x9f))
				clear = 0;
			if ((len >= 2) && (data[1] != 0x88))
				clear = 0;
			if (clear)
			{
				buffer.clear();
#ifdef MMIDEBUG
				eDebug("clear buffer");
#endif
			}
#ifdef MMIDEBUG
			eDebug("Put to buffer:");
			for (int i=0; i < len; ++i)
				eDebugNoNewLine("%02x ", data[i]);
			eDebug("\n--------");
#endif
			buffer.write( data, len );

			while ( buffer.size() >= (3 + MIN_LENGTH_BYTES) )
			{
				unsigned char tmp[3+MAX_LENGTH_BYTES];
				buffer.peek(tmp, 3+MIN_LENGTH_BYTES);
				if (tmp[0] != 0x9f || tmp[1] != 0x88)
				{
					buffer.skip(1);
#ifdef MMIDEBUG
					eDebug("skip %02x", tmp[0]);
#endif
					continue;
				}
				if (tmp[3] & 0x80) {
					int peekLength = (tmp[3] & 0x7f) + 4;
					if (buffer.size() < peekLength)
						continue;
					buffer.peek(tmp, peekLength);
				}
				int size=0;
				int LengthBytes=eDVBCISession::parseLengthField(tmp+3, size);
				int messageLength = 3+LengthBytes+size;
				if ( buffer.size() >= messageLength )
				{
					unsigned char dest[messageLength];
					buffer.read(dest, messageLength);
#ifdef MMIDEBUG
					eDebug("dump mmi:");
					for (int i=0; i < messageLength; ++i)
						eDebugNoNewLine("%02x ", dest[i]);
					eDebug("\n--------");
#endif
					/*emit*/ mmi_progress(0, dest, (const void*)(dest+3+LengthBytes), messageLength-3-LengthBytes);
				}
			}
		}
	}

	if (what & (POLLERR | POLLHUP)) {
		eDebug("pollhup/pollerr");
		closeConn();
		/*emit*/ mmi_progress(0, (const unsigned char*)"\x9f\x88\x00", "\x00", 1);
	}
}

void eSocketMMIHandler::closeConn()
{
	if ( connfd != -1 )
	{
		close(connfd);
		connfd=-1;
	}
	if ( connsn )
	{
		delete connsn;
		connsn=0;
	}
	if ( name )
	{
		delete [] name;
		name=0;
	}
}

eSocketMMIHandler::~eSocketMMIHandler()
{
	closeConn();
	delete listensn;
	unlink(sockname);
}
