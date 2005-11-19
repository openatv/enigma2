#include <fcntl.h>
#include <sys/ioctl.h>

#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/base/ebase.h>

#include <lib/base/eerror.h>
#include <lib/dvb_ci/dvbci.h>
#include <lib/dvb_ci/dvbci_session.h>

#include <lib/dvb_ci/dvbci_ui.h>
#include <lib/dvb_ci/dvbci_appmgr.h>
#include <lib/dvb_ci/dvbci_mmi.h>

eDVBCIInterfaces *eDVBCIInterfaces::instance = 0;

eDVBCIInterfaces::eDVBCIInterfaces()
{
	int num_ci = 0;
	
	instance = this;
	
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

	eDebug("done, found %d common interface slots", num_ci);
}

eDVBCIInterfaces::~eDVBCIInterfaces()
{
}

eDVBCIInterfaces *eDVBCIInterfaces::getInstance()
{
	return instance;
}

eDVBCISlot *eDVBCIInterfaces::getSlot(int slotid)
{
	for(eSmartPtrList<eDVBCISlot>::iterator i(m_slots.begin()); i != m_slots.end(); ++i)
		if(i->getSlotID() == slotid)
			return i;

	printf("FIXME: request for unknown slot\n");
			
	return 0;
}

int eDVBCIInterfaces::reset(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->reset();
}

int eDVBCIInterfaces::initialize(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->initialize();
}

int eDVBCIInterfaces::startMMI(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->startMMI();
}

int eDVBCIInterfaces::stopMMI(int slotid)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->stopMMI();
}

int eDVBCIInterfaces::answerText(int slotid, int answer)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->answerText(answer);
}

int eDVBCIInterfaces::answerEnq(int slotid, int answer, char *value)
{
	eDVBCISlot *slot;

	if( (slot = getSlot(slotid)) == 0 )
		return -1;
	
	return slot->answerEnq(answer, value);
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
			//HACK
			eDVBCI_UI::getInstance()->setState(0,0);
		}
		return;
	}

	__u8 data[4096];
	int r;
	r = ::read(fd, data, 4096);

	if(state != stateInserted) {
		state = stateInserted;
		eDebug("ci inserted");

		//HACK
		eDVBCI_UI::getInstance()->setState(0,1);

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

	application_manager = 0;
	mmi_session = 0;
	
	slotid = nr;

	sprintf(filename, "/dev/ci%d", nr);

	fd = ::open(filename, O_RDWR | O_NONBLOCK);

	eDebug("eDVBCISlot has fd %d", fd);
	
	state = stateInserted;

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

int eDVBCISlot::getSlotID()
{
	return slotid;
}

int eDVBCISlot::reset()
{
	printf("edvbcislot: reset requested\n");

	ioctl(fd, 0);

	return 0;
}

int eDVBCISlot::initialize()
{
	printf("edvbcislot: initialize()\n");
	return 0;
}

int eDVBCISlot::startMMI()
{
	printf("edvbcislot: startMMI()\n");
	
	if(application_manager)
		application_manager->startMMI();
	
	return 0;
}

int eDVBCISlot::stopMMI()
{
	printf("edvbcislot: stopMMI()\n");

	if(mmi_session)
		mmi_session->stopMMI();
	
	return 0;
}

int eDVBCISlot::answerText(int answer)
{
	printf("edvbcislot: answerText(%d)\n", answer);

	if(mmi_session)
		mmi_session->answerText(answer);

	return 0;
}

int eDVBCISlot::answerEnq(int answer, char *value)
{
	printf("edvbcislot: answerMMI(%d,%s)\n", answer, value);
	return 0;
}

eAutoInitP0<eDVBCIInterfaces> init_eDVBCIInterfaces(eAutoInitNumbers::dvb, "CI Slots");
