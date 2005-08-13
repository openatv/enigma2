#include <fcntl.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>

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

	eDebug("done, found %d common interface slots");
}

eDVBCIInterfaces::~eDVBCIInterfaces()
{
}

int eDVBCISlot::send(const unsigned char *data, size_t len)
{
	int res;
	//int i;
	//printf("< ");
	//for(i=0;i<len;i++)
	//	printf("%02x ",data[i]);
	//printf("\n");

	res = ::write(fd, data, len);

	//printf("write() %d\n",res);

	notifier->setRequested(eSocketNotifier::Read | eSocketNotifier::Priority | eSocketNotifier::Write);

	return res;
}

void eDVBCISlot::data(int what)
{
	if(what == eSocketNotifier::Priority) {
		if(state != stateRemoved) {
			state = stateRemoved;
			printf("ci removed\n");
			notifier->setRequested(eSocketNotifier::Read);
		}
		return;
	}


	__u8 data[4096];
	int r;
	r = ::read(fd, data, 4096);

	if(state != stateInserted) {
		state = stateInserted;
		eDebug("ci inserted");
		/* enable PRI to detect removal or errors */
		notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Write);
	}

	if(r > 0) {
		//int i;
		//printf("> ");
		//for(i=0;i<r;i++)
		//	printf("%02x ",data[i]);
		//printf("\n");
		eDVBCISession::receiveData(this, data, r);
		notifier->setRequested(eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Write);
		return;
	}

	if(what == eSocketNotifier::Write) {
		if(eDVBCISession::pollAll() == 0) {
			notifier->setRequested(eSocketNotifier::Read | eSocketNotifier::Priority);
		}
	}
}

DEFINE_REF(eDVBCISlot);

eDVBCISlot::eDVBCISlot(eMainloop *context, int nr)
{
	char filename[128];

	sprintf(filename, "/dev/ci%d", nr);

	fd = ::open(filename, O_RDWR | O_NONBLOCK);

	eDebug("eDVBCISlot has fd %d", fd);

	if (fd >= 0)
	{
		notifier = new eSocketNotifier(context, fd, eSocketNotifier::Read | eSocketNotifier::Priority);
		CONNECT(notifier->activated, eDVBCISlot::data);
	} else
	{
		perror(filename);
	}
}

eDVBCISlot::~eDVBCISlot()
{
}

eAutoInitP0<eDVBCIInterfaces> init_eDVBCIInterfaces(eAutoInitNumbers::dvb, "CI Slots");
