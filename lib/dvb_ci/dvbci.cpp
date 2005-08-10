#include <fcntl.h>

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/dvb_ci/dvbci_session.h>

eDVBCIInterfaces::eDVBCIInterfaces()
{
	int num_ci = 0;

	eDebug("scanning for common interfaces..");
	while (1)
	{
		struct stat s;
		char filename[128];
		sprintf(filename, "/dev/ci%d", num_ci);

		if (stat(filename, &s))
			break;

		ePtr<eDVBCISlot> cislot;

		cislot = new eDVBCISlot(eApp, num_ci);
		m_slots.push_back(cislot);

		++num_ci;
	}

	eDebug("done, found %d common interfaces");
}

int eDVBCISlot::write(const unsigned char *data, size_t len)
{
	return ::write(fd, data, len);
}

void eDVBCISlot::data(int)
{
	eDebug("ci talks to us");

	__u8 data[4096];
	int r;
	r = ::read(fd, data, 4096);
	if(r < 0)
		eWarning("ERROR reading from CI - %m\n");

	if(!se) {
		eDebug("ci inserted");
		se = new eDVBCISession(this);
	
		/* enable HUP to detect removal or errors */
		notifier_event->start();
	}

	if(r > 0)
		se->receiveData(data, r);
}

void eDVBCISlot::event(int)
{
	eDebug("CI removed");
	
	/* kill the TransportConnection */
	
	/* we know about and disable HUP */
	notifier_event->stop();
}

eDVBCISlot::eDVBCISlot(eMainloop *context, int nr): se(0)
{
	char filename[128];

	sprintf(filename, "/dev/ci%d", nr);

	fd = ::open(filename, O_RDWR | O_NONBLOCK);

	eDebug("eDVBCISlot has fd %d", fd);

	if (fd >= 0)
	{
		//read callback
		notifier_data = new eSocketNotifier(context, fd, eSocketNotifier::Read);
		CONNECT(notifier_data->activated, eDVBCISlot::data);
		//remove callback
		notifier_event = new eSocketNotifier(context, fd, eSocketNotifier::Hungup);
		CONNECT(notifier_event->activated, eDVBCISlot::event);
	} else
	{
		perror(filename);
	}
}

