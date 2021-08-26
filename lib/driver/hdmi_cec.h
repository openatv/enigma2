#ifndef _hdmi_cec_h
#define _hdmi_cec_h

#include <lib/driver/rc.h>
#include <lib/python/connections.h>

class eSocketNotifier;

SWIG_IGNORE(iCECMessage);
class iCECMessage : public iObject
{
public:
#ifdef SWIG
	iCECMessage();
	~iCECMessage();
#endif
	virtual int getAddress() = 0;
	virtual int getCommand() = 0;
	virtual int getData(char *data, int length) = 0;
	virtual int getControl0() = 0;
	virtual int getControl1() = 0;
	virtual int getControl2() = 0;
	virtual int getControl3() = 0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iCECMessage>, iCECMessagePtr);

extern PyObject *New_iCECMessagePtr(const ePtr<iCECMessage> &ref); /* defined in enigma_python.i */

inline PyObject *PyFrom(ePtr<iCECMessage> &c)
{
	return New_iCECMessagePtr(c);
}

#ifndef SWIG
inline ePyObject Impl_New_iCECMessagePtr(const ePtr<iCECMessage> &ptr)
{
	return New_iCECMessagePtr(ptr);
}
#define NEW_iCECMessagePtr(ptr) Impl_New_iCECMessagePtr(ptr)
#endif

class eHdmiCEC : public eRCDriver
{
#ifndef SWIG
public:
#ifdef DREAMBOX
	struct cec_message
	{
		unsigned char address;
		unsigned char data[16];
		unsigned char length;
		unsigned char flag;
	}__attribute__((packed));
	struct cec_rx_message
	{
		unsigned char address;
		unsigned char destination;
		unsigned char data[16];
		unsigned char length;
	}__attribute__((packed));
	struct addressinfo
	{
		unsigned char physical[2];
		unsigned char logical;
		unsigned char type;
	};
#else
	struct cec_message
	{
		unsigned char address;
		unsigned char length;
		unsigned char data[256];
	}__attribute__((packed));
#define cec_rx_message cec_message
	struct addressinfo
	{
		unsigned char logical;
		unsigned char physical[2];
		unsigned char type;
	};
#endif
	class eCECMessage : public iCECMessage
	{
		DECLARE_REF(eCECMessage);
		unsigned char address;
		unsigned char command;
		unsigned char dataLength;
		unsigned char messageData[255];
		unsigned char control0;
		unsigned char control1;
		unsigned char control2;
		unsigned char control3;
	public:
		eCECMessage(int address, int command, char *data, int length);
		int getAddress();
		int getCommand();
		int getData(char *data, int length);
		int getControl0() { return control0; }
		int getControl1() { return control1; }
		int getControl2() { return control2; }
		int getControl3() { return control3; }
	};
	void sendMessage(struct cec_message &message);
#endif
protected:
	static eHdmiCEC *instance;
	bool linuxCEC;
	unsigned char physicalAddress[2];
	bool fixedAddress;
	unsigned char deviceType, logicalAddress;
	int hdmiFd;
	ePtr<eSocketNotifier> messageNotifier;
	void addressPoll();
	void reportPhysicalAddress();
	void getAddressInfo();
	bool getActiveStatus();
	long translateKey(unsigned char code);
	void hdmiEvent(int what);
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
	PSignal1<void, ePtr<iCECMessage> &> messageReceived;
	PSignal1<void, int> addressChanged;
	void sendMessage(unsigned char address, unsigned char cmd, char *data, int length);
	int getLogicalAddress();
	int getPhysicalAddress();
	void setFixedPhysicalAddress(int address);
	int getDeviceType();
};

#ifndef SWIG
class eHdmiCECDevice : public eRCDevice
{
public:
	void handleCode(long code);
	eHdmiCECDevice(eRCDriver *driver);
	const char *getDescription() const;
};
#endif

#endif
