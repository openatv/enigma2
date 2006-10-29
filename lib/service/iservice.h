#ifndef __lib_dvb_iservice_h
#define __lib_dvb_iservice_h

#include <lib/python/swig.h>
#include <lib/python/python.h>
#include <lib/base/object.h>
#include <string>
#include <connection.h>
#include <list>

class eServiceEvent;

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
		sort1=32,					// sort key is 1 instead of 0
		isMarker=64			// Marker
	};
	int flags; // flags will NOT be compared.

	inline int getSortKey() const { return (flags & hasSortKey) ? data[3] : ((flags & sort1) ? 1 : 0); }

#ifndef SWIG
	int data[8];
	std::string path;
#endif
	std::string getPath() { return path; }
	void setPath( const std::string &n ) { path=n; }

	unsigned int getUnsignedData(unsigned int num) const
	{
		if ( num < sizeof(data)/sizeof(int) )
			return data[num];
		return 0;
	}

	int getData(unsigned int num) const
	{
		if ( num < sizeof(data)/sizeof(int) )
			return data[num];
		return 0;
	}

	void setUnsignedData(unsigned int num, unsigned int val)
	{
		if ( num < sizeof(data)/sizeof(int) )
			data[num] = val;
	}

	void setData(unsigned int num, int val)
	{
		if ( num < sizeof(data)/sizeof(int) )
			data[num] = val;
	}

// only for override service names in bouquets or to give servicerefs a name which not have a
// real existing service ( for dvb eServiceDVB )
#ifndef SWIG
	std::string name;
#endif
	std::string getName() { return name; }
	void setName( const std::string &n ) { name=n; }

	eServiceReference()
		: type(idInvalid), flags(0)
	{
		memset(data, 0, sizeof(data));
	}
#ifndef SWIG
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
#endif
	eServiceReference(const std::string &string);
	std::string toString() const;
	std::string toCompareString() const;
	bool operator==(const eServiceReference &c) const
	{
		if (type != c.type)
			return 0;
		return (memcmp(data, c.data, sizeof(int)*8)==0) && (path == c.path);
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

		int r=memcmp(data, c.data, sizeof(int)*8);
		if (r)
			return r < 0;
		return path < c.path;
	}
	operator bool() const
	{
		return valid();
	}
	
	int valid() const
	{
		return type != idInvalid;
	}
};

SWIG_ALLOW_OUTPUT_SIMPLE(eServiceReference);

extern PyObject *New_eServiceReference(const eServiceReference &ref); // defined in enigma_python.i

typedef long long pts_t;

	/* the reason we have the servicereference as additional argument is
	   that we don't have to create one object for every entry in a possibly
	   large list, provided that no state information is nessesary to deliver
	   the required information. Anyway - ref *must* be the same as the argument
	   to the info() or getIServiceInformation call! */

	/* About the usage of SWIG_VOID:
	   SWIG_VOID(real_returntype_t) hides a return value from swig. This is used for
	   the "superflouus" RESULT return values.
	   
	   Python code has to check the returned pointer against 0. This works,
	   as all functions returning instances in smartpointers AND having a 
	   RESULT have to BOTH return non-zero AND set the pointer to zero.
	   
	   Python code thus can't check for the reason, but the reason isn't
	   user-servicable anyway. If you want to return a real reason which
	   goes beyong "it just doesn't work", use extra variables for this,
	   not the RESULT.
	   
	   Hide the result only if there is another way to check for failure! */
	   
TEMPLATE_TYPEDEF(ePtr<eServiceEvent>, eServiceEventPtr);
	
class iStaticServiceInformation: public iObject
{
#ifdef SWIG
	iStaticServiceInformation();
	~iStaticServiceInformation();
#endif
public:
	virtual SWIG_VOID(RESULT) getName(const eServiceReference &ref, std::string &SWIG_OUTPUT)=0;
	
		// doesn't need to be implemented, should return -1 then.
	virtual int getLength(const eServiceReference &ref);
	virtual SWIG_VOID(RESULT) getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &SWIG_OUTPUT, time_t start_time=-1);
		// returns true when not implemented
	virtual bool isPlayable(const eServiceReference &ref, const eServiceReference &ignore);

	virtual int getInfo(const eServiceReference &ref, int w);
	virtual std::string getInfoString(const eServiceReference &ref,int w);
};

TEMPLATE_TYPEDEF(ePtr<iStaticServiceInformation>, iStaticServiceInformationPtr);

class iServiceInformation: public iObject
{
#ifdef SWIG
	iServiceInformation();
	~iServiceInformation();
#endif
public:
	virtual SWIG_VOID(RESULT) getName(std::string &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) getEvent(ePtr<eServiceEvent> &SWIG_OUTPUT, int nownext);

	enum {
		sIsCrypted,  /* is encrypted (no indication if decrypt was possible) */
		sAspect,     /* aspect ratio: 0=4:3, 1=16:9, 2=whatever we need */
		sIsMultichannel, /* multichannel *available* (probably not selected) */
		
			/* "user serviceable info" - they are not reliable. Don't use them for anything except the service menu!
			   that's also the reason why they are so globally defined. 
			   
			   
			   again - if somebody EVER tries to use this information for anything else than simply displaying it,
			   i will change this to return a user-readable text like "zero x zero three three" (and change the
			   exact spelling in every version) to stop that!
			*/
		sVideoPID,
		sAudioPID,
		sPCRPID,
		sPMTPID,
		sTXTPID,
		
		sSID,
		sONID,
		sTSID,
		sNamespace,
		sProvider,
		
		sDescription,
		sServiceref,
		sTimeCreate,	// unix time or string
		
		sTitle,
		sArtist,
		sAlbum,
		sComment,
		sTracknumber,
		sGenre,
		sCAIDs,
		sVideoType,  // MPEG2 MPEG4
		
		sTags,  /* space seperated list of tags */
	};
	enum { resNA = -1, resIsString = -2, resIsPyObject = -3 };

	virtual int getInfo(int w);
	virtual std::string getInfoString(int w);
	virtual PyObject *getInfoObject(int w);
};

TEMPLATE_TYPEDEF(ePtr<iServiceInformation>, iServiceInformationPtr);

class iFrontendInformation: public iObject
{
#ifdef SWIG
	iFrontendInformation();
	~iFrontendInformation();
#endif
public:
	enum {
		bitErrorRate,
		signalPower,
		signalQuality,
		lockState,
		syncState,
		frontendNumber
	};
	virtual int getFrontendInfo(int w)=0;
	virtual PyObject *getFrontendData(bool original=false)=0;
};

TEMPLATE_TYPEDEF(ePtr<iFrontendInformation>, iFrontendInformationPtr);

class iPauseableService: public iObject
{
#ifdef SWIG
	iPausableService();
	~iPausableService();
#endif
public:
	virtual RESULT pause()=0;
	virtual RESULT unpause()=0;
	
		/* hm. */
	virtual RESULT setSlowMotion(int ratio=0)=0;
	virtual RESULT setFastForward(int ratio=0)=0;
};

TEMPLATE_TYPEDEF(ePtr<iPauseableService>, iPauseableServicePtr);

class iSeekableService: public iObject
{
#ifdef SWIG
	iSeekableService();
	~iSeekableService();
#endif
public:
	virtual RESULT getLength(pts_t &SWIG_OUTPUT)=0;
	virtual RESULT seekTo(pts_t to)=0;
	enum { dirForward = +1, dirBackward = -1 };
	virtual RESULT seekRelative(int direction, pts_t to)=0;
	virtual RESULT getPlayPosition(pts_t &SWIG_OUTPUT)=0;
		/* if you want to do several seeks in a row, you can enable the trickmode. 
		   audio will be switched off, sync will be disabled etc. */
	virtual RESULT setTrickmode(int trick=0)=0;
	virtual RESULT isCurrentlySeekable()=0;
};

TEMPLATE_TYPEDEF(ePtr<iSeekableService>, iSeekableServicePtr);

struct iAudioTrackInfo
{
#ifndef SWIG
	std::string m_description;
	std::string m_language; /* iso639 */
#endif
	std::string getDescription() { return m_description; }
	std::string getLanguage() { return m_language; }
};

SWIG_ALLOW_OUTPUT_SIMPLE(iAudioTrackInfo);

class iAudioTrackSelection: public iObject
{
#ifdef SWIG
	iAudioTrackSelection();
	~iAudioTrackSelection();
#endif
public:
	virtual int getNumberOfTracks()=0;
	virtual RESULT selectTrack(unsigned int i)=0;
	virtual SWIG_VOID(RESULT) getTrackInfo(struct iAudioTrackInfo &SWIG_OUTPUT, unsigned int n)=0;
};

TEMPLATE_TYPEDEF(ePtr<iAudioTrackSelection>, iAudioTrackSelectionPtr);

class iAudioChannelSelection: public iObject
{
#ifdef SWIG
	iAudioChannelSelection();
	~iAudioChannelSelection();
#endif
public:
	enum { LEFT, STEREO, RIGHT };
	virtual int getCurrentChannel()=0;
	virtual RESULT selectChannel(int i)=0;
};

TEMPLATE_TYPEDEF(ePtr<iAudioChannelSelection>, iAudioChannelSelectionPtr);

class iAudioDelay: public iObject
{
#ifdef SWIG
	iAudioDelay();
	~iAudioDelay();
#endif
public:
	virtual int getAC3Delay()=0;
	virtual int getPCMDelay()=0;
	virtual void setAC3Delay(int)=0;
	virtual void setPCMDelay(int)=0;
};

TEMPLATE_TYPEDEF(ePtr<iAudioDelay>, iAudioDelayPtr);

class iRadioText: public iObject
{
#ifdef SWIG
	iRadioText();
	~iRadioText();
#endif
public:
	virtual std::string getRadioText(int x=0)=0;
};

TEMPLATE_TYPEDEF(ePtr<iRadioText>, iRadioTextPtr);

class iSubserviceList: public iObject
{
#ifdef SWIG
	iSubserviceList();
	~iSubserviceList();
#endif
public:
	virtual int getNumberOfSubservices()=0;
	virtual SWIG_VOID(RESULT) getSubservice(eServiceReference &SWIG_OUTPUT, unsigned int n)=0;
};

TEMPLATE_TYPEDEF(ePtr<iSubserviceList>, iSubserviceListPtr);

class iTimeshiftService: public iObject
{
#ifdef SWIG
	iTimeshiftService();
	~iTimeshiftService();
#endif
public:
	virtual RESULT startTimeshift()=0;
	virtual RESULT stopTimeshift()=0;
	
	virtual int isTimeshiftActive()=0;
			/* this essentially seeks to the relative end of the timeshift buffer */
	virtual RESULT activateTimeshift()=0;
};

TEMPLATE_TYPEDEF(ePtr<iTimeshiftService>, iTimeshiftServicePtr);

	/* not related to eCueSheet */
class iCueSheet: public iObject
{
#ifdef SWIG
	iCueSheet();
	~iCueSheet();
#endif
public:
			/* returns a list of (pts, what)-tuples */
	virtual PyObject *getCutList() = 0;
	virtual void setCutList(PyObject *list) = 0;
	virtual void setCutListEnable(int enable) = 0;
	enum { cutIn = 0, cutOut = 1, cutMark = 2 };
};

TEMPLATE_TYPEDEF(ePtr<iCueSheet>, iCueSheetPtr);

class eWidget;
class PyList;

class iSubtitleOutput: public iObject
{
public:
	virtual RESULT enableSubtitles(eWidget *parent, PyObject *entry)=0;
	virtual RESULT disableSubtitles(eWidget *parent)=0;
	virtual PyObject *getSubtitleList()=0;
};

TEMPLATE_TYPEDEF(ePtr<iSubtitleOutput>, iSubtitleOutputPtr);

class iPlayableService: public iObject
{
#ifdef SWIG
	iPlayableService();
	~iPlaybleService();
#endif
	friend class iServiceHandler;
public:
	enum
	{
			/* these first two events are magical, and should only
			   be generated if you know what you're doing. */
		evStart,
		evEnd,
		
		evTuneFailed,
			// when iServiceInformation is implemented:
		evUpdatedEventInfo,
		evUpdatedInfo,

			/* when seek() is implemented: */		
		evSeekableStatusChanged, /* for example when timeshifting */
		
		evEOF,
		evSOF, /* bounced against start of file (when seeking backwards) */
		
			/* only when cueSheet is implemented */
		evCuesheetChanged,

		evUpdatedRadioText
	};
	virtual RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)=0;
	virtual RESULT start()=0;
	virtual RESULT stop()=0;
			/* might have to be changed... */
	virtual RESULT setTarget(int target)=0;
	virtual SWIG_VOID(RESULT) seek(ePtr<iSeekableService> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) pause(ePtr<iPauseableService> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) info(ePtr<iServiceInformation> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) audioTracks(ePtr<iAudioTrackSelection> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) audioChannel(ePtr<iAudioChannelSelection> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) subServices(ePtr<iSubserviceList> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) frontendInfo(ePtr<iFrontendInformation> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) timeshift(ePtr<iTimeshiftService> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) cueSheet(ePtr<iCueSheet> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) subtitle(ePtr<iSubtitleOutput> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) audioDelay(ePtr<iAudioDelay> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) radioText(ePtr<iRadioText> &SWIG_OUTPUT)=0;
};

TEMPLATE_TYPEDEF(ePtr<iPlayableService>, iPlayableServicePtr);

class iRecordableService: public iObject
{
#ifdef SWIG
	iRecordableService();
	~iRecordableService();
#endif
public:
	virtual RESULT prepare(const char *filename, time_t begTime=-1, time_t endTime=-1, int eit_event_id=-1)=0;
	virtual RESULT start()=0;
	virtual RESULT stop()=0;
	virtual SWIG_VOID(RESULT) frontendInfo(ePtr<iFrontendInformation> &SWIG_OUTPUT)=0;
};

TEMPLATE_TYPEDEF(ePtr<iRecordableService>, iRecordableServicePtr);

// TEMPLATE_TYPEDEF(std::list<eServiceReference>, eServiceReferenceList);

class iMutableServiceList: public iObject
{
#ifdef SWIG
	iMutableServiceList();
	~iMutableServiceList();
#endif
public:
		/* flush changes */
	virtual RESULT flushChanges()=0;
		/* adds a service to a list */
	virtual RESULT addService(eServiceReference &ref, eServiceReference before=eServiceReference())=0;
		/* removes a service from a list */
	virtual RESULT removeService(eServiceReference &ref)=0;
		/* moves a service in a list, only if list suppports a specific sort method. */
		/* pos is the new, absolute position from 0..size-1 */
	virtual RESULT moveService(eServiceReference &ref, int pos)=0;
		/* set name of list, for bouquets this is the visible bouquet name */
	virtual RESULT setListName(const std::string &name)=0;
};

TEMPLATE_TYPEDEF(ePtr<iMutableServiceList>, iMutableServiceListPtr);

class iListableService: public iObject
{
#ifdef SWIG
	iListableService();
	~iListableService();
#endif
public:
		/* legacy interface: get a list */
	virtual RESULT getContent(std::list<eServiceReference> &list, bool sorted=false)=0;
	virtual PyObject *getContent(const char* format, bool sorted=false)=0;

		/* new, shiny interface: streaming. */
	virtual SWIG_VOID(RESULT) getNext(eServiceReference &SWIG_OUTPUT)=0;
	
		/* use this for sorting. output is not sorted because of either
		 - performance reasons: the whole list must be buffered or
		 - the interface would be restricted to a list. streaming
		   (as well as a future "active" extension) won't be possible.
		*/
	virtual int compareLessEqual(const eServiceReference &, const eServiceReference &)=0;
	
	virtual SWIG_VOID(RESULT) startEdit(ePtr<iMutableServiceList> &SWIG_OUTPUT)=0;
};

TEMPLATE_TYPEDEF(ePtr<iListableService>, iListableServicePtr);

#ifndef SWIG
	/* a helper class which can be used as argument to stl's sort(). */
class iListableServiceCompare
{
	ePtr<iListableService> m_list;
public:
	iListableServiceCompare(iListableService *list): m_list(list) { }
	bool operator()(const eServiceReference &a, const eServiceReference &b)
	{
		return m_list->compareLessEqual(a, b);
	}
};
#endif

class iServiceOfflineOperations: public iObject
{
#ifdef SWIG
	iServiceOfflineOperations();
	~iServiceOfflineOperations();
#endif
public:
		/* to delete a service, forever. */
	virtual RESULT deleteFromDisk(int simulate=1)=0;
	
		/* for transferring a service... */
	virtual SWIG_VOID(RESULT) getListOfFilenames(std::list<std::string> &SWIG_OUTPUT)=0;
	
		// TODO: additional stuff, like a conversion interface?
};

TEMPLATE_TYPEDEF(ePtr<iServiceOfflineOperations>, iServiceOfflineOperationsPtr);

class iServiceHandler: public iObject
{
#ifdef SWIG
	iServiceHandler();
	~iServiceHandler();
#endif
public:
	virtual SWIG_VOID(RESULT) play(const eServiceReference &, ePtr<iPlayableService> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) record(const eServiceReference &, ePtr<iRecordableService> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) list(const eServiceReference &, ePtr<iListableService> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) info(const eServiceReference &, ePtr<iStaticServiceInformation> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &SWIG_OUTPUT)=0;
};

TEMPLATE_TYPEDEF(ePtr<iServiceHandler>, iServiceHandlerPtr);

#endif
