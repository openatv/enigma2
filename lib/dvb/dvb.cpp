#include <linux/dvb/frontend.h>
#include <linux/dvb/dmx.h>
#include <linux/dvb/version.h>

#include <lib/base/cfile.h>
#include <lib/base/eerror.h>
#include <lib/base/estring.h>
#include <lib/base/esimpleconfig.h>
#include <lib/base/wrappers.h>
#include <lib/dvb/cahandler.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <lib/dvb/fbc.h>
#include <lib/dvb/fcc.h>
#include <lib/dvb/specs.h>
#include "filepush.h"

#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <fstream>

#define MIN(a,b) (a < b ? a : b)
#define MAX(a,b) (a > b ? a : b)

DEFINE_REF(eDVBRegisteredFrontend);
DEFINE_REF(eDVBRegisteredDemux);

DEFINE_REF(eDVBAllocatedFrontend);

void eDVBRegisteredFrontend::closeFrontend()
{
	if (!m_inuse && m_frontend->closeFrontend()) // frontend busy
		disable->start(60000, true);  // retry close in 60secs
}

eDVBAllocatedFrontend::eDVBAllocatedFrontend(eDVBRegisteredFrontend *fe, eFBCTunerManager *fbcmng)
	: m_fe(fe), m_fbcmng(fbcmng)
{
	m_fe->inc_use();
}

eDVBAllocatedFrontend::~eDVBAllocatedFrontend()
{
	m_fe->dec_use();

	if (m_fe->m_frontend->is_FBCTuner() && m_fbcmng)
		m_fbcmng->Unlink(m_fe);
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

	setUsbTuner();

	int fd = open("/proc/stb/info/model", O_RDONLY);
	char tmp[16];
	int rd = fd >= 0 ? read(fd, tmp, sizeof(tmp)) : 0;
	if (fd >= 0)
		close(fd);

	if (!strncmp(tmp, "dm8000\n", rd))
		m_boxtype = DM8000;
	else if (!strncmp(tmp, "dm800\n", rd))
		m_boxtype = DM800;
	else if (!strncmp(tmp, "dm500hd\n", rd))
		m_boxtype = DM500HD;
	else if (!strncmp(tmp, "dm800se\n", rd))
		m_boxtype = DM800SE;
	else if (!strncmp(tmp, "dm7020hd\n", rd))
		m_boxtype = DM7020HD;
	else if (!strncmp(tmp, "dm7080\n", rd))
		m_boxtype = DM7080;
	else if (!strncmp(tmp, "dm820\n", rd))
		m_boxtype = DM820;
	else if (!strncmp(tmp, "dm520\n", rd))
		m_boxtype = DM520;
	else if (!strncmp(tmp, "dm525\n", rd))
		m_boxtype = DM525;
	else if (!strncmp(tmp, "dm900\n", rd))
		m_boxtype = DM900;
	else if (!strncmp(tmp, "dm920\n", rd))
		m_boxtype = DM920;
	else if (!strncmp(tmp, "one\n", rd))
		m_boxtype = DREAMONE;
	else if (!strncmp(tmp, "two\n", rd))
		m_boxtype = DREAMTWO;
	else if (!strncmp(tmp, "seven\n", rd))
		m_boxtype = DREAMSEVEN;
	else if (!strncmp(tmp, "Gigablue\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gb800solo\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gb800se\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gb800ue\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gb800seplus\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gb800ueplus\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbipbox\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbquad\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbquadplus\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbultra\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbultrase\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbultraue\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbultraueh\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbx1\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbx2\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbx3\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbx3h\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbquad4k\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbquad4kpro\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbue4k\n", rd))
		m_boxtype = GIGABLUE;
	else if (!strncmp(tmp, "gbx34k\n", rd))
		m_boxtype = GIGABLUE;
	else {
		eDebug("[eDVBResourceManager] boxtype detection via /proc/stb/info not possible... use fallback via demux count!");
		if (m_demux.size() == 3)
			m_boxtype = DM800;
		else
			m_boxtype = DM8000;
	}

	eDebug("[eDVBResourceManager] found %zd adapter, %zd frontends(%zd sim) and %zd demux, boxtype %d",
		m_adapter.size(), m_frontend.size(), m_simulate_frontend.size(), m_demux.size(), m_boxtype);

	m_fbcmng = new eFBCTunerManager(instance);

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

	eDebug("[eDVBResourceManager] scanning for frontends..");
	while (1)
	{
		/*
		 * Some frontend devices might have been just created, if
		 * they are virtual (vtuner) frontends.
		 * In that case, we cannot be sure the devicenodes are available yet.
		 * So it is safer to scan for sys entries, than for device nodes
		 */
		char filename[128];
		snprintf(filename, sizeof(filename), "/sys/class/dvb/dvb%d.frontend%d", m_nr, num_fe);
		if (::access(filename, X_OK) < 0) break;
		snprintf(filename, sizeof(filename), "/dev/dvb/adapter%d/frontend%d", m_nr, num_fe);
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
		++num_fe; // NOSONAR
	}

		// scan demux
	int num_demux = 0;
	while (1)
	{
		char filename[128];
		sprintf(filename, "/dev/dvb/adapter%d/demux%d", m_nr, num_demux);
		if (::access(filename, R_OK) < 0) break;
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
	eDebug("[eDVBAdapterLinux] get demux %d", nr);

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
	char filename[128];
	sprintf(filename, "/dev/dvb/adapter%d", nr);
	return (::access(filename, X_OK) >= 0) ? 1 : 0;
}

bool eDVBAdapterLinux::isusb(int nr)
{
	char devicename[256];
	snprintf(devicename, sizeof(devicename), "/sys/class/dvb/dvb%d.frontend0/device/ep_00", nr);
	if (::access(devicename, X_OK) >= 0)
	{
		return true;
	}
	snprintf(devicename, sizeof(devicename), "/sys/class/dvb/dvb%d.frontend0/device/subsystem", nr);
	return readLink(devicename).find("/usb") != std::string::npos;
}

DEFINE_REF(eDVBUsbAdapter);
eDVBUsbAdapter::eDVBUsbAdapter(int nr)
: eDVBAdapterLinux(nr)
{
	int file;
	char type[8] = {};
	struct dvb_frontend_info fe_info = {};
	int frontend = -1;
	char filename[256] = {};
	char name[128] = {0};
	int vtunerid = nr - 1;
	char buffer[4*1024];
	char* buf_pos;
	ssize_t rd;
	int fd;

	pumpThread = 0;

	int num_fe = 0;

	demuxFd = vtunerFd = pipeFd[0] = pipeFd[1] = -1;

	/* we need to know exactly what frontend is internal or initialized! */
	fd = open("/proc/bus/nim_sockets", O_RDONLY);
	if (fd < 0)
	{
		eDebug("[eDVBUsbAdapter] Cannot open /proc/bus/nim_sockets");
		goto error;
	}
	rd = read(fd, buffer, sizeof(buffer));
	if (rd < 0)
	{
		eDebug("[eDVBUsbAdapter] Cannot read /proc/bus/nim_sockets");
		goto error;
	}
	buf_pos = buffer;
	while ((buf_pos = strstr(buf_pos, "Frontend_Device: ")) != NULL)
	{
		int num_fe_tmp;
		if (sscanf(buf_pos, "Frontend_Device: %d", &num_fe_tmp) == 1)
		{
			if (num_fe_tmp > num_fe)
				num_fe = num_fe_tmp;
		}
		buf_pos += 1;
	}
	num_fe++;
	snprintf(filename, sizeof(filename), "/dev/dvb/adapter0/frontend%d", num_fe);
	virtualFrontendName = filename;

	/* find the device name */
	snprintf(filename, sizeof(filename), "/sys/class/dvb/dvb%d.frontend0/device/product", nr);
	file = ::open(filename, O_RDONLY);
	if (file < 0)
	{
		snprintf(filename, sizeof(filename), "/sys/class/dvb/dvb%d.frontend0/device/manufacturer", nr);
		file = ::open(filename, O_RDONLY);
	}

	if (file >= 0)
	{
		int len = singleRead(file, name, sizeof(name) - 1);
		if (len >= 0)
		{
			name[len] = 0;
		}
		::close(file);
		file = -1;
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

	if (!name[0])
	{
		/* fallback to the dvb_frontend_info name */
		int len = MIN(sizeof(fe_info.name), sizeof(name) - 1);
		strncpy(name, fe_info.name, len);
		name[len] = 0;
	}
	if (name[0])
	{
		/* strip trailing LF / CR / whitespace */
		int len = strlen(name);
		char *tmp = name;
		while (len && (strchr(" \n\r\t", tmp[len - 1]) != NULL))
		{
			tmp[--len] = 0;
		}
	}
	if (!name[0])
	{
		/* we did not find a usable name, fallback to a default */
		snprintf(name, sizeof(name), "usb frontend");
	}

	snprintf(filename, sizeof(filename), "/dev/dvb/adapter%d/demux0", nr);
	demuxFd = open(filename, O_RDONLY | O_NONBLOCK | O_CLOEXEC);
	if (demuxFd < 0)
	{
		goto error;
	}

	while (vtunerFd < 0)
	{
		snprintf(filename, sizeof(filename), "/dev/misc/vtuner%d", vtunerid);
		if (::access(filename, F_OK) < 0)
		{
			eDebug("[eDVBUsbAdapter] '%s' not found", filename);
			snprintf(filename, sizeof(filename), "/dev/vtuner%d", vtunerid);
			if (::access(filename, F_OK) < 0)
			{
				eDebug("[eDVBUsbAdapter] '%s' not found -> stop here!", filename);
				break;
			}
		}
		vtunerFd = open(filename, O_RDWR | O_CLOEXEC);
		if (vtunerFd < 0)
		{
			vtunerid++;
		}
	}

	if (vtunerFd < 0)
	{
		goto error;
	}

	eDebug("[eDVBUsbAdapter] linking adapter%d/frontend0 to vtuner%d", nr, vtunerid);

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
		eDebug("[eDVBUsbAdapter] Frontend type 0x%x not supported", fe_info.type);
		goto error;
	}

#ifdef VMSG_TYPE2
#define VTUNER_GET_MESSAGE  11
#define VTUNER_SET_RESPONSE 12
#define VTUNER_SET_NAME     13
#define VTUNER_SET_TYPE     14
#define VTUNER_SET_HAS_OUTPUTS 15
#define VTUNER_SET_FE_INFO  16
#define VTUNER_SET_NUM_MODES 17
#define VTUNER_SET_MODES 18
#else
#define VTUNER_GET_MESSAGE  1
#define VTUNER_SET_RESPONSE 2
#define VTUNER_SET_NAME     3
#define VTUNER_SET_TYPE     4
#define VTUNER_SET_HAS_OUTPUTS 5
#define VTUNER_SET_FE_INFO  6
#define VTUNER_SET_NUM_MODES 7
#define VTUNER_SET_MODES 8
#endif
#define VTUNER_SET_DELSYS 32
#define VTUNER_SET_ADAPTER 33
	ioctl(vtunerFd, VTUNER_SET_NAME, name);
	ioctl(vtunerFd, VTUNER_SET_TYPE, type);
	ioctl(vtunerFd, VTUNER_SET_HAS_OUTPUTS, "no");
	ioctl(vtunerFd, VTUNER_SET_ADAPTER, nr);

	memset(pidList, 0xff, sizeof(pidList));

	mappedFrontendName[virtualFrontendName] = usbFrontendName;
	if (pipe(pipeFd) == -1)
	{
		eDebug("[eDVBUsbAdapter] failed to create pipe (%m)");
	}
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

void *eDVBUsbAdapter::threadproc(void *arg)
{
	eDVBUsbAdapter *user = (eDVBUsbAdapter*)arg;
	return user->vtunerPump();
}

static bool exist_in_pidlist(unsigned short int* pidlist, unsigned short int value)
{
	for (int i=0; i<30; ++i)
		if (pidlist[i] == value)
			return true;
	return false;
}

void *eDVBUsbAdapter::vtunerPump()
{
	int pidcount = 0;
	if (vtunerFd < 0 || demuxFd < 0 || pipeFd[0] < 0) return NULL;

#define MSG_PIDLIST         14
	struct vtuner_message
	{
		int type;
		unsigned short int pidlist[30];
		unsigned char pad[64]; /* nobody knows the much data the driver will try to copy into our struct, add some padding to be sure */
	};

#define DEMUX_BUFFER_SIZE (16 * 1024 * 188 ) /* 3 MB */
	ioctl(demuxFd, DMX_SET_BUFFER_SIZE, DEMUX_BUFFER_SIZE);

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
		if (Select(maxfd + 1, &rset, NULL, &xset, NULL) > 0)
		{
			if (FD_ISSET(vtunerFd, &xset))
			{
				struct vtuner_message message = {};
				memset(message.pidlist, 0xff, sizeof(message.pidlist));
				::ioctl(vtunerFd, VTUNER_GET_MESSAGE, &message);

				switch (message.type)
				{
				case MSG_PIDLIST:
					/* remove old pids */
					for (int i = 0; i < 30; i++)
					{
						if (pidList[i] == 0xffff)
							continue;
						if (exist_in_pidlist(message.pidlist, pidList[i]))
							continue;

						if (pidcount > 1)
						{
							//eDebug("[adenin]rmove PID %d(0x%04x)", pidList[i], pidList[i]);
							::ioctl(demuxFd, DMX_REMOVE_PID, &pidList[i]);
							pidcount--;
						}
						else if (pidcount == 1)
						{
							::ioctl(demuxFd, DMX_STOP);
							pidcount = 0;
						}
					}

					/* add new pids */
					for (int i = 0; i < 30; i++)
					{
						if (message.pidlist[i] == 0xffff)
							continue;
						if (exist_in_pidlist(pidList, message.pidlist[i]))
							continue;

						if (pidcount)
						{
							//eDebug("[adenin]add PID %d(0x%04x)", message.pidlist[i], message.pidlist[i]);
							::ioctl(demuxFd, DMX_ADD_PID, &message.pidlist[i]);
							pidcount++;
						}
						else
						{
							struct dmx_pes_filter_params filter = {};
							filter.input = DMX_IN_FRONTEND;
							filter.flags = 0;
							filter.pid = message.pidlist[i];
							filter.output = DMX_OUT_TSDEMUX_TAP;
							filter.pes_type = DMX_PES_OTHER;
							if (ioctl(demuxFd, DMX_SET_PES_FILTER, &filter) >= 0
									&& ioctl(demuxFd, DMX_START) >= 0)
							{
								pidcount = 1;
							}
						}
					}

					/* copy pids */
					memcpy(pidList, message.pidlist, sizeof(message.pidlist));

					break;
				}
			}
			if (FD_ISSET(demuxFd, &rset))
			{
				ssize_t size = singleRead(demuxFd, buffer, sizeof(buffer));

				if(size < 188)
					continue;

				if (size > 0 && writeAll(vtunerFd, buffer, size) <= 0)
				{
					break;
				}
			}
		}
	}
	return NULL;
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
			eDVBRegisteredFrontend *new_fe = new eDVBRegisteredFrontend(frontend, adapter);
			CONNECT(new_fe->stateChanged, eDVBResourceManager::feStateChanged);
			m_frontend.push_back(new_fe);
			frontend->setSEC(m_sec);
			// we must link all dvb-t frontends ( for active antenna voltage )
			if (frontend->supportsDeliverySystem(SYS_DVBT, false) || frontend->supportsDeliverySystem(SYS_DVBT2, false))
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
			eDVBRegisteredFrontend *new_fe = new eDVBRegisteredFrontend(frontend, adapter);
//			CONNECT(new_fe->stateChanged, eDVBResourceManager::feStateChanged);
			m_simulate_frontend.push_back(new_fe);
			frontend->setSEC(m_sec);
			// we must link all dvb-t frontends ( for active antenna voltage )
			if (frontend->supportsDeliverySystem(SYS_DVBT, false) || frontend->supportsDeliverySystem(SYS_DVBT2, false))
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

void eDVBResourceManager::setUsbTuner()
{
	std::ifstream in("/proc/bus/nim_sockets");
	std::string line;

	int res = -1;
	int fe_idx = -1;
	int usbtuner_idx[8] = {0};
	int usbtuner_count = 0;

	if (in.is_open())
	{
		while(!in.eof())
		{
			getline(in, line);
			if ((res = sscanf(line.c_str(), "NIM Socket %d:", &fe_idx)) == 1)
				continue;

			if ((fe_idx != -1) && (line.find("\tName: ") == 0) && (line.find("VTUNER") != std::string::npos))
				usbtuner_idx[usbtuner_count++] = fe_idx;
		}
		in.close();
	}

	if (usbtuner_count)
	{
		for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_frontend.begin()); it != m_frontend.end(); ++it)
		{
			int slotid = it->m_frontend->getSlotID();
			for (int i=0; i < usbtuner_count ; i++)
			{
				if (slotid == usbtuner_idx[i])
				{
					it->m_frontend->setUSBTuner(true);
					break;
				}
			}
		}
		for (eSmartPtrList<eDVBRegisteredFrontend>::iterator it(m_simulate_frontend.begin()); it != m_simulate_frontend.end(); ++it)
		{
			int slotid = it->m_frontend->getSlotID();
			for (int i=0; i < usbtuner_count ; i++)
			{
				if (slotid == usbtuner_idx[i])
				{
					it->m_frontend->setUSBTuner(true);
					break;
				}
			}
		}
	}
}

PyObject *eDVBResourceManager::setFrontendSlotInformations(ePyObject list)
{
	if (!PyList_Check(list))
	{
		PyErr_SetString(PyExc_TypeError, "eDVBResourceManager::setFrontendSlotInformations argument should be a python list");
		return NULL;
	}
	unsigned int assigned=0;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
	{
		int pos=0;
		while (pos < PyList_Size(list)) {
			ePyObject obj = PyList_GET_ITEM(list, pos++);
			ePyObject Id, Descr, Enabled, IsDVBS2, frontendId;
			if (!PyTuple_Check(obj) || PyTuple_Size(obj) != 5)
				continue;
			Id = PyTuple_GET_ITEM(obj, 0);
			Descr = PyTuple_GET_ITEM(obj, 1);
			Enabled = PyTuple_GET_ITEM(obj, 2);
			IsDVBS2 = PyTuple_GET_ITEM(obj, 3);
			frontendId = PyTuple_GET_ITEM(obj, 4);
			if (!PyLong_Check(Id) || !PyUnicode_Check(Descr) || !PyBool_Check(Enabled) || !PyBool_Check(IsDVBS2) || !PyLong_Check(frontendId))
				continue;
			if (!i->m_frontend->setSlotInfo(PyLong_AsLong(Id), PyUnicode_AsUTF8(Descr), Enabled == Py_True, IsDVBS2 == Py_True, PyLong_AsLong(frontendId)))
				continue;
			++assigned;
			break;
		}
	}
	if (assigned != m_frontend.size()) {
		eDebug("[eDVBResourceManager::setFrontendSlotInformations] .. assigned %zd socket informations, but %d registered frontends!",
			m_frontend.size(), assigned);
	}
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_simulate_frontend.begin()); i != m_simulate_frontend.end(); ++i)
	{
		int pos=0;
		while (pos < PyList_Size(list)) {
			ePyObject obj = PyList_GET_ITEM(list, pos++);
			ePyObject Id, Descr, Enabled, IsDVBS2, frontendId;
			if (!PyTuple_Check(obj) || PyTuple_Size(obj) != 5)
				continue;
			Id = PyTuple_GET_ITEM(obj, 0);
			Descr = PyTuple_GET_ITEM(obj, 1);
			Enabled = PyTuple_GET_ITEM(obj, 2);
			IsDVBS2 = PyTuple_GET_ITEM(obj, 3);
			frontendId = PyTuple_GET_ITEM(obj, 4);
			if (!PyLong_Check(Id) || !PyUnicode_Check(Descr) || !PyBool_Check(Enabled) || !PyBool_Check(IsDVBS2) || !PyLong_Check(frontendId))
				continue;
			if (!i->m_frontend->setSlotInfo(PyLong_AsLong(Id), PyUnicode_AsUTF8(Descr), Enabled == Py_True, IsDVBS2 == Py_True, PyLong_AsLong(frontendId)))
				continue;
			break;
		}
	}
	Py_RETURN_NONE;
}

bool eDVBResourceManager::frontendIsCompatible(int index, const char *type)
{
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
	{
		if (i->m_frontend->getSlotID() == index)
		{
			if (!strcmp(type, "DVB-S2"))
			{
				return i->m_frontend->supportsDeliverySystem(SYS_DVBS2, false);
			}
			else if (!strcmp(type, "DVB-S"))
			{
				return i->m_frontend->supportsDeliverySystem(SYS_DVBS, false);
			}
			else if (!strcmp(type, "DVB-T2"))
			{
				return i->m_frontend->supportsDeliverySystem(SYS_DVBT2, false);
			}
			else if (!strcmp(type, "DVB-T"))
			{
				return i->m_frontend->supportsDeliverySystem(SYS_DVBT, false);
			}
			else if (!strcmp(type, "DVB-C"))
			{
#if defined SYS_DVBC_ANNEX_A
				return i->m_frontend->supportsDeliverySystem(SYS_DVBC_ANNEX_A, false) || i->m_frontend->supportsDeliverySystem(SYS_DVBC_ANNEX_C, false);
#else
				return i->m_frontend->supportsDeliverySystem(SYS_DVBC_ANNEX_AC, false);
#endif
			}
			else if (!strcmp(type, "ATSC"))
			{
				return i->m_frontend->supportsDeliverySystem(SYS_ATSC, false) || i->m_frontend->supportsDeliverySystem(SYS_DVBC_ANNEX_B, false);
			}
			break;
		}
	}
	return false;
}

int eDVBResourceManager::getFrontendType(int index)
{
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
	{
		if (i->m_frontend->getSlotID() == index)
			return i->m_frontend->getCurrentType();
	}
	return -1;
}

bool eDVBResourceManager::frontendIsMultistream(int index)
{
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
	{
		if (i->m_frontend->getSlotID() == index)
		{
			return i->m_frontend->is_multistream();
		}
	}
	return false;
}

std::string eDVBResourceManager::getFrontendCapabilities(int index)
{
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
	{
		if (i->m_frontend->getSlotID() == index)
		{
			return i->m_frontend->getCapabilities();
		}
	}
	return "";
}

void eDVBResourceManager::setFrontendType(int index, const char *type, bool append)
{
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
	{
		if (i->m_frontend->getSlotID() == index)
		{
			std::vector<fe_delivery_system_t> whitelist;
			if (!strcmp(type, "DVB-S2") || !strcmp(type, "DVB-S"))
			{
				whitelist.push_back(SYS_DVBS);
				whitelist.push_back(SYS_DVBS2);
			}
			else if (!strcmp(type, "DVB-T2") || !strcmp(type, "DVB-T"))
			{
				whitelist.push_back(SYS_DVBT);
				whitelist.push_back(SYS_DVBT2);
			}
			else if (!strcmp(type, "DVB-C"))
			{
#if defined SYS_DVBC_ANNEX_A
				whitelist.push_back(SYS_DVBC_ANNEX_A);
				whitelist.push_back(SYS_DVBC_ANNEX_C);
#else
				whitelist.push_back(SYS_DVBC_ANNEX_AC);
#endif
			}
			else if (!strcmp(type, "ATSC"))
			{
				whitelist.push_back(SYS_ATSC);
				whitelist.push_back(SYS_DVBC_ANNEX_B);
			}
			i->m_frontend->setDeliverySystemWhitelist(whitelist, append);
			break;
		}
	}
}

RESULT eDVBResourceManager::allocateFrontend(ePtr<eDVBAllocatedFrontend> &fe, ePtr<iDVBFrontendParameters> &feparm, bool simulate, bool returnScoreOnly)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_simulate_frontend : m_frontend;
	eDVBRegisteredFrontend *best, *fbc_fe, *best_fbc_fe;
	int bestval, foundone, current_fbc_setid, c;
	bool check_fbc_leaf_linkable;
	[[maybe_unused]] bool is_configured_sat;
	[[maybe_unused]] long link;

	fbc_fe  = NULL;
	best_fbc_fe = NULL;
	best = NULL;
	bestval = 0;
	foundone = 0;
	check_fbc_leaf_linkable = false;
	current_fbc_setid = -1;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(frontends.begin()); i != frontends.end(); ++i)
	{
		c = 0;
		is_configured_sat = false;
		fbc_fe = NULL;
		if (i->m_frontend->is_FBCTuner() && m_fbcmng->CanLink(*i))
		{
			int fbc_setid = m_fbcmng->GetFBCSetID(i->m_frontend->getSlotID());

			if (fbc_setid != current_fbc_setid)
			{
				current_fbc_setid = fbc_setid;
				check_fbc_leaf_linkable = false;
			}

			if (!check_fbc_leaf_linkable)
			{
				c = m_fbcmng->IsCompatibleWith(feparm, *i, fbc_fe, simulate);
				check_fbc_leaf_linkable = true;
				//eDebug("[eDVBResourceManager::allocateFrontend] m_fbcmng->isCompatibleWith slotid : %p (%d), fbc_fe : %p (%d), score : %d", (eDVBRegisteredFrontend *)*i, i->m_frontend->ge);
			}
		}
		else
		{
			c = i->m_frontend->isCompatibleWith(feparm);
		}

		if (c)	/* if we have at least one frontend which is compatible with the source, flag this. */
			foundone = 1;

		if (!i->m_inuse)
		{
//			eDebug("[eDVBResourceManager::allocateFrontend] Slot %d, score %d", i->m_frontend->getSlotID(), c);
			if (c > bestval)
			{
				bestval = c;
//				best = i;
				best = *i;
				best_fbc_fe = fbc_fe;
			}
		}
		else
		{
//			eDebug("[eDVBResourceManager::allocateFrontend] Slot %d, score %d... but BUSY!!!!!!!!!!!", i->m_frontend->getSlotID(), c);
		}

		//eDVBRegisteredFrontend *tmp = *i;
	}

	if (returnScoreOnly)
	{
		return bestval;
	}
	
	if (best)
	{
		if (best_fbc_fe)
			m_fbcmng->AddLink(best, best_fbc_fe, simulate);

		fe = new eDVBAllocatedFrontend(best, m_fbcmng);
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
					eDebug("[eDVBResourceManager] another satpos depending frontend is in use.. so allocateFrontendByIndex not possible!");
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
						eDebug("[eDVBResourceManager] another linked frontend is in use.. so allocateFrontendByIndex not possible!");
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
						eDebug("[eDVBResourceManager] another linked frontend is in use.. so allocateFrontendByIndex not possible!");
						err = errAllSourcesBusy;
						goto alloc_fe_by_id_not_possible;
					}
					prev->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, tmp);
				}
			}
			fe = new eDVBAllocatedFrontend(i, m_fbcmng);
			return 0;
		}
alloc_fe_by_id_not_possible:
	fe = 0;
	return err;
}

RESULT eDVBResourceManager::allocateDemux(eDVBRegisteredFrontend *fe, ePtr<eDVBAllocatedDemux> &demux, int &cap)
{
	/* find first unused demux which is on same adapter as frontend (or any, if PVR)
		never use the first one unless we need a decoding demux. */

	eDebug("[eDVBResourceManager] allocate demux cap=%02X", cap);
	eSmartPtrList<eDVBRegisteredDemux>::iterator i(m_demux.begin());

	if (i == m_demux.end())
		return -1;


	iDVBAdapter *adapter = fe ? fe->m_adapter : m_adapter.begin(); /* look for a demux on the same adapter as the frontend, or the first adapter for dvr playback */
	int fesource = fe ? fe->m_frontend->getDVBID() : -1;
	ePtr<eDVBRegisteredDemux> unused;
	uint8_t d, a;

	/*
	 * For pvr playback, start with the last demux.
	 * On some hardware, there are less ca devices than demuxes, so try to leave
	 * the first demuxes for live tv, and start with the last for pvr playback
	 */

	bool use_decode_demux = (fe || (cap & iDVBChannel::capDecode));

	if (!use_decode_demux)
	{
		i = m_demux.end();
		--i;
	}

	while (i != m_demux.end())
	{
		if (i->m_adapter == adapter)
		{
			if (!i->m_inuse)
			{
				// mark the first unused demux and use that when no better match is found
				if (!unused)
					unused = i;
			}
			else
			{
				// demux is in use, see if it can be shared
				if (fesource >= 0 && i->m_demux->getSource() == fesource)
				{
					i->m_demux->getCAAdapterID(a);
					i->m_demux->getCADemuxID(d);
					eDebug("[eDVBResourceManager] allocating shared demux adapter=%d, demux=%d, source=%d", a, d, i->m_demux->getSource());
					demux = new eDVBAllocatedDemux(i);
					return 0;
				}
			}
		}
		if (use_decode_demux)
		{
			++i;
		}
		else
		{
			if (i == m_demux.begin())
				break;
			--i;
		}
	}

	if (unused)
	{
		unused->m_demux->getCAAdapterID(a);
		unused->m_demux->getCADemuxID(d);
		eDebug("[eDVBResourceManager] allocating demux adapter=%d, demux=%d, source=%d fesource=%d", a, d, unused->m_demux->getSource(), fesource);
		demux = new eDVBAllocatedDemux(unused);
		if (fe)
			demux->get().setSourceFrontend(fesource);
		else
			demux->get().setSourcePVR(0);
		return 0;
	}

	eDebug("[eDVBResourceManager] no free demux found");
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

RESULT eDVBResourceManager::getActiveChannels(std::list<active_channel> &list)
{
	list = m_active_channels;
	return 0;
}

#define eDebugNoSimulate(x...) \
	do { \
		if (!simulate) \
			eDebug(x); \
	} while(0)

bool eDVBResourceManager::frontendPreferenceAllowsChannelUse(const eDVBChannelID &channelid, eUsePtr<iDVBChannel> channel, bool simulate)
{
	ePtr<iDVBFrontend> fe;
	channel->getFrontend(fe);
	int slotid = fe->readFrontendData(iFrontendInformation_ENUMS::frontendNumber);
	
	int preferredFrontend = eDVBFrontend::getPreferredFrontend();
	if (preferredFrontend < 0)
	{
		//eDebug("frontend %d allowed, no frontend preference", slotid);      
		return true; /* no frontend preference */
	}
    
	if (!((preferredFrontend >= 0) && (preferredFrontend & eDVBFrontend::preferredFrontendPrioForced)) && !((preferredFrontend >= 0) && (preferredFrontend & eDVBFrontend::preferredFrontendPrioHigh)))
	{
		//eDebug("frontend %d allowed, sharing/caching channels is allowed for any frontend", slotid);      
		return true; /* sharing/caching channels is allowed for any frontend */
	}

	if (eDVBFrontend::isPreferred(preferredFrontend,slotid))
	{
		//eDebug("frontend %d allowed, preferred frontend", slotid);      
		return true; /* preferred frontend */
	}

	if (!m_list)
	{
		//eDebug("frontend %d allowed, no channel list set", slotid);      
		return true; /* no channel list set */
	}

	ePtr<iDVBFrontendParameters> feparm;
	if (m_list->getChannelFrontendData(channelid, feparm))
	{
		//eDebug("frontend %d allowed, channel not found", slotid);      
		return true; /* channel not found */
	}

	ePtr<eDVBAllocatedFrontend> dummy_fe;
	int score = allocateFrontend(dummy_fe, feparm, simulate, /*returnScoreOnly=*/true);
	//eDebug("frontend %d score %d", slotid, score);      
	if (score < eDVBFrontend::preferredFrontendScore)
	{
		if ((preferredFrontend >= 0) && (preferredFrontend & eDVBFrontend::preferredFrontendPrioForced))
		{
			//eDebug("frontend %d forbidden, no preferred frontend available, no sharing allowed", slotid);      
			return false; /* no preferred frontend available, no sharing allowed */
		}
		else
		{
			//eDebug("frontend %d allowed, no new preferred frontend available, use shared or cached channel", slotid);      
			return true; /* no new preferred frontend available, use shared or cached channel */
		}
	}
	else
	{
		//eDebug("frontend %d forbidden, a new preferred frontend is available, dont use shared or cached channel", slotid);      
		return false;
	}
}

RESULT eDVBResourceManager::allocateChannel(const eDVBChannelID &channelid, eUsePtr<iDVBChannel> &channel, bool simulate)
{
		/* first, check if a channel is already existing. */
	std::list<active_channel> &active_channels = simulate ? m_active_simulate_channels : m_active_channels;

	if (!simulate && m_cached_channel)
	{
		eDVBChannel *cache_chan = (eDVBChannel*)&(*m_cached_channel);
		if(channelid==cache_chan->getChannelID())
		{
			ePtr<iDVBFrontend> fe;
			m_cached_channel->getFrontend(fe);
			int slotid = fe->readFrontendData(iFrontendInformation_ENUMS::frontendNumber);
			if (frontendPreferenceAllowsChannelUse(channelid,m_cached_channel,simulate))
			{
				eDebug("[eDVBResourceManager] use cached_channel, frontend=%d",slotid);
				channel = m_cached_channel;
				return 0;
			}
			else
			{
				eDebug("[eDVBResourceManager] strict frontend preference policy, don't use cached_channel, frontend=%d",slotid);
			}
		}
		m_cached_channel_state_changed_conn.disconnect();
		m_cached_channel=0;
		m_releaseCachedChannelTimer->stop();
	}

	eDebugNoSimulate("[eDVBResourceManager] allocate channel.. %04x:%04x", channelid.transport_stream_id.get(), channelid.original_network_id.get());
	for (std::list<active_channel>::iterator i(active_channels.begin()); i != active_channels.end(); ++i)
	{
		eDebugNoSimulate("[eDVBResourceManager] available channel.. %04x:%04x", i->m_channel_id.transport_stream_id.get(), i->m_channel_id.original_network_id.get());
		if (i->m_channel_id == channelid)
		{
			ePtr<iDVBFrontend> fe;
			if (!i->m_channel->getFrontend(fe))
			{
				int slotid = fe->readFrontendData(iFrontendInformation_ENUMS::frontendNumber);
				if (frontendPreferenceAllowsChannelUse(channelid,i->m_channel,simulate))
				{
					eDebugNoSimulate("[eDVBResourceManager] found shared channel.. i=%ld, frontend=%d (preferred=%d)",std::distance(active_channels.begin(), i),slotid,eDVBFrontend::getPreferredFrontend());
					channel = i->m_channel;
					return 0;
				}
				else
				{
					eDebugNoSimulate("[eDVBResourceManager] strict frontend preference policy, don't use shared channel.. i=%ld, frontend=%d (preferred=%d)",std::distance(active_channels.begin(), i),slotid,eDVBFrontend::getPreferredFrontend());
				}
			}
		}
	}

	/* no currently available channel is tuned to this channelid. create a new one, if possible. */

	if (!m_list)
	{
		eDebugNoSimulate("[eDVBResourceManager] no channel list set!");
		return errNoChannelList;
	}

	ePtr<iDVBFrontendParameters> feparm;
	if (m_list->getChannelFrontendData(channelid, feparm))
	{
		eDebugNoSimulate("[eDVBResourceManager] channel not found!");
		return errChannelNotInList;
	}

	/* allocate a frontend. */

	ePtr<eDVBAllocatedFrontend> fe;

	int err = allocateFrontend(fe, feparm, simulate);
	if (err)
	{
		eDebugNoSimulate("[eDVBResourceManager] can't allocate frontend!");
		return err;
	}
	RESULT res;
	ePtr<eDVBChannel> ch = new eDVBChannel(this, fe);

	res = ch->setChannel(channelid, feparm);
	if (res)
	{
		channel = 0;
		eDebugNoSimulate("[eDVBResourceManager] channel id not found!");
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
			eDebug("[eDVBResourceManager] stop release channel timer");
			m_releaseCachedChannelTimer->stop();
			break;
		}
		case iDVBChannel::state_last_instance:
		{
			eDebug("[eDVBResourceManager] start release channel timer");
			m_releaseCachedChannelTimer->start(3000, true);
			break;
		}
		default: // ignore all other events
			break;
	}
}

void eDVBResourceManager::releaseCachedChannel()
{
	eDebug("[eDVBResourceManager] release cached channel (timer timeout)");
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
		if (m_list) m_list->getChannelFrontendData(channelid, feparm);
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

RESULT eDVBResourceManager::connectChannelAdded(const sigc::slot<void(eDVBChannel*)> &channelAdded, ePtr<eConnection> &connection)
{
	connection = new eConnection((eDVBResourceManager*)this, m_channelAdded.connect(channelAdded));
	return 0;
}

int eDVBResourceManager::canAllocateFrontend(ePtr<iDVBFrontendParameters> &feparm, bool simulate)
{
	eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_simulate_frontend : m_frontend;
	ePtr<eDVBRegisteredFrontend> best;
	int bestval, current_fbc_setid, c;
	bool check_fbc_leaf_linkable;

	bestval = 0;
	check_fbc_leaf_linkable = false;
	current_fbc_setid = -1;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(frontends.begin()); i != frontends.end(); ++i)
	{
		if (!i->m_inuse)
		{
			c = 0;
			if(i->m_frontend->is_FBCTuner() && m_fbcmng->CanLink(*i))
			{
				int fbc_setid = m_fbcmng->GetFBCSetID(i->m_frontend->getSlotID());

				if (fbc_setid != current_fbc_setid)
				{
					current_fbc_setid = fbc_setid;
					check_fbc_leaf_linkable = false;
				}

				if (!check_fbc_leaf_linkable)
				{
					eDVBRegisteredFrontend *dummy;
					c = m_fbcmng->IsCompatibleWith(feparm, *i, dummy, simulate);
					check_fbc_leaf_linkable = true;
				}
			}
			else
				c = i->m_frontend->isCompatibleWith(feparm);

			if (c > bestval)
				bestval = c;
		}
	}
	return bestval;
}

int tuner_type_channel_default(ePtr<iDVBChannelList> &channellist, const eDVBChannelID &chid, int &system)
{
	system = iDVBFrontend::feSatellite;
	if (channellist)
	{
		ePtr<iDVBFrontendParameters> feparm;
		if (!channellist->getChannelFrontendData(chid, feparm))
		{
			if (!feparm->getSystem(system))
			{
				switch (system)
				{
					case iDVBFrontend::feSatellite:
						return 50000;
					case iDVBFrontend::feCable:
						return 40000;
					case iDVBFrontend::feTerrestrial:
						return 30000;
					case iDVBFrontend::feATSC:
						return 20000;
					default:
						break;
				}
			}
		}
	}
	return 0;
}

int eDVBResourceManager::canAllocateChannel(const eDVBChannelID &channelid, const eDVBChannelID& ignore, int &system, bool simulate)
{
	std::list<active_channel> &active_channels = simulate ? m_active_simulate_channels : m_active_channels;
	int ret = 0;
	system = iDVBFrontend::feSatellite;
	if (!simulate && m_cached_channel)
	{
		eDVBChannel *cache_chan = (eDVBChannel*)&(*m_cached_channel);
		if(channelid==cache_chan->getChannelID())
			return tuner_type_channel_default(m_list, channelid, system);
	}

		/* first, check if a channel is already existing. */
//	eDebug("[eDVBResourceManager] allocate channel.. %04x:%04x", channelid.transport_stream_id.get(), channelid.original_network_id.get());
	for (std::list<active_channel>::iterator i(active_channels.begin()); i != active_channels.end(); ++i)
	{
//		eDebug("[eDVBResourceManager] available channel.. %04x:%04x", i->m_channel_id.transport_stream_id.get(), i->m_channel_id.original_network_id.get());
		if (i->m_channel_id == channelid)
		{
//			eDebug("[eDVBResourceManager] found shared channel..");
			return tuner_type_channel_default(m_list, channelid, system);
		}
	}

	int *decremented_cached_channel_fe_usecount=NULL,
		*decremented_fe_usecount=NULL;

	/* check FCC channels */
	std::vector<int*> fcc_decremented_fe_usecounts;
	std::map<eDVBChannelID, int> fcc_chids;
	int apply_to_ignore = 0;
	if (!eFCCServiceManager::getFCCChannelID(fcc_chids))
	{
		for (std::map<eDVBChannelID, int>::iterator i(fcc_chids.begin()); i != fcc_chids.end(); ++i)
		{
			//eDebug("[eDVBResourceManager::canAllocateChannel] FCC NS : %08x, TSID : %04x, ONID : %04x", i->first.dvbnamespace.get(), i->first.transport_stream_id.get(), i->first.original_network_id.get());
			if (ignore == i->first)
			{
				apply_to_ignore = i->second;
				continue;
			}
			for (std::list<active_channel>::iterator ii(active_channels.begin()); ii != active_channels.end(); ++ii)
			{
				eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_simulate_frontend : m_frontend;
				if (ii->m_channel_id == i->first)
				{
					eDVBChannel *channel = (eDVBChannel*) &(*ii->m_channel);

					int check_usecount = channel == &(*m_cached_channel) ? 1 : 0;
					check_usecount += i->second * 2; // one is used in eDVBServicePMTHandler and another is used in eDVBScan.
					//eDebug("[eDVBResourceManager::canAllocateChannel] channel->getUseCount() : %d , check_usecount : %d (cached : %d)", channel->getUseCount(), check_usecount, channel == &(*m_cached_channel));
					if (channel->getUseCount() == check_usecount)
					{
						ePtr<iDVBFrontend> fe;
						if (!ii->m_channel->getFrontend(fe))
						{
							for (eSmartPtrList<eDVBRegisteredFrontend>::iterator iii(frontends.begin()); iii != frontends.end(); ++iii)
							{
								if ( &(*fe) == &(*iii->m_frontend) )
								{
									//eDebug("[eDVBResourceManager::canAllocateChannel] fcc : decrease fcc fe use_count! feid : %d (%d -> %d)", iii->m_frontend->getSlotID(), iii->m_inuse, iii->m_inuse-1);
									--iii->m_inuse;
									int *tmp_decremented_fe_usecount = &iii->m_inuse;
									fcc_decremented_fe_usecounts.push_back(tmp_decremented_fe_usecount);
									if (channel == &(*m_cached_channel))
										decremented_cached_channel_fe_usecount = tmp_decremented_fe_usecount;
									break;
								}
							}
						}
					}
					break;
				}
			}
		}
	}

	for (std::list<active_channel>::iterator i(active_channels.begin()); i != active_channels.end(); ++i)
	{
		eSmartPtrList<eDVBRegisteredFrontend> &frontends = simulate ? m_simulate_frontend : m_frontend;
//		eDebug("[eDVBResourceManager] available channel.. %04x:%04x", i->m_channel_id.transport_stream_id.get(), i->m_channel_id.original_network_id.get());
		if (i->m_channel_id == ignore)
		{
			eDVBChannel *channel = (eDVBChannel*) &(*i->m_channel);
			// one eUsePtr<iDVBChannel> is used in eDVBServicePMTHandler
			// another on eUsePtr<iDVBChannel> is used in the eDVBScan instance used in eDVBServicePMTHandler (for SDT scan)
			// so we must check here if usecount is 3 (when the channel is equal to the cached channel)
			// or 2 when the cached channel is not equal to the compared channel
			int check_usecount = channel == &(*m_cached_channel) ? 1 : 0;
			check_usecount += (apply_to_ignore+1) * 2; // one is used in eDVBServicePMTHandler and another is used in eDVBScan.
			//eDebug("[eDVBResourceManager] canAllocateChannel channel->getUseCount() : %d , check_usecount : %d (cached : %d)", channel->getUseCount(), check_usecount, channel == &(*m_cached_channel));
			if (channel->getUseCount() == check_usecount)  // channel only used once..(except fcc)
			{
				ePtr<iDVBFrontend> fe;
				if (!i->m_channel->getFrontend(fe))
				{
					for (eSmartPtrList<eDVBRegisteredFrontend>::iterator ii(frontends.begin()); ii != frontends.end(); ++ii)
					{
						if ( &(*fe) == &(*ii->m_frontend) )
						{
							//eDebug("[eDVBResourceManager] canAllocateChannel ignore : decrease fcc fe use_count! feid : %d (%d -> %d)", ii->m_frontend->getSlotID(), ii->m_inuse, ii->m_inuse-1);
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
		eDebug("[eDVBResourceManager] no channel list set!");
		goto error;
	}

	if (m_list->getChannelFrontendData(channelid, feparm))
	{
		eDebug("[eDVBResourceManager] channel not found!");
		goto error;
	}
	feparm->getSystem(system);

	ret = canAllocateFrontend(feparm, simulate);

error:
	if (decremented_fe_usecount)
		++(*decremented_fe_usecount);
	if (decremented_cached_channel_fe_usecount)
		++(*decremented_cached_channel_fe_usecount);
	if (fcc_decremented_fe_usecounts.size())
	{
		for (std::vector<int*>::iterator i(fcc_decremented_fe_usecounts.begin()); i != fcc_decremented_fe_usecounts.end(); ++i)
		{
			//eDebug("[eDVBResourceManager] canAllocateChannel fcc : increase fcc fe use_count!");
			++(**i);
		}
	}

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
		eFilePushThread(IOPRIO_CLASS_BE, 0, packetsize, packetsize * 512),
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
	void filterRecordData(const unsigned char *data, int len);
};

void eDVBChannelFilePush::filterRecordData(const unsigned char *_data, int len)
{
	if (m_parity_switch_delay)
	{
		int offset;
		for (offset = 0; offset < len; offset += m_packet_size)
		{
			const unsigned char *pkt = _data + offset + m_packet_size - 188;
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
}

DEFINE_REF(eDVBChannel);

int eDVBChannel::m_debug = -1;

eDVBChannel::eDVBChannel(eDVBResourceManager *mgr, eDVBAllocatedFrontend *frontend): m_state(state_idle), m_mgr(mgr)
{
	if(eDVBChannel::m_debug < 0)
		eDVBChannel::m_debug = eSimpleConfig::getBool("config.crash.debugDVB", false) ? 1 : 0;

	m_frontend = frontend;

	m_pvr_thread = 0;
	m_pvr_fd_dst = -1;

	m_skipmode_n = m_skipmode_m = m_skipmode_frames = 0;

	if (m_frontend)
		m_frontend->get().connectStateChange(sigc::mem_fun(*this, &eDVBChannel::frontendStateChanged), m_conn_frontendStateChanged);
}

eDVBChannel::~eDVBChannel()
{
	if (m_channel_id)
		m_mgr->removeChannel(this);

	stop();
}

void eDVBChannel::frontendStateChanged(iDVBFrontend*fe)
{
	int state, ourstate = 0;

		/* if we are already in shutdown, don't change state. */
	if (m_state == state_release)
		return;

	if (fe->getState(state))
		return;

	int tuner_id = fe->getDVBID();
	if (state == iDVBFrontend::stateLock)
	{
		if(eDVBChannel::m_debug)
			eDebug("[eDVBChannel] OURSTATE: tuner %d ok", tuner_id);
		ourstate = state_ok;
	} else if (state == iDVBFrontend::stateTuning)
	{
		if(eDVBChannel::m_debug)
			eDebug("[eDVBChannel] OURSTATE: tuner %d tuning", tuner_id);
		ourstate = state_tuning;
	} else if (state == iDVBFrontend::stateLostLock)
	{
			/* on managed channels, we try to retune in order to re-acquire lock. */
		fe->setData(eDVBFrontend::CUR_FREQ,0);
		if (m_current_frontend_parameters)
		{
			eDebug("[eDVBChannel] OURSTATE: tuner %d lost lock, trying to retune", tuner_id);
			ourstate = state_tuning;
			m_frontend->get().tune(*m_current_frontend_parameters);
		} else
			/* on unmanaged channels, we don't do this. the client will do this. */
		{
			eDebug("[eDVBChannel] OURSTATE: tuner %d lost lock, unavailable now.", tuner_id);
			ourstate = state_unavailable;
		}
	} else if (state == iDVBFrontend::stateFailed)
	{
		ourstate = state_failed;
		fe->setData(eDVBFrontend::CUR_FREQ,0);
			/* on managed channels, we do a retry */
		if (m_current_frontend_parameters)
		{
			eDebug("[eDVBChannel] OURSTATE: tuner %d failed, retune", tuner_id);
			m_frontend->get().tune(*m_current_frontend_parameters);
		} else
		{ /* nothing we can do */
			eDebug("[eDVBChannel] OURSTATE: tuner %d failed, fatal", tuner_id);
		}
	} else
		eFatal("[eDVBChannel] tuner %d state unknown", tuner_id);

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
		eDebug("[eDVBChannel] End of file!");
		m_event(this, evtEOF);
		break;
	case eFilePushThread::evtUser: /* start */
		eDebug("[eDVBChannel] SOF");
		m_event(this, evtSOF);
		break;
	case eFilePushThread::evtStopped:
		eDebug("[eDVBChannel] pvrEvent evtStopped");
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
		eDebug("[eDVBChannel] seek.");
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
				eDebug("[eDVBChannel] skipmode ratio is %lld:90000, bitrate is %d bit/s", m_cue->m_skipmode_ratio, bitrate);
						/* i agree that this might look a bit like black magic. */
				m_skipmode_n = 512*1024; /* must be 1 iframe at least. */
// The / and * are done in order, resulting in a distinct integer
// truncation after bitrate / 8 / 90000
// I don't think that this is intended...
// github.com/OpenViX/enigma2/commit/33d172b5a3ad1b22d69ce60c2102552537b77929
//				m_skipmode_m = bitrate / 8 / 90000 * m_cue->m_skipmode_ratio / 8;
				m_skipmode_frames = m_cue->m_skipmode_ratio / 90000;
				m_skipmode_m = (bitrate / 8) * (m_skipmode_frames / 8);
				m_skipmode_frames_remainder = 0;

				if (m_cue->m_skipmode_ratio < 0)
					m_skipmode_m -= m_skipmode_n;

				eDebug("[eDVBChannel] resolved to: %d %d", m_skipmode_m, m_skipmode_n);

				if (abs(m_skipmode_m) < abs(m_skipmode_n))
				{
					eWarning("[eDVBChannel] something is wrong with this cueSheetEvent calculation");
					m_skipmode_frames = m_skipmode_n = m_skipmode_m = 0;
				}
			} else
			{
				eDebug("[eDVBChannel] skipmode ratio is 0, normal play");
				m_skipmode_frames = m_skipmode_n = m_skipmode_m = 0;
			}
		}
		m_pvr_thread->setIFrameSearch(m_skipmode_n != 0);
		if (m_cue->m_skipmode_ratio != 0)
			m_pvr_thread->setTimebaseChange(0x10000 * 9000 / (m_cue->m_skipmode_ratio / 10)); /* negative values are also ok */
		else
			m_pvr_thread->setTimebaseChange(0); /* normal playback */
		eDebug("[eDVBChannel] flush pvr");
		flushPVR(m_cue->m_decoding_demux);
		eDebug("[eDVBChannel] done");
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
				eDebug("[eDVBChannel] span translation failed.\n");
				continue;
			}
			eDebug("[eDVBChannel] source span: %lld .. %lld, translated to %jd..%jd", pts_in, pts_out, (intmax_t)offset_in, (intmax_t)offset_out);
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

static size_t diff_upto(off_t high, off_t low, size_t max)
{
	size_t diff = static_cast<size_t>(high-low);
	if (diff < max)
		return diff;
	return max;
}

	/* remember, this gets called from another thread. */
void eDVBChannel::getNextSourceSpan(off_t current_offset, size_t bytes_read, off_t &start, size_t &size, int blocksize, int &sof)
{
	unsigned int max = align(1024*1024*1024, blocksize);
	current_offset = align(current_offset, blocksize);

	if (!m_cue)
	{
		eDebug("[eDVBChannel] no cue sheet. forcing normal play");
		start = current_offset;
		size = max;
		return;
	}

	if (m_skipmode_n)
	{
		max = align(m_skipmode_n, blocksize);
	}

	//eDebug("[eDVBChannel] getNextSourceSpan, current offset is %08llx, m_skipmode_m = %d!", current_offset, m_skipmode_m);
	int frame_skip_success = 0;

	if (m_skipmode_m)
	{
		int frames_to_skip = m_skipmode_frames + m_skipmode_frames_remainder;
		//eDebug("[eDVBChannel] we are at %llu, and we try to skip %d+%d frames from here", current_offset, m_skipmode_frames, m_skipmode_frames_remainder);
		size_t iframe_len;
		off_t iframe_start = current_offset;
		int frames_skipped = frames_to_skip;
		m_tstools_lock.lock();
		int r = m_tstools.findNextPicture(iframe_start, iframe_len, frames_skipped);
		m_tstools_lock.unlock();
		if (!r)
		{
			m_skipmode_frames_remainder = frames_to_skip - frames_skipped;
			//eDebug("[eDVBChannel] successfully skipped %d (out of %d, rem now %d) frames.", frames_skipped, frames_to_skip, m_skipmode_frames_remainder);
			current_offset = align(iframe_start, blocksize);
			max = align(iframe_len + 187, blocksize);
			frame_skip_success = 1;
		} else
		{
			m_skipmode_frames_remainder = 0;
			eDebug("[eDVBChannel] frame skipping failed, reverting to byte-skipping");
		}
	}

	if (!frame_skip_success)
	{
		current_offset += align(m_skipmode_m, blocksize);

		if (m_skipmode_m)
		{
			eDebug("[eDVBChannel] we are at %jd, and we try to find the iframe here:", (intmax_t)current_offset);
			size_t iframe_len;
			off_t iframe_start = current_offset;

			int direction = (m_skipmode_m < 0) ? -1 : +1;
			m_tstools_lock.lock();
			int r = m_tstools.findFrame(iframe_start, iframe_len, direction);
			m_tstools_lock.unlock();
			if (r)
				eDebug("[eDVBChannel] failed");
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
				eDebug("[eDVBChannel] no decoder - can't seek relative");
				continue;
			}
			if (m_cue->m_decoder->getPTS(0, now))
			{
				eDebug("[eDVBChannel] decoder getPTS failed, can't seek relative");
				continue;
			}
			if (!m_cue->m_decoding_demux)
			{
				eDebug("[eDVBChannel] getNextSourceSpan, no decoding demux. couldn't seek to %llu... ignore request!", pts);
				start = current_offset;
				size = max;
				continue;
			}
			if (getCurrentPosition(m_cue->m_decoding_demux, now, 1))
			{
				eDebug("[eDVBChannel] seekTo: getCurrentPosition failed!");
				continue;
			}
		} else if (pts < 0) /* seek relative to end */
		{
			pts_t len;
			if (!getLength(len))
			{
				eDebug("[eDVBChannel] seeking relative to end. len=%lld, seek = %lld", len, pts);
				pts += len;
			} else
			{
				eWarning("[eDVBChannel] getLength failed - can't seek relative to end!");
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
			eDebug("[eDVBChannel] AP relative seeking: %lld, at %lld", pts, now);
			pts_t nextap;
			eSingleLocker l(m_tstools_lock);
			if (m_tstools.getNextAccessPoint(nextap, now, pts))
			{
				pts = now - 90000; /* approx. 1s */
				eDebug("[eDVBChannel] AP relative seeking failed!");
			} else
			{
				pts = nextap;
				eDebug("[eDVBChannel] next ap is %llu\n", pts);
			}
		}

		off_t offset = 0;
		m_tstools_lock.lock();
		int r = m_tstools.getOffset(offset, pts, -1);
		m_tstools_lock.unlock();
		if (r)
		{
			eDebug("[eDVBChannel] get offset for pts=%llu failed!", pts);
			continue;
		}

		eDebug("[eDVBChannel] ok, resolved skip (rel: %d, diff %lld), now at %16jx", relative, pts, (intmax_t)offset);
		current_offset = align(offset, blocksize); /* in case tstools return non-aligned offset */
	}

	m_cue->m_lock.Unlock();

	for (std::list<std::pair<off_t, off_t> >::const_iterator i(m_source_span.begin()); i != m_source_span.end(); ++i)
	{
		if (current_offset >= i->first)
		{
			if (current_offset < i->second)
			{
				start = current_offset;
				size = diff_upto(i->second, start, max);
				//eDebug("[eDVBChannel] HIT, %lld < %lld < %lld, size: %zd", i->first, current_offset, i->second, size);
				return;
			}
		}
		else /* (current_offset < i->first) */
		{
				/* ok, our current offset is in an 'out' zone. */
			if ((m_skipmode_m >= 0) || (i == m_source_span.begin()))
			{
					/* in normal playback, just start at the next zone. */
				start = i->first;
				size = align(diff_upto(i->second, start, max), blocksize);
				eDebug("[eDVBChannel] skip");
				if (m_skipmode_m < 0)
				{
					eDebug("[eDVBChannel] reached SOF");
					m_skipmode_m = 0;
					sof = 1;
				}
			}
			else
			{
				/* when skipping reverse, however, choose the zone before. */
				/* This returns a size 0 block, in case you noticed... */
				--i;
				eDebug("[eDVBChannel] skip to previous block, which is %jd..%jd", (intmax_t)i->first, (intmax_t)i->second);
				size_t len = diff_upto(i->second, i->first, max);
				start = i->second - len;
				eDebug("[eDVBChannel] skipping to %jd, %zd", (intmax_t)start, len);
			}

			eDebug("[eDVBChannel] result: %jd, %zx (%jd %jd)", (intmax_t)start, size, (intmax_t)i->first, (intmax_t)i->second);
			return;
		}
	}

//	if ((current_offset < -m_skipmode_m) && (m_skipmode_m < 0))
	if ((current_offset < 0) && (m_skipmode_m < 0))
	{
		eDebug("[eDVBChannel] reached SOF");
		m_skipmode_m = 0;
		sof = 1;
	}

	start = current_offset;
	if (m_source_span.empty())
	{
		size = max;
		// eDebug("[eDVBChannel] NO CUESHEET. (%08llx, %zd)", start, size);
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
	int count = --m_use_count;
	if (!count)
	{
		m_state = state_release;
		m_stateChanged(this);
	}
	else if (count == 1)
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

	m_current_frontend_parameters = feparm;

	if (!m_frontend)
	{
		/* no frontend, no need to tune (must be a streamed service) */
		return 0;
	}

	m_state = state_tuning;
			/* if tuning fails, shutdown the channel immediately. */
	int res;
	res = m_frontend->get().tune(*feparm);

	if (res)
	{
		m_state = state_release;
		m_stateChanged(this);
		return res;
	}

	return 0;
}

RESULT eDVBChannel::connectStateChange(const sigc::slot<void(iDVBChannel*)> &stateChange, ePtr<eConnection> &connection)
{
	connection = new eConnection((iDVBChannel*)this, m_stateChanged.connect(stateChange));
	return 0;
}

RESULT eDVBChannel::connectEvent(const sigc::slot<void(iDVBChannel*,int)> &event, ePtr<eConnection> &connection)
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
	int tsid = -1, onid = -1;
	if (!result)
	{
		for (std::vector<ServiceDescriptionSection*>::const_iterator i = m_SDT->getSections().begin(); i != m_SDT->getSections().end(); ++i)
		{
			tsid = (*i)->getTransportStreamId();
			onid = (*i)->getOriginalNetworkId();
			break;
		}
	}
	/* emit */ receivedTsidOnid(tsid, onid);
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

int eDVBChannel::getDvrId()
{
	ePtr<eDVBAllocatedDemux> dmx = m_decoder_demux ? m_decoder_demux : m_demux;
	if (dmx)
	{
		return dmx->get().getDvrId();
	}
	return -1;
}

RESULT eDVBChannel::requestTsidOnid()
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
			return 0;
		}
	}
	return -1;
}

RESULT eDVBChannel::getDemux(ePtr<iDVBDemux> &demux, int cap)
{
	ePtr<eDVBAllocatedDemux> &our_demux = (cap & capDecode) ? m_decoder_demux : m_demux;

	if(eDVBChannel::m_debug)
		eDebug("[eDVBChannel] getDemux cap=%02X", cap);
	if (!m_frontend)
	{
		/* in dvr mode, we have to stick to a single demux (the one connected to our dvr device) */
		our_demux = m_decoder_demux ? m_decoder_demux : m_demux;
	}

	if (!our_demux)
	{
		demux = 0;
		// eDebug"[eDVBChannel] DEBUG getDemux call allocateDemuxu");
		if (m_mgr->allocateDemux(m_frontend ? (eDVBRegisteredFrontend*)*m_frontend : (eDVBRegisteredFrontend*)0, our_demux, cap))
			return -1;

	}
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
		eDebug("[eDVBChannel] can't open PVR file %s (%m)", file);
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
		m_pvr_thread = 0;
	}

	if (!source->valid() && !source->isStream())
	{
		eDebug("[eDVBChannel] PVR source is not valid!");
		return -ENOENT;
	}

	m_source = source;
	m_tstools.setSource(m_source, streaminfo_file);

	if (m_pvr_fd_dst < 0)
	{
		ePtr<eDVBAllocatedDemux> &demux = m_demux ? m_demux : m_decoder_demux;
		if (demux)
		{
			m_pvr_fd_dst = demux->get().openDVR(O_WRONLY);
			if (m_pvr_fd_dst < 0)
			{
				eDebug("[eDVBChannel] can't open /dev/dvb/adapterX/dvrX: %m");
				return -ENODEV;
			}
		}
		else
		{
			eDebug("[eDVBChannel] no demux allocated yet.. so its not possible to open the dvr device!!");
			return -ENODEV;
		}
	}

	m_pvr_thread = new eDVBChannelFilePush(m_source->getPacketSize());
	m_pvr_thread->enablePVRCommit(1);
	m_pvr_thread->setStreamMode(m_source->isStream());
	m_pvr_thread->setScatterGather(this);

	m_event(this, evtPreStart);

	m_pvr_thread->start(m_source, m_pvr_fd_dst);
	CONNECT(m_pvr_thread->m_event, eDVBChannel::pvrEvent);

	m_state = state_ok;
	m_stateChanged(this);

	return 0;
}

void eDVBChannel::stop()
{
	if (m_pvr_thread)
	{
		m_pvr_thread->stop();
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

void eDVBChannel::setCueSheet(eCueSheet *cuesheet)
{
	m_conn_cueSheetEvent = 0;
	m_cue = cuesheet;
	if (m_cue)
		m_cue->connectEvent(sigc::mem_fun(*this, &eDVBChannel::cueSheetEvent), m_conn_cueSheetEvent);
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
			eDebug("[eDVBChannel] demux getSTC failed");
			return -1;
		}
	} else
		now = pos; /* fixup supplied */

	m_tstools_lock.lock();
	/* Interesting: the only place where iTSSource->offset() is ever used */
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

RESULT eCueSheet::connectEvent(const sigc::slot<void(int)> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_event.connect(event));
	return 0;
}
