#ifndef __rfmod_h
#define __rfmod_h

class eRFmod
{
	static eRFmod *instance;
	
	int fd;
#ifdef SWIG
	eRFmod();
	~eRFmod();
#endif
public:
#ifndef SWIG
	eRFmod();
	~eRFmod();
#endif
	static eRFmod *getInstance();
	bool detected() { return fd >= 0; }
	void setFunction(int val);						//0=Enable 1=Disable
	void setTestmode(int val);						//0=Enable 1=Disable
	void setSoundFunction(int val);				//0=Enable 1=Disable
	void setSoundCarrier(int val);
	void setChannel(int val);
	void setFinetune(int val);
};

#endif
