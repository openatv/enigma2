#ifndef _hdmi_cec_h
#define _hdmi_cec_h

#include <lib/driver/rc.h>
#include <lib/python/connections.h>

class eSocketNotifier;

class eHdmiCEC : public eRCDriver
{
#ifndef SWIG
public:
struct cec_message
{
	unsigned char address;
	unsigned char length;
	unsigned char data[256];
}__attribute__((packed));
#endif
protected:
	static eHdmiCEC *instance;
	int hdmiFd;
	ePtr<eSocketNotifier> messageNotifier;
	void getAddressInfo(unsigned char *physicaladdress, unsigned char &logicaladdress, unsigned char &type);
	bool getActiveStatus();
	long translateKey(unsigned char code);
	void hdmiEvent(int what);
	void sendMessage(struct cec_message &message);
#ifdef SWIG
	eHdmiCEC();
	~eHdmiCEC();
#endif
public:
#ifndef SWIG
	eHdmiCEC();
	~eHdmiCEC();
#endif
	static eHdmiCEC *getInstance();
	PSignal2<void, int, int> messageReceived;
	void sendMessage(unsigned char address, unsigned char length, char *data);
	int getLogicalAddress();
	int getPhysicalAddress();
	int getDeviceType();
};

class eHdmiCECDevice : public eRCDevice
{
public:
	void handleCode(long code);
	eHdmiCECDevice(eRCDriver *driver);
	const char *getDescription() const;
};

#endif
