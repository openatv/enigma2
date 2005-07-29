#ifndef __lib_dvb_iservice_h
#define __lib_dvb_iservice_h

#include <lib/base/object.h>
#include <string>
#include <connection.h>
#include <list>

class eServiceReference
{
public:
	enum
	{
		idInvalid=-1,
		idStructure,	// service_id == 0 is root
		idDVB,
		idFile,
		idUser=0x1000
	};
	int type;

	int flags; // flags will NOT be compared.
	enum
	{
		isDirectory=1,		// SHOULD enter  (implies mustDescent)
		mustDescent=2,		// cannot be played directly - often used with "isDirectory" (implies canDescent)
		/*
			for example:
				normal services have none of them - they can be fed directly into the "play"-handler.
				normal directories have both of them set - you cannot play a directory directly and the UI should descent into it.
				playlists have "mustDescent", but not "isDirectory" - you don't want the user to browse inside the playlist (unless he really wants)
				services with sub-services have none of them, instead the have the "canDecsent" flag (as all of the above)
		*/
		canDescent=4,			// supports enterDirectory/leaveDirectory
		flagDirectory=isDirectory|mustDescent|canDescent,
		shouldSort=8,			// should be ASCII-sorted according to service_name. great for directories.
		hasSortKey=16,		// has a sort key in data[3]. not having a sort key implies 0.
		sort1=32					// sort key is 1 instead of 0
	};

	inline int getSortKey() const { return (flags & hasSortKey) ? data[3] : ((flags & sort1) ? 1 : 0); }

	int data[8];
	std::string path;

	eServiceReference()
		: type(idInvalid), flags(0)
	{
	}

	eServiceReference(int type, int flags)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
	}
	eServiceReference(int type, int flags, int data0)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		data[0]=data0;
	}
	eServiceReference(int type, int flags, int data0, int data1)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		data[0]=data0;
		data[1]=data1;
	}
	eServiceReference(int type, int flags, int data0, int data1, int data2)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		data[0]=data0;
		data[1]=data1;
		data[2]=data2;
	}
	eServiceReference(int type, int flags, int data0, int data1, int data2, int data3)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		data[0]=data0;
		data[1]=data1;
		data[2]=data2;
		data[3]=data3;
	}
	eServiceReference(int type, int flags, int data0, int data1, int data2, int data3, int data4)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		data[0]=data0;
		data[1]=data1;
		data[2]=data2;
		data[3]=data3;
		data[4]=data4;
	}
	eServiceReference(int type, int flags, const std::string &path)
		: type(type), flags(flags), path(path)
	{
		memset(data, 0, sizeof(data));
	}
	eServiceReference(const std::string &string);
	std::string toString() const;
	bool operator==(const eServiceReference &c) const
	{
		if (type != c.type)
			return 0;
		return /* (flags == c.flags) && */ (memcmp(data, c.data, sizeof(int)*8)==0) && (path == c.path);
	}
	bool operator!=(const eServiceReference &c) const
	{
		return !(*this == c);
	}
	bool operator<(const eServiceReference &c) const
	{
		if (type < c.type)
			return 1;

		if (type > c.type)
			return 0;
			
/*		if (flags < c.flags)
			return 1;
		if (flags > c.flags)
			return 0; */

		int r=memcmp(data, c.data, sizeof(int)*8);
		if (r)
			return r < 0;
		return path < c.path;
	}
	operator bool() const
	{
		return type != idInvalid;
	}
};

	/* the reason we have the servicereference as additional argument is
	   that we don't have to create one object for every entry in a possibly
	   large list, provided that no state information is nessesary to deliver
	   the required information. Anyway - ref *must* be the same as the argument
	   to the info() or getIServiceInformation call! */
class iStaticServiceInformation: public iObject
{
public:
	virtual RESULT getName(const eServiceReference &ref, std::string &name)=0;

		// FOR SWIG
	std::string getName(const eServiceReference &ref) { std::string temp; getName(ref, temp); return temp; }
};

TEMPLATE_TYPEDEF(ePtr<iStaticServiceInformation>, iStaticServiceInformationPtr);

class eServiceEvent;

class iServiceInformation: public iObject
{
public:
	virtual RESULT getName(std::string &name)=0;
		// FOR SWIG
	std::string getName() { std::string temp; getName(temp); return temp; }
	virtual RESULT getEvent(ePtr<eServiceEvent> &evt, int nownext);
};

TEMPLATE_TYPEDEF(ePtr<iServiceInformation>, iServiceInformationPtr);

class iPauseableService: public iObject
{
public:
	virtual RESULT pause()=0;
	virtual RESULT unpause()=0;
};

TEMPLATE_TYPEDEF(ePtr<iPauseableService>, iPauseableServicePtr);

class iPlayableService: public iObject
{
	friend class iServiceHandler;
public:
	enum
	{
		evStart,
		evEnd,
		
		// when iServiceInformation is implemented:
		evUpdatedEventInfo
	};
	virtual RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)=0;
	virtual RESULT start()=0;
	virtual RESULT stop()=0;
	virtual RESULT pause(ePtr<iPauseableService> &ptr)=0;
	virtual RESULT info(ePtr<iServiceInformation> &ptr)=0;
};

TEMPLATE_TYPEDEF(ePtr<iPlayableService>, iPlayableServicePtr);

class iRecordableService: public iObject
{
public:
	virtual RESULT prepare()=0;
	virtual RESULT start()=0;
	virtual RESULT stop()=0;
};

TEMPLATE_TYPEDEF(ePtr<iRecordableService>, iRecordableServicePtr);

// TEMPLATE_TYPEDEF(std::list<eServiceReference>, eServiceReferenceList);

class iListableService: public iObject
{
public:
		/* legacy interface: get a list */
	virtual RESULT getContent(std::list<eServiceReference> &list)=0;
	
		/* new, shiny interface: streaming. */
	virtual RESULT getNext(eServiceReference &ptr)=0;
};

TEMPLATE_TYPEDEF(ePtr<iListableService>, iListableServicePtr);

class iServiceHandler: public iObject
{
public:
	virtual RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr)=0;
	virtual RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr)=0;
	virtual RESULT list(const eServiceReference &, ePtr<iListableService> &ptr)=0;
	virtual RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
};

TEMPLATE_TYPEDEF(ePtr<iServiceHandler>, iServiceHandlerPtr);

#endif
