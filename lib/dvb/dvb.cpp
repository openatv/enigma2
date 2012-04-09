#include <linux/dvb/frontend.h>
#include <linux/dvb/dmx.h>
#include <linux/dvb/version.h>

#include <lib/base/eerror.h>
#include <lib/base/filepush.h>
#include <lib/dvb/cahandler.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <lib/dvb/specs.h>

#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

DEFINE_REF(eDVBRegisteredFrontend);
DEFINE_REF(eDVBRegisteredDemux);

DEFINE_REF(eDVBAllocatedFrontend);

eDVBAllocatedFrontend::eDVBAllocatedFrontend(eDVBRegisteredFrontend *fe): m_fe(fe)
{
	m_fe->inc_use();
}

eDVBAllocatedFrontend::~eDVBAllocatedFrontend()
{
	m_fe->dec_use();
}

DEFINE_REF(eDVBAllocatedDemux);

eDVBAllocatedDemux::eDVBAllocatedDemux(eDVBRegisteredDemux *demux): m_demux(demux)
{
	m_demux->m_inuse++;
}

eDVBAllocatedDemux::~eDVBAllocatedDemux()
{
	--m_demux->m_inuse;
}

DEFINE_REF(eDVBResourceManager);

eDVBResourceManager *eDVBResourceManager::instance;

RESULT eDVBResourceManager::getInstance(ePtr<eDVBResourceManager> &ptr)
{
	if (instance)
	{
		ptr = instance;
		return 0;
	}
	return -1;
}

ePtr<eDVBResourceManager> NewResourceManagerPtr(void)
{
	ePtr<eDVBResourceManager> ptr;
	eDVBResourceManager::getInstance(ptr);
	return ptr;
}

eDVBResourceManager::eDVBResourceManager()
	:m_releaseCachedChannelTimer(eTimer::create(eApp))
{
	avail = 1;
	busy = 0;
	m_sec = new eDVBSatelliteEquipmentControl(m_frontend, m_simulate_frontend);

	if (!instance)
		instance = this;

	int num_adapter = 1;
	while (eDVBAdapterLinux::exist(num_adapter))
	{
		if (eDVBAdapterLinux::isusb(num_adapter))
		{
			eDVBAdapterLinux *adapter = new eDVBUsbAdapter(num_adapter);
			addAdapter(adapter);
		}
		num_adapter++;
	}

	if (eDVBAdapterLinux::exist(0))
	{
		eDVBAdapterLinux *adapter = new eDVBAdapterLinux(0);
		adapter->scanDevices();
		addAdapter(adapter, true);
	}

	int fd = open("/proc/stb/info/model", O_RDONLY);
	char tmp[16];
	int rd = fd >= 0 ? read(fd, tmp, sizeof(tmp)) : 0;
	if (fd >= 0)
		close(fd);

	if (!strncmp(tmp, "dm7025\n", rd))
		m_boxtype = DM7025;
	else if (!strncmp(tmp, "dm8000\n", rd))
		m_boxtype = DM8000;
	else if (!strncmp(tmp, "dm800\n", rd))
		m_boxtype = DM800;
	else if (!strncmp(tmp, "dm500hd\n", rd))
		m_boxtype = DM500HD;
	else if (!strncmp(tmp, "dm800se\n", rd))
		m_boxtype = DM800SE;
	else if (!strncmp(tmp, "dm7020hd\n", rd))
		m_boxtype = DM7020HD;
	else {
		eDebug("boxtype detection via /proc/stb/info not possible... use fallback via demux count!\n");
		if (m_demux.size() == 3)
			m_boxtype = DM800;
		else if (m_demux.size() < 5)
			m_boxtype = DM7025;
		else
			m_boxtype = DM8000;
	}

	eDebug("found %zd adapter, %zd frontends(%zd sim) and %zd demux, boxtype %d",
		m_adapter.size(), m_frontend.size(), m_simulate_frontend.size(), m_demux.size(), m_boxtype);

	CONNECT(m_releaseCachedChannelTimer->timeout, eDVBResourceManager::releaseCachedChannel);
}

void eDVBResourceManager::feStateChanged()
{
	int mask=0;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
		if (i->m_inuse)
			mask |= ( 1 << i->m_frontend->getSlotID() );
	/* emit */ frontendUseMaskChanged(mask);
}

std::map<std::string, std::string> eDVBAdapterLinux::mappedFrontendName;

DEFINE_REF(eDVBAdapterLinux);
eDVBAdapterLinux::eDVBAdapterLinux(int nr): m_nr(nr)
{
}

void eDVBAdapterLinux::scanDevices()
{
		// scan frontends
	int num_fe = 0;

	eDebug("scanning for frontends..");
	while (1)
	{
		struct stat s;
		char filename[128];
		sprintf(filename, "/dev/dvb/adapter%d/frontend%d", m_nr, num_fe);
		if (stat(filename, &s))
			break;
		eDVBFrontend *fe;
		std::string name = filename;
		std::map<std::string, std::string>::iterator it = mappedFrontendName.find(name);
		if (it != mappedFrontendName.end()) name = it->second;

		{
			int ok = 0;
			fe = new eDVBFrontend(name.c_str(), num_fe, ok, true);
			if (ok)
				m_simulate_frontend.push_back(ePtr<eDVBFrontend>(fe));
		}

		{
			int ok = 0;
			fe = new eDVBFrontend(name.c_str(), num_fe, ok, false, fe);
			if (ok)
				m_frontend.push_back(ePtr<eDVBFrontend>(fe));
		}
		++num_fe;
	}

		// scan demux
	int num_demux = 0;
	while (1)
	{
		struct stat s;
		char filename[128];
		sprintf(filename, "/dev/dvb/adapter%d/demux%d", m_nr, num_demux);
		if (stat(filename, &s))
			break;
		ePtr<eDVBDemux> demux;

		demux = new eDVBDemux(m_nr, num_demux);
		m_demux.push_back(demux);

		++num_demux;
	}
}

int eDVBAdapterLinux::getNumDemux()
{
	return m_demux.size();
}

RESULT eDVBAdapterLinux::getDemux(ePtr<eDVBDemux> &demux, int nr)
{
	eSmartPtrList<eDVBDemux>::iterator i(m_demux.begin());
	while (nr && (i != m_demux.end()))
	{
		--nr;
		++i;
	}

	if (i != m_demux.end())
		demux = *i;
	else
		return -1;

	return 0;
}

int eDVBAdapterLinux::getNumFrontends()
{
	return m_frontend.size();
}

RESULT eDVBAdapterLinux::getFrontend(ePtr<eDVBFrontend> &fe, int nr, bool simulate)
{
	eSmartPtrList<eDVBFrontend>::iterator i(simulate ? m_simulate_frontend.begin() : m_frontend.begin());
	while (nr && (i != m_frontend.end()))
	{
		--nr;
		++i;
	}

	if (i != m_frontend.end())
		fe = *i;
	else
		return -1;

	return 0;
}

int eDVBAdapterLinux::exist(int nr)
{
	struct stat s;
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d", nr);
	if (!stat(filename, &s))
		return 1;
	return 0;
}

bool eDVBAdapterLinux::isusb(int nr)
{
	char devicename[256];
	snprintf(devicename, sizeof(devicename), "/sys/class/dvb/dvb%d.frontend0/device/ep_00", nr);
	return ::access(devicename, X_OK) >= 0;
}

DEFINE_REF(eDVBUsbAdapter);
eDVBUsbAdapter::eDVBUsbAdapter(int nr)
: eDVBAdapterLinux(nr)
{
	FILE *file = NULL;
	char type[8];
	struct dmx_pes_filter_params filter;
	struct dvb_frontend_info fe_info;
	int frontend = -1;
	char filename[256];
	eDebug("linking adapter%d/frontend0 to vtuner%d", nr, nr - 1);

	pumpThread = NULL;

	int num_fe = 0;
	while (1)
	{
		snprintf(filename, sizeof(filename), "/dev/dvb/adapter0/frontend%d", num_fe);
		if (::access(filename, R_OK) < 0) break;
		num_fe++;
	}
	virtualFrontendName = filename;

	demuxFd = vtunerFd = pipeFd[0] = pipeFd[1] = -1;

	snprintf(filename, sizeof(filename), "/sys/class/dvb/dvb%d.frontend0/device/product", nr);
	file = fopen(filename, "r");
	if (!file)
	{
		snprintf(filename, sizeof(filename), "/sys/class/dvb/dvb%d.frontend0/device/manufacturer", nr);
		file = fopen(filename, "r");
	}

	if (file)
	{
		char *tmp = name;
		fread(tmp, sizeof(name), 1, file);
		tmp[sizeof(name) - 1] = 0;
		while (strlen(tmp) > 0 && (tmp[strlen(tmp) - 1] == '\n' || tmp[strlen(tmp) - 1] == ' ')) tmp[strlen(tmp) - 1] = 0;
		fclose(file);
	}

	snprintf(filename, sizeof(filename), "/dev/dvb/adapter%d/frontend0", nr);
	frontend = open(filename, O_RDWR);
	if (frontend < 0)
	{
		goto error;
	}
	if (::ioctl(frontend, FE_GET_INFO, &fe_info) < 0)
	{
		::close(frontend);
		frontend = -1;
		goto error;
	}
	::close(frontend);
	frontend = -1;

	usbFrontendName = filename;

	snprintf(filename, sizeof(filename), "/dev/dvb/adapter%d/demux0", nr);
	demuxFd = open(filename, O_RDONLY | O_NONBLOCK);
	if (demuxFd < 0)
	{
		goto error;
	}

	snprintf(filename, sizeof(filename), "/dev/misc/vtuner%d", nr - 1);
	vtunerFd = open(filename, O_RDWR);
	if (vtunerFd < 0)
	{
		goto error;
	}

	filter.input = DMX_IN_FRONTEND;
	filter.flags = 0;
	filter.pid = 0;
	filter.output = DMX_OUT_TSDEMUX_TAP;
	filter.pes_type = DMX_PES_OTHER;

#define DEMUX_BUFFER_SIZE (8 * ((188 / 4) * 4096)) /* 1.5MB */
	ioctl(demuxFd, DMX_SET_BUFFER_SIZE, DEMUX_BUFFER_SIZE);
	ioctl(demuxFd, DMX_SET_PES_FILTER, &filter);
	ioctl(demuxFd, DMX_START);

	switch (fe_info.type)
	{
	case FE_QPSK:
		strcpy(type,"DVB-S2");
		break;
	case FE_QAM:
		strcpy(type,"DVB-C");
		break;
	case FE_OFDM:
		strcpy(type,"DVB-T");
		break;
	case FE_ATSC:
		strcpy(type,"ATSC");
		break;
	default:
		eDebug("Frontend type 0x%x not supported", fe_info.type);
		goto error;
	}

#define VTUNER_GET_MESSAGE  1
#define VTUNER_SET_RESPONSE 2
#define VTUNER_SET_NAME     3
#define VTUNER_SET_TYPE     4
#define VTUNER_SET_HAS_OUTPUTS 5
#define VTUNER_SET_FE_INFO  6
#define VTUNER_SET_DELSYS   7
	ioctl(vtunerFd, VTUNER_SET_NAME, name);
	ioctl(vtunerFd, VTUNER_SET_TYPE, type);
	ioctl(vtunerFd, VTUNER_SET_HAS_OUTPUTS, "no");

	memset(pidList, 0xff, sizeof(pidList));

	mappedFrontendName[virtualFrontendName] = usbFrontendName;
	pipe(pipeFd);
	running = true;
	pthread_create(&pumpThread, NULL, threadproc, (void*)this);
	return;

error:
	if (vtunerFd >= 0)
	{
		close(vtunerFd);
		vtunerFd = -1;
	}
	if (demuxFd >= 0)
	{
		close(demuxFd);
		demuxFd = -1;
	}
}

eDVBUsbAdapter::~eDVBUsbAdapter()
{
	running = false;
	if (pipeFd[1] >= 0)
	{
		::close(pipeFd[1]);
		pipeFd[1] = -1;
	}
	if (pumpThread) pthread_join(pumpThread, NULL);
	if (pipeFd[0] >= 0)
	{
		::close(pipeFd[0]);
		pipeFd[0] = -1;
	}
	if (vtunerFd >= 0)
	{
		close(vtunerFd);
		vtunerFd = -1;
	}
	if (demuxFd >= 0)
	{
		close(demuxFd);
		demuxFd = -1;
	}
}

int eDVBUsbAdapter::select(int maxfd, fd_set *readfds, fd_set *writefds, fd_set *exceptfds, struct timeval *timeout)
{
	int retval;
	fd_set rset, wset, xset;
	struct timeval interval;
	timerclear(&interval);

	/* make a backup of all fd_set's and timeval struct */
	if (readfds) rset = *readfds;
	if (writefds) wset = *writefds;
	if (exceptfds) xset = *exceptfds;
	if (timeout) interval = *timeout;

	while (1)
	{
		retval = ::select(maxfd, readfds, writefds, exceptfds, timeout);

		if (retval < 0)
		{
			/* restore the backup before we continue */
			if (readfds) *readfds = rset;
			if (writefds) *writefds = wset;
			if (exceptfds) *exceptfds = xset;
			if (timeout) *timeout = interval;
			if (errno == EINTR) continue;
			break;
		}
		break;
	}
	return retval;
}

ssize_t eDVBUsbAdapter::writeAll(int fd, const void *buf, size_t count)
{
	ssize_t retval;
	char *ptr = (char*)buf;
	size_t handledcount = 0;
	if (fd < 0) return -1;
	while (handledcount < count)
	{
		retval = ::write(fd, &ptr[handledcount], count - handledcount);

		if (retval == 0) return -1;
		if (retval < 0)
		{
			if (errno == EINTR) continue;
			return retval;
		}
		handledcount += retval;
	}
	return handledcount;
}

ssize_t eDVBUsbAdapter::read(int fd, void *buf, size_t count)
{
	ssize_t retval;
	char *ptr = (char*)buf;
	size_t handledcount = 0;
	if (fd < 0) return -1;
	while (handledcount < count)
	{
		retval = ::read(fd, &ptr[handledcount], count - handledcount);
		if (retval < 0)
		{
			if (errno == EINTR) continue;
			return retval;
		}
		handledcount += retval;
		break; /* one read only */
	}
	return handledcount;
}

void *eDVBUsbAdapter::threadproc(void *arg)
{
	eDVBUsbAdapter *user = (eDVBUsbAdapter*)arg;
	return user->vtunerPump();
}

void *eDVBUsbAdapter::vtunerPump()
{
	if (vtunerFd < 0 || demuxFd < 0 || pipeFd[0] < 0) return NULL;

#define MSG_PIDLIST         14
	struct vtuner_message
	{
		int type;
		unsigned short int pidlist[30];
		unsigned char pad[64]; /* nobody knows the much data the driver will try to copy into our struct, add some padding to be sure */
	};

	while (running)
	{
		fd_set rset, xset;
		int maxfd = vtunerFd;
		if (demuxFd > maxfd) maxfd = demuxFd;
		if (pipeFd[0] > maxfd) maxfd = pipeFd[0];
		FD_ZERO(&rset);
		FD_ZERO(&xset);
		FD_SET(vtunerFd, &xset);
		FD_SET(demuxFd, &rset);
		FD_SET(pipeFd[0], &rset);
		if (select(maxfd + 1, &rset, NULL, &xset, NULL) > 0)
		{
			if (FD_ISSET(vtunerFd, &xset))
			{
				int i, j;
				struct vtuner_message message;
				memset(message.pidlist, 0xff, sizeof(message.pidlist));
				::ioctl(vtunerFd, VTUNER_GET_MESSAGE, &message);

				switch (message.type)
				{
				case MSG_PIDLIST:
					/* remove old pids */
					for (i = 0; i < 30; i++)
					{
						bool found = false;
						if (pidList[i] == 0xffff) continue;
						for (j = 0; j < 30; j++)
						{
							if (pidList[i] == message.pidlist[j])
							{
								found = true;
								break;
							}
						}

						if (found) continue;

						::ioctl(demuxFd, DMX_REMOVE_PID, &pidList[i]);
					}

					/* add new pids */
					for (i = 0; i < 30; i++)
					{
						bool found = false;
						if (message.pidlist[i] == 0xffff) continue;
						for (j = 0; j < 30; j++)
						{
							if (message.pidlist[i] == pidList[j])
							{
								found = true;
								break;
							}
						}

						if (found) continue;

						::ioctl(demuxFd, DMX_ADD_PID, &message.pidlist[i]);
					}

					/* copy pids */
					for (i = 0; i < 30; i++)
					{
						pidList[i] = message.pidlist[i];
					}
					break;
				}
			}
			if (FD_ISSET(demuxFd, &rset))
			{
				int size = read(demuxFd, buffer, sizeof(buffer));
				if (writeAll(vtunerFd, buffer, size) <= 0)
				{
					break;
				}
			}
		}
	}
}

eDVBResourceManager::~eDVBResourceManager()
{
	if (instance == this)
		instance = 0;
}

void eDVBResourceManager::addAdapter(iDVBAdapter *adapter, bool front)
{
	int num_fe = adapter->getNumFrontends();
	int num_demux = adapter->getNumDemux();

	if (front)
	{
		m_adapter.push_front(adapter);
	}
	else
	{
		m_adapter.push_back(adapter);
	}

	int i;
	for (i=0; i<num_demux; ++i)
	{
		ePtr<eDVBDemux> demux;
		if (!adapter->getDemux(demux, i))
			m_demux.push_back(new eDVBRegisteredDemux(demux, adapter));
	}

	ePtr<eDVBRegisteredFrontend> prev_dvbt_frontend;
	for (i=0; i<num_fe; ++i)
	{
		ePtr<eDVBFrontend> frontend;
		if (!adapter->getFrontend(frontend, i))
		{
			int frontendType=0;
			frontend->getFrontendType(frontendType);
			eDVBRegisteredFrontend *new_fe = new eDVBRegisteredFrontend(frontend, adapter);
			CONNECT(new_fe->stateChanged, eDVBResourceManager::feStateChanged);
			m_frontend.push_back(new_fe);
			frontend->setSEC(m_sec);
			// we must link all dvb-t frontends ( for active antenna voltage )
			if (frontendType == iDVBFrontend::feTerrestrial)
			{
				if (prev_dvbt_frontend)
				{
					prev_dvbt_frontend->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)new_fe);
					frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)&(*prev_dvbt_frontend));
				}
				prev_dvbt_frontend = new_fe;
			}
		}
	}

	prev_dvbt_frontend = 0;
	for (i=0; i<num_fe; ++i)
	{
		ePtr<eDVBFrontend> frontend;
		if (!adapter->getFrontend(frontend, i, true))
		{
			int frontendType=0;
			frontend->getFrontendType(frontendType);
			eDVBRegisteredFrontend *new_fe = new eDVBRegisteredFrontend(frontend, adapter);
//			CONNECT(new_fe->stateChanged, eDVBResourceManager::feStateChanged);
			m_simulate_frontend.push_back(new_fe);
			frontend->setSEC(m_sec);
			// we must link all dvb-t frontends ( for active antenna voltage )
			if (frontendType == iDVBFrontend::feTerrestrial)
			{
				if (prev_dvbt_frontend)
				{
					prev_dvbt_frontend->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (long)new_fe);
					frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (long)&(*prev_dvbt_frontend));
				}
				prev_dvbt_frontend = new_fe;
			}
		}
	}

}

PyObject *eDVBResourceManager::setFrontendSlotInformations(ePyObject list)
{
	if (!PyList_Check(list))
	{
		PyErr_SetString(PyExc_StandardError, "eDVBResourceManager::setFrontendSlotInformations argument should be a python list");
		return NULL;
	}
	unsigned int assigned=0;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
	{
		int pos=0;
		while (pos < PyList_Size(list)) {
			ePyObject obj = PyList_GET_ITEM(list, pos++);
			if (!i->m_frontend->setSlotInfo(obj))
				continue;
			++assigned;
			break;
		}
	}
	if (assigned != m_frontend.size()) {
		char blasel[256];
		sprintf(blasel, "eDVBResourceManager::setFrontendSlotInformations .. assigned %zd socket informations, but %d registered frontends!",
			m_frontend.size(), assigned);
		PyErr_SetString(PyExc_StandardError, blasel);
		return NULL;
	}
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_simulate_frontend.begin()); i != m_simulate_frontend.end(); ++i)
	{
		int pos=0;
		while (pos < PyList_Size(list)) {
			ePyObject obj = PyList_GET_ITEM(list, pos++);
			if (!i->m_frontend->setSlotInfo(obj))
				continue;
			break;
		}
	}
	Py_RETURN_NONE;
}

RESULT eDVBResourceManager::allocateFrontend(ePtr<eDVBAllocatedFrontend> &fe, ePtr<iDVBFrontendParameters> &feparm, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_simulate_frontend : m_frontend;
	ePtr<eDVBRegisteredFrontend> best;
	int bestval = 0;
	int foundone = 0;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(frontends.begin()); i != frontends.end(); ++i)
	{
		int c = i->m_frontend->isCompatibleWith(feparm);

		if (c)	/* if we have at least one frontend which is compatible with the source, flag this. */
			foundone = 1;

		if (!i->m_inuse)
		{
//			eDebug("Slot %d, score %d", i->m_frontend->getSlotID(), c);
			if (c > bestval)
			{
				bestval = c;
				best = i;
			}
		}
//		else
//			eDebug("Slot %d, score %d... but BUSY!!!!!!!!!!!", i->m_frontend->getSlotID(), c);
	}

	if (best)
	{
		fe = new eDVBAllocatedFrontend(best);
		return 0;
	}

	fe = 0;

	if (foundone)
		return errAllSourcesBusy;
	else
		return errNoSourceFound;
}

RESULT eDVBResourceManager::allocateFrontendByIndex(ePtr<eDVBAllocatedFrontend> &fe, int slot_index)
{
	int err = errNoSourceFound;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
		if (!i->m_inuse && i->m_frontend->getSlotID() == slot_index)
		{
			// check if another slot linked to this is in use
			long tmp;
			i->m_frontend->getData(eDVBFrontend::SATPOS_DEPENDS_PTR, tmp);
			if ( tmp != -1 )
			{
				eDVBRegisteredFrontend *satpos_depends_to_fe = (eDVBRegisteredFrontend *)tmp;
				if (satpos_depends_to_fe->m_inuse)
				{
					eDebug("another satpos depending frontend is in use.. so allocateFrontendByIndex not possible!");
					err = errAllSourcesBusy;
					goto alloc_fe_by_id_not_possible;
				}
			}
			else // check linked tuners
			{
				i->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, tmp);
				while ( tmp != -1 )
				{
					eDVBRegisteredFrontend *next = (eDVBRegisteredFrontend *) tmp;
					if (next->m_inuse)
					{
						eDebug("another linked frontend is in use.. so allocateFrontendByIndex not possible!");
						err = errAllSourcesBusy;
						goto alloc_fe_by_id_not_possible;
					}
					next->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, tmp);
				}
				i->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, tmp);
				while ( tmp != -1 )
				{
					eDVBRegisteredFrontend *prev = (eDVBRegisteredFrontend *) tmp;
					if (prev->m_inuse)
					{
						eDebug("another linked frontend is in use.. so allocateFrontendByIndex not possible!");
						err = errAllSourcesBusy;
						goto alloc_fe_by_id_not_possible;
					}
					prev->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, tmp);
				}
			}
			fe = new eDVBAllocatedFrontend(i);
			return 0;
		}
alloc_fe_by_id_not_possible:
	fe = 0;
	return err;
}

#define capHoldDecodeReference 64

RESULT eDVBResourceManager::allocateDemux(eDVBRegisteredFrontend *fe, ePtr<eDVBAllocatedDemux> &demux, int &cap)
{
		/* find first unused demux which is on same adapter as frontend (or any, if PVR)
		   never use the first one unless we need a decoding demux. */

	eDebug("allocate demux");
	eSmartPtrList<eDVBRegisteredDemux>::iterator i(m_demux.begin());

	if (i == m_demux.end())
		return -1;

	ePtr<eDVBRegisteredDemux> unused;

	if (m_boxtype == DM7025) // ATI
	{
		/* FIXME: hardware demux policy */
		int n=0;
		if (!(cap & iDVBChannel::capDecode))
		{
			if (m_demux.size() > 2)  /* assumed to be true, otherwise we have lost anyway */
			{
				++i, ++n;
				++i, ++n;
			}
		}

		for (; i != m_demux.end(); ++i, ++n)
		{
			int is_decode = n < 2;

			int in_use = is_decode ? (i->m_demux->getRefCount() != 2) : i->m_inuse;

			if ((!in_use) && ((!fe) || (i->m_adapter == fe->m_adapter)))
			{
				if ((cap & iDVBChannel::capDecode) && !is_decode)
					continue;
				unused = i;
				break;
			}
		}
	}
	else
	{
		iDVBAdapter *adapter = fe ? fe->m_adapter : m_adapter.begin(); /* look for a demux on the same adapter as the frontend, or the first adapter for dvr playback */
		int source = fe ? fe->m_frontend->getDVBID() : -1;
		cap |= capHoldDecodeReference; // this is checked in eDVBChannel::getDemux
		if (!fe)
		{
			/*
			 * For pvr playback, start with the last demux.
			 * On some hardware, we have less ca devices than demuxes,
			 * so we should try to leave the first demuxes for live tv,
			 * and start with the last for pvr playback
			 */
			i = m_demux.end();
			--i;
		}
		while (i != m_demux.end())
		{
			if (i->m_adapter == adapter)
			{
				if (!i->m_inuse)
				{
					/* mark the first unused demux, we'll use that when we do not find a better match */
					if (!unused) unused = i;
				}
				else
				{
					/* demux is in use, see if we can share it */
					if (source >= 0 && i->m_demux->getSource() == source)
					{
						demux = new eDVBAllocatedDemux(i);
						return 0;
					}
				}
			}
			if (fe)
			{
				++i;
			}
			else
			{
				--i;
			}
		}
	}

	if (unused)
	{
		demux = new eDVBAllocatedDemux(unused);
		if (fe)
			demux->get().setSourceFrontend(fe->m_frontend->getDVBID());
		else
			demux->get().setSourcePVR(0);
		return 0;
	}

	eDebug("demux not found");
	return -1;
}

RESULT eDVBResourceManager::setChannelList(iDVBChannelList *list)
{
	m_list = list;
	return 0;
}

RESULT eDVBResourceManager::getChannelList(ePtr<iDVBChannelList> &list)
{
	list = m_list;
	if (list)
		return 0;
	else
		return -ENOENT;
}

#define eDebugNoSimulate(x...) \
	do { \
		if (!simulate) \
			eDebug(x); \
	} while(0)


RESULT eDVBResourceManager::allocateChannel(const eDVBChannelID &channelid, eUsePtr<iDVBChannel> &channel, bool simulate)
{
		/* first, check if a channel is already existing. */
	std::list<active_channel> &active_channels = simulate ? m_active_simulate_channels : m_active_channels;

	if (!simulate && m_cached_channel)
	{
		eDVBChannel *cache_chan = (eDVBChannel*)&(*m_cached_channel);
		if(channelid==cache_chan->getChannelID())
		{
			eDebug("use cached_channel");
			channel = m_cached_channel;
			return 0;
		}
		m_cached_channel_state_changed_conn.disconnect();
		m_cached_channel=0;
		m_releaseCachedChannelTimer->stop();
	}

	eDebugNoSimulate("allocate channel.. %04x:%04x", channelid.transport_stream_id.get(), channelid.original_network_id.get());
	for (std::list<active_channel>::iterator i(active_channels.begin()); i != active_channels.end(); ++i)
	{
		eDebugNoSimulate("available channel.. %04x:%04x", i->m_channel_id.transport_stream_id.get(), i->m_channel_id.original_network_id.get());
		if (i->m_channel_id == channelid)
		{
			eDebugNoSimulate("found shared channel..");
			channel = i->m_channel;
			return 0;
		}
	}

	/* no currently available channel is tuned to this channelid. create a new one, if possible. */

	if (!m_list)
	{
		eDebugNoSimulate("no channel list set!");
		return errNoChannelList;
	}

	ePtr<iDVBFrontendParameters> feparm;
	if (m_list->getChannelFrontendData(channelid, feparm))
	{
		eDebugNoSimulate("channel not found!");
		return errChannelNotInList;
	}

	/* allocate a frontend. */

	ePtr<eDVBAllocatedFrontend> fe;

	int err = allocateFrontend(fe, feparm, simulate);
	if (err)
		return err;

	RESULT res;
	ePtr<eDVBChannel> ch = new eDVBChannel(this, fe);

	res = ch->setChannel(channelid, feparm);
	if (res)
	{
		channel = 0;
		return errChidNotFound;
	}

	if (simulate)
		channel = ch;
	else
	{
		m_cached_channel = channel = ch;
		m_cached_channel_state_changed_conn =
			CONNECT(ch->m_stateChanged,eDVBResourceManager::DVBChannelStateChanged);
	}

	return 0;
}

void eDVBResourceManager::DVBChannelStateChanged(iDVBChannel *chan)
{
	int state=0;
	chan->getState(state);
	switch (state)
	{
		case iDVBChannel::state_release:
		case iDVBChannel::state_ok:
		{
			eDebug("stop release channel timer");
			m_releaseCachedChannelTimer->stop();
			break;
		}
		case iDVBChannel::state_last_instance:
		{
			eDebug("start release channel timer");
			m_releaseCachedChannelTimer->start(3000, true);
			break;
		}
		default: // ignore all other events
			break;
	}
}

void eDVBResourceManager::releaseCachedChannel()
{
	eDebug("release cached channel (timer timeout)");
	m_cached_channel=0;
}

RESULT eDVBResourceManager::allocateRawChannel(eUsePtr<iDVBChannel> &channel, int slot_index)
{
	ePtr<eDVBAllocatedFrontend> fe;

	if (m_cached_channel)
	{
		m_cached_channel_state_changed_conn.disconnect();
		m_cached_channel=0;
		m_releaseCachedChannelTimer->stop();
	}

	int err = allocateFrontendByIndex(fe, slot_index);
	if (err)
		return err;

	channel = new eDVBChannel(this, fe);
	return 0;
}


RESULT eDVBResourceManager::allocatePVRChannel(const eDVBChannelID &channelid, eUsePtr<iDVBPVRChannel> &channel)
{
	ePtr<eDVBAllocatedDemux> demux;

	if (m_cached_channel && m_releaseCachedChannelTimer->isActive())
	{
		m_cached_channel_state_changed_conn.disconnect();
		m_cached_channel=0;
		m_releaseCachedChannelTimer->stop();
	}

	ePtr<eDVBChannel> ch = new eDVBChannel(this, 0);
	if (channelid)
	{
		/* 
		 * user provided a channelid, with the clear intention for 
		 * this channel to be registered at the resource manager.
		 * (allowing e.g. epgcache to be started) 
		 */
		ePtr<iDVBFrontendParameters> feparm;
		ch->setChannel(channelid, feparm);
	}
	channel = ch;
	return 0;
}

RESULT eDVBResourceManager::addChannel(const eDVBChannelID &chid, eDVBChannel *ch)
{
	bool simulate = false;
	ePtr<iDVBFrontend> fe;
	if (!ch->getFrontend(fe))
	{
		eDVBFrontend *frontend = (eDVBFrontend*)&(*fe);
		simulate = frontend->is_simulate();
	}
	std::list<active_channel> &active_channels = simulate ? m_active_simulate_channels : m_active_channels;
	active_channels.push_back(active_channel(chid, ch));
	if (!simulate) 
	{
		/* emit */ m_channelAdded(ch);
	}
	return 0;
}

RESULT eDVBResourceManager::removeChannel(eDVBChannel *ch)
{
	bool simulate = false;
	ePtr<iDVBFrontend> fe;
	if (!ch->getFrontend(fe))
	{
		eDVBFrontend *frontend = (eDVBFrontend*)&(*fe);
		simulate = frontend->is_simulate();
	}
	std::list<active_channel> &active_channels = simulate ? m_active_simulate_channels : m_active_channels;
	int cnt = 0;
	for (std::list<active_channel>::iterator i(active_channels.begin()); i != active_channels.end();)
	{
		if (i->m_channel == ch)
		{
			i = active_channels.erase(i);
			++cnt;
		} else
			++i;
	}
	ASSERT(cnt == 1);
	if (cnt == 1)
		return 0;
	return -ENOENT;
}

RESULT eDVBResourceManager::connectChannelAdded(const Slot1<void,eDVBChannel*> &channelAdded, ePtr<eConnection> &connection)
{
	connection = new eConnection((eDVBResourceManager*)this, m_channelAdded.connect(channelAdded));
	return 0;
}

int eDVBResourceManager::canAllocateFrontend(ePtr<iDVBFrontendParameters> &feparm, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_simulate_frontend : m_frontend;
	ePtr<eDVBRegisteredFrontend> best;
	int bestval = 0;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(frontends.begin()); i != frontends.end(); ++i)
		if (!i->m_inuse)
		{
			int c = i->m_frontend->isCompatibleWith(feparm);
			if (c > bestval)
				bestval = c;
		}
	return bestval;
}

int tuner_type_channel_default(ePtr<iDVBChannelList> &channellist, const eDVBChannelID &chid)
{
	if (channellist)
	{
		ePtr<iDVBFrontendParameters> feparm;
		if (!channellist->getChannelFrontendData(chid, feparm))
		{
			int system;
			if (!feparm->getSystem(system))
			{
				switch(system)
				{
					case iDVBFrontend::feSatellite:
						return 50000;
					case iDVBFrontend::feCable:
						return 40000;
					case iDVBFrontend::feTerrestrial:
						return 30000;
					default:
						break;
				}
			}
		}
	}
	return 0;
}

int eDVBResourceManager::canAllocateChannel(const eDVBChannelID &channelid, const eDVBChannelID& ignore, bool simulate)
{
	std::list<active_channel> &active_channels = simulate ? m_active_simulate_channels : m_active_channels;
	int ret=0;
	if (!simulate && m_cached_channel)
	{
		eDVBChannel *cache_chan = (eDVBChannel*)&(*m_cached_channel);
		if(channelid==cache_chan->getChannelID())
			return tuner_type_channel_default(m_list, channelid);
	}

		/* first, check if a channel is already existing. */
//	eDebug("allocate channel.. %04x:%04x", channelid.transport_stream_id.get(), channelid.original_network_id.get());
	for (std::list<active_channel>::iterator i(active_channels.begin()); i != active_channels.end(); ++i)
	{
//		eDebug("available channel.. %04x:%04x", i->m_channel_id.transport_stream_id.get(), i->m_channel_id.original_network_id.get());
		if (i->m_channel_id == channelid)
		{
//			eDebug("found shared channel..");
			return tuner_type_channel_default(m_list, channelid);
		}
	}

	int *decremented_cached_channel_fe_usecount=NULL,
		*decremented_fe_usecount=NULL;

	for (std::list<active_channel>::iterator i(active_channels.begin()); i != active_channels.end(); ++i)
	{
		eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_simulate_frontend : m_frontend;
//		eDebug("available channel.. %04x:%04x", i->m_channel_id.transport_stream_id.get(), i->m_channel_id.original_network_id.get());
		if (i->m_channel_id == ignore)
		{
			eDVBChannel *channel = (eDVBChannel*) &(*i->m_channel);
			// one eUsePtr<iDVBChannel> is used in eDVBServicePMTHandler
			// another on eUsePtr<iDVBChannel> is used in the eDVBScan instance used in eDVBServicePMTHandler (for SDT scan)
			// so we must check here if usecount is 3 (when the channel is equal to the cached channel)
			// or 2 when the cached channel is not equal to the compared channel
			if (channel == &(*m_cached_channel) ? channel->getUseCount() == 3 : channel->getUseCount() == 2)  // channel only used once..
			{
				ePtr<iDVBFrontend> fe;
				if (!i->m_channel->getFrontend(fe))
				{
					for (eSmartPtrList<eDVBRegisteredFrontend>::iterator ii(frontends.begin()); ii != frontends.end(); ++ii)
					{
						if ( &(*fe) == &(*ii->m_frontend) )
						{
							--ii->m_inuse;
							decremented_fe_usecount = &ii->m_inuse;
							if (channel == &(*m_cached_channel))
								decremented_cached_channel_fe_usecount = decremented_fe_usecount;
							break;
						}
					}
				}
			}
			break;
		}
	}

	if (!decremented_cached_channel_fe_usecount)
	{
		if (m_cached_channel)
		{
			eDVBChannel *channel = (eDVBChannel*) &(*m_cached_channel);
			if (channel->getUseCount() == 1)
			{
				ePtr<iDVBFrontend> fe;
				if (!channel->getFrontend(fe))
				{
					eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_simulate_frontend : m_frontend;
					for (eSmartPtrList<eDVBRegisteredFrontend>::iterator ii(frontends.begin()); ii != frontends.end(); ++ii)
					{
						if ( &(*fe) == &(*ii->m_frontend) )
						{
							--ii->m_inuse;
							decremented_cached_channel_fe_usecount = &ii->m_inuse;
							break;
						}
					}
				}
			}
		}
	}
	else
		decremented_cached_channel_fe_usecount=NULL;

	ePtr<iDVBFrontendParameters> feparm;

	if (!m_list)
	{
		eDebug("no channel list set!");
		goto error;
	}

	if (m_list->getChannelFrontendData(channelid, feparm))
	{
		eDebug("channel not found!");
		goto error;
	}

	ret = canAllocateFrontend(feparm, simulate);

error:
	if (decremented_fe_usecount)
		++(*decremented_fe_usecount);
	if (decremented_cached_channel_fe_usecount)
		++(*decremented_cached_channel_fe_usecount);

	return ret;
}

bool eDVBResourceManager::canMeasureFrontendInputPower()
{
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
	{
		return i->m_frontend->readInputpower() >= 0;
	}
	return false;
}

class eDVBChannelFilePush: public eFilePushThread
{
public:
	eDVBChannelFilePush(int packetsize = 188):
		eFilePushThread(IOPRIO_CLASS_BE, 0, packetsize, 65536), // 64k buffer for playback
		m_iframe_search(0),
		m_iframe_state(0),
		m_pid(0),
		m_timebase_change(0),
		m_packet_size(packetsize),
		m_parity_switch_delay(0),
		m_parity(-1)
	{}
	void setIFrameSearch(int enabled) { m_iframe_search = enabled; m_iframe_state = 0; }

			/* "timebase change" is for doing trickmode playback at an exact speed, even when pictures are skipped. */
			/* you need to set it to 1/16 if you want 16x playback, for example. you need video master sync. */
	void setTimebaseChange(int ratio) { m_timebase_change = ratio; } /* 16bit fixpoint, 0 for disable */
	void setParitySwitchDelay(int msdelay) { m_parity_switch_delay = msdelay; }
protected:
	int m_iframe_search, m_iframe_state, m_pid;
	int m_timebase_change;
	int m_packet_size;
	int m_parity_switch_delay;
	int m_parity;
	int filterRecordData(const unsigned char *data, int len, size_t &current_span_remaining);
};

int eDVBChannelFilePush::filterRecordData(const unsigned char *_data, int len, size_t &current_span_remaining)
{
	if (m_parity_switch_delay)
	{
		int offset;
		for (offset = 0; offset < len; offset += m_packet_size)
		{
			unsigned char *pkt = (unsigned char*)_data + offset + m_packet_size - 188;
			if (pkt[3] & 0xc0)
			{
				int parity = (pkt[3] & 0x40) ? 1 : 0;
				if (parity != m_parity)
				{
					if (m_parity >= 0)
					{
						usleep(m_parity_switch_delay * 1000);
					}
					m_parity = parity;
					break;
				}
			}
		}
	}
#if 0
	if (m_timebase_change)
	{
		eDebug("timebase change: %d", m_timebase_change);
		int offset;
		for (offset = 0; offset < len; offset += 188)
		{
			unsigned char *pkt = (unsigned char*)_data + offset;
			if (pkt[1] & 0x40) /* pusi */
			{
				if (pkt[3] & 0x20) // adaption field present?
					pkt += pkt[4] + 4 + 1;  /* skip adaption field and header */
				else
					pkt += 4; /* skip header */
				if (pkt[0] || pkt[1] || (pkt[2] != 1))
				{
					eWarning("broken startcode");
					continue;
				}

				pts_t pts = 0;

				if (pkt[7] & 0x80) // PTS present?
				{
					pts  = ((unsigned long long)(pkt[ 9]&0xE))  << 29;
					pts |= ((unsigned long long)(pkt[10]&0xFF)) << 22;
					pts |= ((unsigned long long)(pkt[11]&0xFE)) << 14;
					pts |= ((unsigned long long)(pkt[12]&0xFF)) << 7;
					pts |= ((unsigned long long)(pkt[13]&0xFE)) >> 1;

#if 0
					off_t off = 0;
					RESULT r = m_tstools.fixupPTS(off, pts);
					if (r)
						eWarning("fixup PTS while trickmode playback failed.\n");
#endif

					int sec = pts / 90000;
					int frm = pts % 90000;
					int min = sec / 60;
					sec %= 60;
					int hr = min / 60;
					min %= 60;
					int d = hr / 24;
					hr %= 24;

//					eDebug("original, fixed pts: %016llx %d:%02d:%02d:%02d:%05d", pts, d, hr, min, sec, frm);

					pts += 0x80000000LL;
					pts *= m_timebase_change;
					pts >>= 16;

					sec = pts / 90000;
					frm = pts % 90000;
					min = sec / 60;
					sec %= 60;
					hr = min / 60;
					min %= 60;
					d = hr / 24;
					hr %= 24;

//					eDebug("new pts (after timebase change): %016llx %d:%02d:%02d:%02d:%05d", pts, d, hr, min, sec, frm);

					pkt[9] &= ~0xE;
					pkt[10] = 0;
					pkt[11] &= ~1;
					pkt[12] = 0;
					pkt[13] &= ~1;

					pkt[9]  |= (pts >> 29) & 0xE;
					pkt[10] |= (pts >> 22) & 0xFF;
					pkt[11] |= (pts >> 14) & 0xFE;
					pkt[12] |= (pts >> 7) & 0xFF;
					pkt[13] |= (pts << 1) & 0xFE;
				}
			}
		}
	}
#endif

#if 0
	if (!m_iframe_search)
		return len;

	unsigned char *data = (unsigned char*)_data; /* remove that const. we know what we are doing. */

//	eDebug("filterRecordData, size=%d (mod 188=%d), first byte is %02x", len, len %188, data[0]);

	unsigned char *d = data;
	while ((d + 3 < data + len) && (d = (unsigned char*)memmem(d, data + len - d, "\x00\x00\x01", 3)))
	{
		int offset = d - data;
		int ts_offset = offset - offset % 188; /* offset to the start of TS packet */
		unsigned char *ts = data + ts_offset;
		int pid = ((ts[1] << 8) | ts[2]) & 0x1FFF;

		if ((d[3] == 0 || d[3] == 0x09 && d[-1] == 0 && (ts[1] & 0x40)) && (m_pid == pid))  /* picture start */
		{
			int picture_type = (d[3]==0 ? (d[5] >> 3) & 7 : (d[4] >> 5) + 1);
			d += 4;

//			eDebug("%d-frame at %d, offset in TS packet: %d, pid=%04x", picture_type, offset, offset % 188, pid);

			if (m_iframe_state == 1)
			{
					/* we are allowing data, and stop allowing data on the next frame.
					   we now found a frame. so stop here. */
				memset(data + offset, 0, 188 - (offset%188)); /* zero out rest of TS packet */
				current_span_remaining = 0;
				m_iframe_state = 0;
				unsigned char *fts = ts + 188;
				while (fts < (data + len))
				{
					fts[1] |= 0x1f;
					fts[2] |= 0xff; /* drop packet */
					fts += 188;
				}

				return len; // ts_offset + 188; /* deliver this packet, but not more. */
			} else
			{
				if (picture_type != 1) /* we are only interested in I frames */
					continue;

				unsigned char *fts = data;
				while (fts < ts)
				{
					fts[1] |= 0x1f;
					fts[2] |= 0xff; /* drop packet */

					fts += 188;
				}

				m_iframe_state = 1;
			}
		} else if ((d[3] & 0xF0) == 0xE0) /* video stream */
		{
				/* verify that this is actually a PES header, not just some ES data */
			if (ts[1] & 0x40) /* PUSI set */
			{
				int payload_start = 4;
				if (ts[3] & 0x20) /* adaptation field present */
					payload_start += ts[4] + 1; /* skip AF */
				if (payload_start == (offset%188)) /* the 00 00 01 should be directly at the payload start, otherwise it's not a PES header */
				{
					if (m_pid != pid)
					{
						eDebug("now locked to pid %04x (%02x %02x %02x %02x)", pid, ts[0], ts[1], ts[2], ts[3]);
						m_pid = pid;
					}
				}
			}
//			m_pid = 0x6e;
			d += 4;
		} else
			d += 4; /* ignore */
	}

	if (m_iframe_state == 1)
		return len;
	else
		return 0; /* we need find an iframe first */
#else
	return len;
#endif
}

DEFINE_REF(eDVBChannel);

eDVBChannel::eDVBChannel(eDVBResourceManager *mgr, eDVBAllocatedFrontend *frontend): m_state(state_idle), m_mgr(mgr)
{
	m_frontend = frontend;

	m_pvr_thread = 0;
	m_pvr_fd_dst = -1;

	m_skipmode_n = m_skipmode_m = m_skipmode_frames = 0;

	if (m_frontend)
		m_frontend->get().connectStateChange(slot(*this, &eDVBChannel::frontendStateChanged), m_conn_frontendStateChanged);
}

eDVBChannel::~eDVBChannel()
{
	if (m_channel_id)
		m_mgr->removeChannel(this);

	stopFile();
}

void eDVBChannel::frontendStateChanged(iDVBFrontend*fe)
{
	int state, ourstate = 0;

		/* if we are already in shutdown, don't change state. */
	if (m_state == state_release)
		return;

	if (fe->getState(state))
		return;

	if (state == iDVBFrontend::stateLock)
	{
		eDebug("OURSTATE: ok");
		ourstate = state_ok;
	} else if (state == iDVBFrontend::stateTuning)
	{
		eDebug("OURSTATE: tuning");
		ourstate = state_tuning;
	} else if (state == iDVBFrontend::stateLostLock)
	{
			/* on managed channels, we try to retune in order to re-acquire lock. */
		if (m_current_frontend_parameters)
		{
			eDebug("OURSTATE: lost lock, trying to retune");
			ourstate = state_tuning;
			m_frontend->get().tune(*m_current_frontend_parameters);
		} else
			/* on unmanaged channels, we don't do this. the client will do this. */
		{
			eDebug("OURSTATE: lost lock, unavailable now.");
			ourstate = state_unavailable;
		}
	} else if (state == iDVBFrontend::stateFailed)
	{
		ourstate = state_failed;
			/* on managed channels, we do a retry */
		if (m_current_frontend_parameters)
		{
			eDebug("OURSTATE: failed, retune");
			m_frontend->get().tune(*m_current_frontend_parameters);
		} else
		{ /* nothing we can do */
			eDebug("OURSTATE: failed, fatal");
		}
	} else
		eFatal("state unknown");

	if (ourstate != m_state)
	{
		m_state = ourstate;
		m_stateChanged(this);
	}
}

void eDVBChannel::pvrEvent(int event)
{
	switch (event)
	{
	case eFilePushThread::evtEOF:
		eDebug("eDVBChannel: End of file!");
		m_event(this, evtEOF);
		break;
	case eFilePushThread::evtUser: /* start */
		eDebug("SOF");
		m_event(this, evtSOF);
		break;
	case eFilePushThread::evtStopped:
		eDebug("eDVBChannel: pvrEvent evtStopped");
		m_event(this, evtStopped);
		break;
	}
}

void eDVBChannel::cueSheetEvent(int event)
{
		/* we might end up here if playing failed or stopped, but the client hasn't (yet) noted. */
	if (!m_pvr_thread)
		return;
	switch (event)
	{
	case eCueSheet::evtSeek:
		eDebug("seek.");
		flushPVR(m_cue->m_decoding_demux);
		break;
	case eCueSheet::evtSkipmode:
	{
		{
			m_cue->m_lock.WrLock();
			m_cue->m_seek_requests.push_back(std::pair<int, pts_t>(1, 0)); /* resync */
			m_cue->m_lock.Unlock();
			eRdLocker l(m_cue->m_lock);
			if (m_cue->m_skipmode_ratio)
			{
				m_tstools_lock.lock();
				int bitrate = m_tstools.calcBitrate(); /* in bits/s */
				m_tstools_lock.unlock();
				eDebug("skipmode ratio is %lld:90000, bitrate is %d bit/s", m_cue->m_skipmode_ratio, bitrate);
						/* i agree that this might look a bit like black magic. */
				m_skipmode_n = 512*1024; /* must be 1 iframe at least. */
				m_skipmode_m = bitrate / 8 / 90000 * m_cue->m_skipmode_ratio / 8;
				m_skipmode_frames = m_cue->m_skipmode_ratio / 90000;
				m_skipmode_frames_remainder = 0;

				if (m_cue->m_skipmode_ratio < 0)
					m_skipmode_m -= m_skipmode_n;

				eDebug("resolved to: %d %d", m_skipmode_m, m_skipmode_n);

				if (abs(m_skipmode_m) < abs(m_skipmode_n))
				{
					eWarning("something is wrong with this calculation");
					m_skipmode_frames = m_skipmode_n = m_skipmode_m = 0;
				}
			} else
			{
				eDebug("skipmode ratio is 0, normal play");
				m_skipmode_frames = m_skipmode_n = m_skipmode_m = 0;
			}
		}
		m_pvr_thread->setIFrameSearch(m_skipmode_n != 0);
		if (m_cue->m_skipmode_ratio != 0)
			m_pvr_thread->setTimebaseChange(0x10000 * 9000 / (m_cue->m_skipmode_ratio / 10)); /* negative values are also ok */
		else
			m_pvr_thread->setTimebaseChange(0); /* normal playback */
		eDebug("flush pvr");
		flushPVR(m_cue->m_decoding_demux);
		eDebug("done");
		break;
	}
	case eCueSheet::evtSpanChanged:
	{
		m_source_span.clear();
		for (std::list<std::pair<pts_t, pts_t> >::const_iterator i(m_cue->m_spans.begin()); i != m_cue->m_spans.end(); ++i)
		{
			off_t offset_in, offset_out;
			pts_t pts_in = i->first, pts_out = i->second;
			m_tstools_lock.lock();
			bool r = m_tstools.getOffset(offset_in, pts_in, -1) || m_tstools.getOffset(offset_out, pts_out, 1);
			m_tstools_lock.unlock();
			if (r)
			{
				eDebug("span translation failed.\n");
				continue;
			}
			eDebug("source span: %llx .. %llx, translated to %llx..%llx", pts_in, pts_out, offset_in, offset_out);
			m_source_span.push_back(std::pair<off_t, off_t>(offset_in, offset_out));
		}
		break;
	}
	}
}

	/* align toward zero */
static inline long long align(long long x, int align)
{
	if (x < 0)
	{
		return x - (x % (-align));
	}
	else
	{
		return x - (x % align);
	}
}


	/* remember, this gets called from another thread. */
void eDVBChannel::getNextSourceSpan(off_t current_offset, size_t bytes_read, off_t &start, size_t &size)
{
	const int blocksize = 188;
	unsigned int max = align(10*1024*1024, blocksize);
	current_offset = align(current_offset, blocksize);

	if (!m_cue)
	{
		eDebug("no cue sheet. forcing normal play");
		start = current_offset;
		size = max;
		return;
	}

	if (m_skipmode_n)
	{
		max = align(m_skipmode_n, blocksize);
	}

	//eDebug("getNextSourceSpan, current offset is %08llx, m_skipmode_m = %d!", current_offset, m_skipmode_m);
	int frame_skip_success = 0;

	if (m_skipmode_m)
	{
		int frames_to_skip = m_skipmode_frames + m_skipmode_frames_remainder;
		//eDebug("we are at %llx, and we try to skip %d+%d frames from here", current_offset, m_skipmode_frames, m_skipmode_frames_remainder);
		size_t iframe_len;
		off_t iframe_start = current_offset;
		int frames_skipped = frames_to_skip;
		m_tstools_lock.lock();
		int r = m_tstools.findNextPicture(iframe_start, iframe_len, frames_skipped);
		m_tstools_lock.unlock();
		if (!r)
		{
			m_skipmode_frames_remainder = frames_to_skip - frames_skipped;
			//eDebug("successfully skipped %d (out of %d, rem now %d) frames.", frames_skipped, frames_to_skip, m_skipmode_frames_remainder);
			current_offset = align(iframe_start, blocksize);
			max = align(iframe_len + 187, blocksize);
			frame_skip_success = 1;
		} else
		{
			m_skipmode_frames_remainder = 0;
			eDebug("frame skipping failed, reverting to byte-skipping");
		}
	}
	
	if (!frame_skip_success)
	{
		current_offset += align(m_skipmode_m, blocksize);
		
		if (m_skipmode_m)
		{
			eDebug("we are at %llx, and we try to find the iframe here:", current_offset);
			size_t iframe_len;
			off_t iframe_start = current_offset;
			
			int direction = (m_skipmode_m < 0) ? -1 : +1;
			m_tstools_lock.lock();
			int r = m_tstools.findFrame(iframe_start, iframe_len, direction);
			m_tstools_lock.unlock();
			if (r)
				eDebug("failed");
			else
			{
				current_offset = align(iframe_start, blocksize);
				max = align(iframe_len, blocksize);
			}
		}
	}

	m_cue->m_lock.RdLock();

	while (!m_cue->m_seek_requests.empty())
	{
		std::pair<int, pts_t> seek = m_cue->m_seek_requests.front();
		m_cue->m_lock.Unlock();
		m_cue->m_lock.WrLock();
		m_cue->m_seek_requests.pop_front();
		m_cue->m_lock.Unlock();
		m_cue->m_lock.RdLock();
		int relative = seek.first;
		pts_t pts = seek.second;
		pts_t now = 0;
		if (relative)
		{
			if (!m_cue->m_decoder)
			{
				eDebug("no decoder - can't seek relative");
				continue;
			}
			if (m_cue->m_decoder->getPTS(0, now))
			{
				eDebug("decoder getPTS failed, can't seek relative");
				continue;
			}
			if (!m_cue->m_decoding_demux)
			{
				eDebug("getNextSourceSpan, no decoding demux. couldn't seek to %llx... ignore request!", pts);
				start = current_offset;
				size = max;
				continue;
			}
			if (getCurrentPosition(m_cue->m_decoding_demux, now, 1))
			{
				eDebug("seekTo: getCurrentPosition failed!");
				continue;
			}
		} else if (pts < 0) /* seek relative to end */
		{
			pts_t len;
			if (!getLength(len))
			{
				eDebug("seeking relative to end. len=%lld, seek = %lld", len, pts);
				pts += len;
			} else
			{
				eWarning("getLength failed - can't seek relative to end!");
				continue;
			}
		}

		if (relative == 1) /* pts relative */
		{
			pts += now;
			if (pts < 0)
				pts = 0;
		}

		if (relative != 2)
			if (pts < 0)
				pts = 0;

		if (relative == 2) /* AP relative */
		{
			eDebug("AP relative seeking: %lld, at %lld", pts, now);
			pts_t nextap;
			eSingleLocker l(m_tstools_lock);
			if (m_tstools.getNextAccessPoint(nextap, now, pts))
			{
				pts = now - 90000; /* approx. 1s */
				eDebug("AP relative seeking failed!");
			} else
			{
				pts = nextap;
				eDebug("next ap is %llu\n", pts);
			}
		}

		off_t offset = 0;
		m_tstools_lock.lock();
		int r = m_tstools.getOffset(offset, pts, -1);
		m_tstools_lock.unlock();
		if (r)
		{
			eDebug("get offset for pts=%llu failed!", pts);
			continue;
		}
		
		eDebug("ok, resolved skip (rel: %d, diff %lld), now at %08llx", relative, pts, offset);
		current_offset = align(offset, blocksize); /* in case tstools return non-aligned offset */
	}

	m_cue->m_lock.Unlock();

	for (std::list<std::pair<off_t, off_t> >::const_iterator i(m_source_span.begin()); i != m_source_span.end(); ++i)
	{
		long long aligned_start = align(i->first, blocksize);
		long long aligned_end = align(i->second, blocksize);

		if ((current_offset >= aligned_start) && (current_offset < aligned_end))
		{
			start = current_offset;
				/* max can not exceed max(size_t). aligned_end - current_offset, however, can. */
			if ((aligned_end - current_offset) > max)
				size = max;
			else
				size = aligned_end - current_offset;
			eDebug("HIT, %lld < %lld < %lld, size: %zd", i->first, current_offset, i->second, size);
			return;
		}
		if (current_offset < aligned_start)
		{
				/* ok, our current offset is in an 'out' zone. */
			if ((m_skipmode_m >= 0) || (i == m_source_span.begin()))
			{
					/* in normal playback, just start at the next zone. */
				start = i->first;

					/* size is not 64bit! */
				if ((i->second - i->first) > max)
					size = max;
				else
					size = aligned_end - aligned_start;

				eDebug("skip");
				if (m_skipmode_m < 0)
				{
					eDebug("reached SOF");
						/* reached SOF */
					m_skipmode_m = 0;
					m_pvr_thread->sendEvent(eFilePushThread::evtUser);
				}
			} else
			{
					/* when skipping reverse, however, choose the zone before. */
				--i;
				eDebug("skip to previous block, which is %llx..%llx", i->first, i->second);
				size_t len;

				aligned_start = align(i->first, blocksize);
				aligned_end = align(i->second, blocksize);

				if ((aligned_end - aligned_start) > max)
					len = max;
				else
					len = aligned_end - aligned_start;

				start = aligned_end - len;
				eDebug("skipping to %llx, %zd", start, len);
			}

			eDebug("result: %llx, %zx (%llx %llx)", start, size, aligned_start, aligned_end);
			return;
		}
	}

	if ((current_offset < -m_skipmode_m) && (m_skipmode_m < 0))
	{
		eDebug("reached SOF");
		m_skipmode_m = 0;
		m_pvr_thread->sendEvent(eFilePushThread::evtUser);
	}

	start = current_offset;
	if (m_source_span.empty())
	{
		size = max;
		// eDebug("NO CUESHEET. (%08llx, %zd)", start, size);
	} else
	{
		size = 0;
	}
	return;
}

void eDVBChannel::AddUse()
{
	if (++m_use_count > 1 && m_state == state_last_instance)
	{
		m_state = state_ok;
		m_stateChanged(this);
	}
}

void eDVBChannel::ReleaseUse()
{
	if (!--m_use_count)
	{
		m_state = state_release;
		m_stateChanged(this);
	}
	else if (m_use_count == 1)
	{
		m_state = state_last_instance;
		m_stateChanged(this);
	}
}

RESULT eDVBChannel::setChannel(const eDVBChannelID &channelid, ePtr<iDVBFrontendParameters> &feparm)
{
	if (m_channel_id)
		m_mgr->removeChannel(this);

	if (!channelid)
		return 0;

	m_channel_id = channelid;
	m_mgr->addChannel(channelid, this);

	if (!m_frontend)
	{
		/* no frontend, no need to tune (must be a streamed service) */
		return 0;
	}

	m_state = state_tuning;
			/* if tuning fails, shutdown the channel immediately. */
	int res;
	res = m_frontend->get().tune(*feparm);
	m_current_frontend_parameters = feparm;

	if (res)
	{
		m_state = state_release;
		m_stateChanged(this);
		return res;
	}

	return 0;
}

RESULT eDVBChannel::connectStateChange(const Slot1<void,iDVBChannel*> &stateChange, ePtr<eConnection> &connection)
{
	connection = new eConnection((iDVBChannel*)this, m_stateChanged.connect(stateChange));
	return 0;
}

RESULT eDVBChannel::connectEvent(const Slot2<void,iDVBChannel*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iDVBChannel*)this, m_event.connect(event));
	return 0;
}

RESULT eDVBChannel::getState(int &state)
{
	state = m_state;
	return 0;
}

RESULT eDVBChannel::setCIRouting(const eDVBCIRouting &routing)
{
	return -1;
}

void eDVBChannel::SDTready(int result)
{
	ePyObject args = PyTuple_New(2), ret;
	bool ok=false;
	if (!result)
	{
		for (std::vector<ServiceDescriptionSection*>::const_iterator i = m_SDT->getSections().begin(); i != m_SDT->getSections().end(); ++i)
		{
			ok = true;
			PyTuple_SET_ITEM(args, 0, PyInt_FromLong((*i)->getTransportStreamId()));
			PyTuple_SET_ITEM(args, 1, PyInt_FromLong((*i)->getOriginalNetworkId()));
			break;
		}
	}
	if (!ok)
	{
		PyTuple_SET_ITEM(args, 0, Py_None);
		PyTuple_SET_ITEM(args, 1, Py_None);
		Py_INCREF(Py_None);
		Py_INCREF(Py_None);
	}
	ret = PyObject_CallObject(m_tsid_onid_callback, args);
	if (ret)
		Py_DECREF(ret);
	Py_DECREF(args);
	Py_DECREF(m_tsid_onid_callback);
	m_tsid_onid_callback = ePyObject();
	m_tsid_onid_demux = 0;
	m_SDT = 0;
}

int eDVBChannel::reserveDemux()
{
	ePtr<iDVBDemux> dmx;
	if (!getDemux(dmx, 0))
	{
		uint8_t id;
		if (!dmx->getCADemuxID(id))
			return id;
	}
	return -1;
}

RESULT eDVBChannel::requestTsidOnid(ePyObject callback)
{
	if (PyCallable_Check(callback))
	{
		if (!getDemux(m_tsid_onid_demux, 0))
		{
			m_SDT = new eTable<ServiceDescriptionSection>;
			CONNECT(m_SDT->tableReady, eDVBChannel::SDTready);
			if (m_SDT->start(m_tsid_onid_demux, eDVBSDTSpec()))
			{
				m_tsid_onid_demux = 0;
				m_SDT = 0;
			}
			else
			{
				Py_INCREF(callback);
				m_tsid_onid_callback = callback;
				return 0;
			}
		}
	}
	return -1;
}

RESULT eDVBChannel::getDemux(ePtr<iDVBDemux> &demux, int cap)
{
	ePtr<eDVBAllocatedDemux> &our_demux = (cap & capDecode) ? m_decoder_demux : m_demux;

	if (m_frontend == NULL)
	{
		/* in dvr mode, we have to stick to a single demux (the one connected to our dvr device) */
		our_demux = m_decoder_demux ? m_decoder_demux : m_demux;
	}

	if (!our_demux)
	{
		demux = 0;

		if (m_mgr->allocateDemux(m_frontend ? (eDVBRegisteredFrontend*)*m_frontend : (eDVBRegisteredFrontend*)0, our_demux, cap))
			return -1;

		demux = *our_demux;

		/* don't hold a reference to the decoding demux, we don't need it. */

		/* FIXME: by dropping the 'allocated demux' in favour of the 'iDVBDemux',
		   the refcount is lost. thus, decoding demuxes are never allocated.

		   this poses a big problem for PiP. */

		if (cap & capHoldDecodeReference) // this is set in eDVBResourceManager::allocateDemux for Dm500HD/DM800 and DM8000
			;
		else if (cap & capDecode)
			our_demux = 0;
	}
	else
		demux = *our_demux;

	return 0;
}

RESULT eDVBChannel::getFrontend(ePtr<iDVBFrontend> &frontend)
{
	frontend = 0;
	if (!m_frontend)
		return -ENODEV;
	frontend = &m_frontend->get();
	if (frontend)
		return 0;
	return -ENODEV;
}

RESULT eDVBChannel::getCurrentFrontendParameters(ePtr<iDVBFrontendParameters> &param)
{
	param = m_current_frontend_parameters;
	return 0;
}

RESULT eDVBChannel::playFile(const char *file)
{
	eRawFile *f = new eRawFile();
	ePtr<iTsSource> source = f;

	if (f->open(file) < 0)
	{
		eDebug("can't open PVR file %s (%m)", file);
		return -ENOENT;
	}

	return playSource(source, file);
}

RESULT eDVBChannel::playSource(ePtr<iTsSource> &source, const char *streaminfo_file)
{
	ASSERT(!m_frontend);
	if (m_pvr_thread)
	{
		m_pvr_thread->stop();
		delete m_pvr_thread;
		m_pvr_thread = 0;
	}

	if (!source->valid())
	{
		eDebug("PVR source is not valid!");
		return -ENOENT;
	}

	m_source = source;
	m_tstools.setSource(m_source, streaminfo_file);

		/* DON'T EVEN THINK ABOUT FIXING THIS. FIX THE ATI SOURCES FIRST,
		   THEN DO A REAL FIX HERE! */

	if (m_pvr_fd_dst < 0)
	{
		/* (this codepath needs to be improved anyway.) */
#ifdef HAVE_OLDPVR
		m_pvr_fd_dst = open("/dev/misc/pvr", O_WRONLY);
		if (m_pvr_fd_dst < 0)
		{
			eDebug("can't open /dev/misc/pvr - %m"); // or wait for the driver to be improved.
			return -ENODEV;
		}
#else
		ePtr<eDVBAllocatedDemux> &demux = m_demux ? m_demux : m_decoder_demux;
		if (demux)
		{
			m_pvr_fd_dst = demux->get().openDVR(O_WRONLY);
			if (m_pvr_fd_dst < 0)
			{
				eDebug("can't open /dev/dvb/adapterX/dvrX - you need to buy the new(!) $$$ box! (%m)"); // or wait for the driver to be improved.
				return -ENODEV;
			}
		}
		else
		{
			eDebug("no demux allocated yet.. so its not possible to open the dvr device!!");
			return -ENODEV;
		}
#endif
	}

	m_pvr_thread = new eDVBChannelFilePush(m_source->getPacketSize());
	m_pvr_thread->enablePVRCommit(1);
	/* If the source specifies a length, it's a file. If not, it's a stream */
	m_pvr_thread->setStreamMode(m_source->length() <= 0);
	m_pvr_thread->setScatterGather(this);

	m_event(this, evtPreStart);

	m_pvr_thread->start(m_source, m_pvr_fd_dst);
	CONNECT(m_pvr_thread->m_event, eDVBChannel::pvrEvent);

	m_state = state_ok;
	m_stateChanged(this);

	return 0;
}

void eDVBChannel::stopSource()
{
	if (m_pvr_thread)
	{
		m_pvr_thread->stop();
		delete m_pvr_thread;
		m_pvr_thread = 0;
	}
	if (m_pvr_fd_dst >= 0)
	{
		::close(m_pvr_fd_dst);
		m_pvr_fd_dst = -1;
	}
	m_source = NULL;
	m_tstools.setSource(m_source);
}

void eDVBChannel::stopFile()
{
	stopSource();
}

void eDVBChannel::setCueSheet(eCueSheet *cuesheet)
{
	m_conn_cueSheetEvent = 0;
	m_cue = cuesheet;
	if (m_cue)
		m_cue->connectEvent(slot(*this, &eDVBChannel::cueSheetEvent), m_conn_cueSheetEvent);
}

void eDVBChannel::setOfflineDecodeMode(int parityswitchdelay)
{
	if (m_pvr_thread) m_pvr_thread->setParitySwitchDelay(parityswitchdelay);
}

RESULT eDVBChannel::getLength(pts_t &len)
{
	m_tstools_lock.lock();
	RESULT r = m_tstools.calcLen(len);
	m_tstools_lock.unlock();
	return r;
}

RESULT eDVBChannel::getCurrentPosition(iDVBDemux *decoding_demux, pts_t &pos, int mode)
{
	if (!decoding_demux)
		return -1;

	pts_t now;

	int r;

	if (mode == 0) /* demux */
	{
		r = decoding_demux->getSTC(now, 0);
		if (r)
		{
			eDebug("demux getSTC failed");
			return -1;
		}
	} else
		now = pos; /* fixup supplied */

	m_tstools_lock.lock();
	r = m_tstools.fixupPTS(m_source ? m_source->offset() : 0, now);
	m_tstools_lock.unlock();
	if (r)
	{
		return -1;
	}

	pos = now;

	return 0;
}

void eDVBChannel::flushPVR(iDVBDemux *decoding_demux)
{
			/* when seeking, we have to ensure that all buffers are flushed.
			   there are basically 3 buffers:
			   a.) the filepush's internal buffer
			   b.) the PVR buffer (before demux)
			   c.) the ratebuffer (after demux)

			   it's important to clear them in the correct order, otherwise
			   the ratebuffer (for example) would immediately refill from
			   the not-yet-flushed PVR buffer.
			*/

	m_pvr_thread->pause();
		/* flush internal filepush buffer */
	m_pvr_thread->flush();
		/* HACK: flush PVR buffer */
	::ioctl(m_pvr_fd_dst, 0);

		/* flush ratebuffers (video, audio) */
	if (decoding_demux)
		decoding_demux->flush();

		/* demux will also flush all decoder.. */
		/* resume will re-query the SG */
	m_pvr_thread->resume();
}

DEFINE_REF(eCueSheet);

eCueSheet::eCueSheet()
{
	m_skipmode_ratio = 0;
}

void eCueSheet::seekTo(int relative, const pts_t &pts)
{
	m_lock.WrLock();
	m_seek_requests.push_back(std::pair<int, pts_t>(relative, pts));
	m_lock.Unlock();
	m_event(evtSeek);
}

void eCueSheet::clear()
{
	m_lock.WrLock();
	m_spans.clear();
	m_lock.Unlock();
}

void eCueSheet::addSourceSpan(const pts_t &begin, const pts_t &end)
{
	ASSERT(begin < end);
	m_lock.WrLock();
	m_spans.push_back(std::pair<pts_t, pts_t>(begin, end));
	m_lock.Unlock();
}

void eCueSheet::commitSpans()
{
	m_event(evtSpanChanged);
}

void eCueSheet::setSkipmode(const pts_t &ratio)
{
	m_lock.WrLock();
	m_skipmode_ratio = ratio;
	m_lock.Unlock();
	m_event(evtSkipmode);
}

void eCueSheet::setDecodingDemux(iDVBDemux *demux, iTSMPEGDecoder *decoder)
{
	m_decoding_demux = demux;
	m_decoder = decoder;
}

RESULT eCueSheet::connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_event.connect(event));
	return 0;
}
