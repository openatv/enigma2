#ifndef __lib_dvb_iservice_h
#define __lib_dvb_iservice_h

#include <lib/python/swig.h>
#include <lib/python/python.h>
#include <lib/base/object.h>
#include <string>
#include <connection.h>
#include <list>
#include <vector>

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
		idUser=0x1000,
		idServiceMP3=0x1001
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
		isMarker=64,			// Marker
		isGroup=128,			// is a group of services
		isNumberedMarker=256, //use together with isMarker, to force the marker to be numbered
		isInvisible=512 // use to make services or markers in a list invisable
	};
	int flags; // flags will NOT be compared.

	inline int getSortKey() const { return (flags & hasSortKey) ? data[3] : ((flags & sort1) ? 1 : 0); }

#ifndef SWIG
	int data[8];
	std::string path;
#endif
	std::string getPath() const { return path; }
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
	int number;
#endif
	std::string getName() const { return name; }
	void setName( const std::string &n ) { name=n; }
	int getChannelNum() const { return number; }
	void setChannelNum(const int n) { number = n; }

	eServiceReference()
		: type(idInvalid), flags(0)
	{
		memset(data, 0, sizeof(data));
		number = 0;
	}
#ifndef SWIG
	eServiceReference(int type, int flags)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		number = 0;
	}
	eServiceReference(int type, int flags, int data0)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		data[0]=data0;
		number = 0;
	}
	eServiceReference(int type, int flags, int data0, int data1)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		data[0]=data0;
		data[1]=data1;
		number = 0;
	}
	eServiceReference(int type, int flags, int data0, int data1, int data2)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		data[0]=data0;
		data[1]=data1;
		data[2]=data2;
		number = 0;
	}
	eServiceReference(int type, int flags, int data0, int data1, int data2, int data3)
		: type(type), flags(flags)
	{
		memset(data, 0, sizeof(data));
		data[0]=data0;
		data[1]=data1;
		data[2]=data2;
		data[3]=data3;
		number = 0;
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
		number = 0;
	}
	operator bool() const
	{
		return valid();
	}
#endif
	eServiceReference(int type, int flags, const std::string &path)
		: type(type), flags(flags), path(path)
	{
		memset(data, 0, sizeof(data));
	}
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

	int valid() const
	{
		return type != idInvalid;
	}
};

SWIG_ALLOW_OUTPUT_SIMPLE(eServiceReference);

extern PyObject *New_eServiceReference(const eServiceReference &ref); // defined in enigma_python.i

#ifndef SWIG
#ifdef PYTHON_REFCOUNT_DEBUG
inline ePyObject Impl_New_eServiceReference(const char* file, int line, const eServiceReference &ref)
{
	return ePyObject(New_eServiceReference(ref), file, line);
}
#define NEW_eServiceReference(ref) Impl_New_eServiceReference(__FILE__, __LINE__, ref)
#else
inline ePyObject Impl_New_eServiceReference(const eServiceReference &ref)
{
	return New_eServiceReference(ref);
}
#define NEW_eServiceReference(ref) Impl_New_eServiceReference(ref)
#endif
#endif // SWIG

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

class eServiceEvent;
class iDVBTransponderData;

class iServiceInfoContainer: public iObject
{
public:
	virtual int getInteger(unsigned int index) const { return 0; }
	virtual std::string getString(unsigned int index) const { return ""; }
	virtual double getDouble(unsigned int index) const { return 0.0; }
	virtual unsigned char *getBuffer(unsigned int &size) const { return NULL; }
};

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
	virtual int isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate=false);

	virtual int getInfo(const eServiceReference &ref, int w);
	virtual std::string getInfoString(const eServiceReference &ref,int w);
	virtual ePtr<iServiceInfoContainer> getInfoObject(int w);
	virtual ePtr<iDVBTransponderData> getTransponderData(const eServiceReference &ref);
	virtual long long getFileSize(const eServiceReference &ref);
	virtual bool isCrypted();

	virtual int setInfo(const eServiceReference &ref, int w, int v);
	virtual int setInfoString(const eServiceReference &ref, int w, const char *v);
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iStaticServiceInformation>, iStaticServiceInformationPtr);

class iServiceInformation_ENUMS
{
#ifdef SWIG
	iServiceInformation_ENUMS();
	~iServiceInformation_ENUMS();
#endif
public:
	enum {
		sIsCrypted, 		/* is encrypted (no indication if decrypt was possible) */
		sAspect,    		/* aspect ratio: 0=4:3, 1=16:9, 2=whatever we need */
		sFrameRate,			/* frame rate */
		sProgressive,		/* 0 = interlaced, 1 = progressive */
		sIsMultichannel, 	/* multichannel *available* (probably not selected) */

			/* "user serviceable info" - they are not reliable. Don't use them for anything except the service menu!
			   that's also the reason why they are so globally defined.
			   again - if somebody EVER tries to use this information for anything else than simply displaying it,
			   i will change this to return a user-readable text like "zero x zero three three" (and change the
			   exact spelling in every version) to stop that! */

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
		sTimeCreate, 		/* unix time or string */
		sFileSize,

		sCAIDs,
		sCAIDPIDs,
		sVideoType, 		/* MPEG2 MPEG4 */

		sTags,  			/* space seperated list of tags */

		sDVBState, 			/* states as defined in pmt handler (as events there) */

		sVideoHeight,
		sVideoWidth,

		sTransponderData, 	/* transponderdata as python dict */

		sCurrentChapter,
		sCurrentTitle,
		sTotalChapters,
		sTotalTitles,

		sTagTitle,
		sTagTitleSortname,
		sTagArtist,
		sTagArtistSortname,
		sTagAlbum,
		sTagAlbumSortname,
		sTagComposer,
		sTagDate,
		sTagGenre,
		sTagComment,
		sTagExtendedComment,
		sTagTrackNumber,
		sTagTrackCount,
		sTagAlbumVolumeNumber,
		sTagAlbumVolumeCount,
		sTagLocation,
		sTagHomepage,
		sTagDescription,
		sTagVersion,
		sTagISRC,
		sTagOrganization,
		sTagCopyright,
		sTagCopyrightURI,
		sTagContact,
		sTagLicense,
		sTagLicenseURI,
		sTagPerformer,
		sTagCodec,
		sTagVideoCodec,
		sTagAudioCodec,
		sTagBitrate,
		sTagNominalBitrate,
		sTagMinimumBitrate,
		sTagMaximumBitrate,
		sTagSerial,
		sTagEncoder,
		sTagEncoderVersion,
		sTagTrackGain,
		sTagTrackPeak,
		sTagAlbumGain,
		sTagAlbumPeak,
		sTagReferenceLevel,
		sTagLanguageCode,
		sTagImage,
		sTagPreviewImage,
		sTagAttachment,
		sTagBeatsPerMinute,
		sTagKeywords,
		sTagCRC,
		sTagChannelMode,

		sTransferBPS,

		sHBBTVUrl,
		sLiveStreamDemuxId,
		sBuffer,

		sUser = 0x100
	};
	enum {
		resNA = -1,
		resIsString = -2,
		resIsPyObject = -3
	};
};

/* some words to structs like struct iServiceInformation_ENUMS
For some classes we need in python just the SmartPointer Variants.
So we prevent building wrapper classes for the non smart pointer classes with the SWIG_IGNORE makro.
But now we have the problem that swig do not export enums for smart pointer classes (i dont know why).
So we move all enum's to own classes (with _ENUMS as name ending) and let our real
class inherit from the *_ENUMS class. This *_ENUMS classes are normally exportet via swig to python.
But in the python code we doesn't like to write iServiceInformation_ENUMS.sVideoType....
we like to write iServiceInformation.sVideoType.
So until swig have no Solution for this Problem we call in lib/python/Makefile.am a python script named
enigma_py_patcher.py to remove the "_ENUMS" strings in enigma.py at all needed locations. */

class iServiceInformation: public iServiceInformation_ENUMS, public iObject
{
#ifdef SWIG
	iServiceInformation();
	~iServiceInformation();
#endif
public:
	virtual SWIG_VOID(RESULT) getName(std::string &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) getEvent(ePtr<eServiceEvent> &SWIG_OUTPUT, int nownext);

	virtual int getInfo(int w);
	virtual std::string getInfoString(int w);
	virtual ePtr<iServiceInfoContainer> getInfoObject(int w);
	virtual ePtr<iDVBTransponderData> getTransponderData();
	virtual void getAITApplications(std::map<int, std::string> &aitlist) {};
	virtual void getCaIds(std::vector<int> &caids, std::vector<int> &ecmpids);
	virtual long long getFileSize();

	virtual int setInfo(int w, int v);
	virtual int setInfoString(int w, const char *v);
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iServiceInformation>, iServiceInformationPtr);

class iFrontendInformation_ENUMS
{
#ifdef SWIG
	iFrontendInformation_ENUMS();
	~iFrontendInformation_ENUMS();
#endif
public:
	enum {
		bitErrorRate,
		signalPower,
		signalQuality,
		lockState,
		syncState,
		frontendNumber,
		signalQualitydB,
		frontendStatus,
		snrValue,
		frequency,
	};
};

class iDVBFrontendData;
class iDVBFrontendStatus;
class iDVBTransponderData;

class iFrontendInformation: public iFrontendInformation_ENUMS, public iObject
{
#ifdef SWIG
	iFrontendInformation();
	~iFrontendInformation();
#endif
public:
	virtual int getFrontendInfo(int w)=0;
	virtual ePtr<iDVBFrontendData> getFrontendData()=0;
	virtual ePtr<iDVBFrontendStatus> getFrontendStatus()=0;
	virtual ePtr<iDVBTransponderData> getTransponderData(bool original)=0;
	void getAll() {}
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iFrontendInformation>, iFrontendInformationPtr);

SWIG_IGNORE(iPauseableService);
class iPauseableService: public iObject
{
#ifdef SWIG
	iPausableService();
	~iPausableService();
#endif
public:

		/* this will set the *state* directly. So just call a SINGLE function of those at a time. */
	virtual RESULT pause()=0;
	virtual RESULT unpause()=0;

		/* hm. */
	virtual RESULT setSlowMotion(int ratio=0)=0;
	virtual RESULT setFastForward(int ratio=0)=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iPauseableService>, iPauseableServicePtr);

class iSeekableService_ENUMS
{
#ifdef SWIG
	iSeekableService_ENUMS();
	~iSeekableService_ENUMS();
#endif
public:
	enum { dirForward = +1, dirBackward = -1 };
};

SWIG_IGNORE(iSeekableService);
class iSeekableService: public iSeekableService_ENUMS, public iObject
{
#ifdef SWIG
	iSeekableService();
	~iSeekableService();
#endif
public:
	virtual RESULT getLength(pts_t &SWIG_OUTPUT)=0;
	virtual RESULT seekTo(pts_t to)=0;
	virtual RESULT seekRelative(int direction, pts_t to)=0;
	virtual RESULT getPlayPosition(pts_t &SWIG_OUTPUT)=0;
		/* if you want to do several seeks in a row, you can enable the trickmode.
		   audio will be switched off, sync will be disabled etc. */
	virtual RESULT setTrickmode(int trick=0)=0;
	virtual RESULT isCurrentlySeekable()=0;
	virtual RESULT seekChapter(int) { return -1; }
	virtual RESULT seekTitle(int) { return -1; }
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iSeekableService>, iSeekableServicePtr);

struct iAudioTrackInfo
{
#ifndef SWIG
	std::string m_description;
	std::string m_language; /* iso639 */
	int m_pid; /* for association with the stream. */
#endif
	std::string getDescription() { return m_description; }
	std::string getLanguage() { return m_language; }
	int getPID() { return m_pid; }
};
SWIG_ALLOW_OUTPUT_SIMPLE(iAudioTrackInfo);

SWIG_IGNORE(iAudioTrackSelection);
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
	virtual int getCurrentTrack()=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iAudioTrackSelection>, iAudioTrackSelectionPtr);

class iAudioChannelSelection_ENUMS
{
#ifdef SWIG
	iAudioChannelSelection_ENUMS();
	~iAudioChannelSelection_ENUMS();
#endif
public:
	enum { LEFT, STEREO, RIGHT };
};

SWIG_IGNORE(iAudioChannelSelection);
class iAudioChannelSelection: public iAudioChannelSelection_ENUMS, public iObject
{
#ifdef SWIG
	iAudioChannelSelection();
	~iAudioChannelSelection();
#endif
public:
	virtual int getCurrentChannel()=0;
	virtual RESULT selectChannel(int i)=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iAudioChannelSelection>, iAudioChannelSelectionPtr);

SWIG_IGNORE(iAudioDelay);
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
SWIG_TEMPLATE_TYPEDEF(ePtr<iAudioDelay>, iAudioDelayPtr);

class iRdsDecoder_ENUMS
{
#ifdef SWIG
	iRdsDecoder_ENUMS();
	~iRdsDecoder_ENUMS();
#endif
public:
	enum { RadioText, RtpText };
};

SWIG_IGNORE(iRdsDecoder);
class iRdsDecoder: public iObject, public iRdsDecoder_ENUMS
{
#ifdef SWIG
	iRdsDecoder();
	~iRdsDecoder();
#endif
public:
	virtual std::string getText(int x=RadioText)=0;
	virtual void showRassSlidePicture()=0;
	virtual void showRassInteractivePic(int page, int subpage)=0;
	virtual SWIG_PYOBJECT(ePyObject) getRassInteractiveMask()=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iRdsDecoder>, iRdsDecoderPtr);

SWIG_IGNORE(iSubserviceList);
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
SWIG_TEMPLATE_TYPEDEF(ePtr<iSubserviceList>, iSubserviceListPtr);

SWIG_IGNORE(iTimeshiftService);
class iTimeshiftService: public iObject
{
#ifdef SWIG
	iTimeshiftService();
	~iTimeshiftService();
#endif
public:
	virtual RESULT startTimeshift()=0;
	virtual RESULT stopTimeshift(bool swToLive=true)=0;
	virtual RESULT setNextPlaybackFile(const char *fn)=0; // not needed by our internal timeshift.. but external plugin...

	virtual int isTimeshiftActive()=0;
	virtual int isTimeshiftEnabled()=0;
			/* this essentially seeks to the relative end of the timeshift buffer */
	virtual RESULT activateTimeshift()=0;
	virtual RESULT saveTimeshiftFile()=0;
	virtual std::string getTimeshiftFilename()=0;
	virtual void switchToLive()=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iTimeshiftService>, iTimeshiftServicePtr);

	/* not related to eCueSheet */

class iCueSheet_ENUMS
{
#ifdef SWIG
	iCueSheet_ENUMS();
	~iCueSheet_ENUMS();
#endif
public:
	enum { cutIn = 0, cutOut = 1, cutMark = 2 };
};

SWIG_IGNORE(iCueSheet);
class iCueSheet: public iCueSheet_ENUMS, public iObject
{
#ifdef SWIG
	iCueSheet();
	~iCueSheet();
#endif
public:
	/* returns a list of (pts, what)-tuples */
	virtual PyObject *getCutList() = 0;
	virtual void setCutList(SWIG_PYOBJECT(ePyObject) list) = 0;
	virtual void setCutListEnable(int enable) = 0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iCueSheet>, iCueSheetPtr);

class PyList;

class eDVBTeletextSubtitlePage;
class eDVBSubtitlePage;
struct ePangoSubtitlePage;
class eRect;
struct gRegion;
struct gPixmap;

SWIG_IGNORE(iSubtitleUser);
class iSubtitleUser
{
public:
	virtual void setPage(const eDVBTeletextSubtitlePage &p) = 0;
	virtual void setPage(const eDVBSubtitlePage &p) = 0;
	virtual void setPage(const ePangoSubtitlePage &p) = 0;
	virtual void setPixmap(ePtr<gPixmap> &pixmap, gRegion changed, eRect dest) = 0;
	virtual void destroy() = 0;
};

class iSubtitleOutput: public iObject
{
public:
	struct SubtitleTrack
	{
		int type;
		int pid;
		int page_number;
		int magazine_number;
		std::string language_code;
	};

	virtual RESULT enableSubtitles(iSubtitleUser *user, SubtitleTrack &track) = 0;
	virtual RESULT disableSubtitles() = 0;
	virtual RESULT getCachedSubtitle(SubtitleTrack &track) = 0;
	virtual RESULT getSubtitleList(std::vector<SubtitleTrack> &subtitlelist) = 0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iSubtitleOutput>, iSubtitleOutputPtr);

SWIG_IGNORE(iMutableServiceList);
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
	virtual RESULT removeService(eServiceReference &ref, bool renameBouquet=true)=0;
		/* moves a service in a list, only if list suppports a specific sort method. */
		/* pos is the new, absolute position from 0..size-1 */
	virtual RESULT moveService(eServiceReference &ref, int pos)=0;
		/* set name of list, for bouquets this is the visible bouquet name */
	virtual RESULT setListName(const std::string &name)=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iMutableServiceList>, iMutableServiceListPtr);

SWIG_IGNORE(iListableService);
class iListableService: public iObject
{
#ifdef SWIG
	iListableService();
	~iListableService();
#endif
public:
#ifndef SWIG
		/* legacy interface: get a list */
	virtual RESULT getContent(std::list<eServiceReference> &list, bool sorted=false)=0;
#endif
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
SWIG_TEMPLATE_TYPEDEF(ePtr<iListableService>, iListableServicePtr);

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

SWIG_IGNORE(iServiceOfflineOperations);
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

		/* a blocking call to reindex a file */
	virtual int reindex() = 0;

		// TODO: additional stuff, like a conversion interface?
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iServiceOfflineOperations>, iServiceOfflineOperationsPtr);

class iStreamData: public iObject
{
public:
	virtual SWIG_VOID(RESULT) getAllPids(std::vector<int> &result) const = 0;
	virtual SWIG_VOID(RESULT) getVideoPids(std::vector<int> &result) const = 0;
	virtual SWIG_VOID(RESULT) getAudioPids(std::vector<int> &result) const = 0;
	virtual SWIG_VOID(RESULT) getSubtitlePids(std::vector<int> &result) const = 0;
	virtual SWIG_VOID(RESULT) getPmtPid(int &result) const = 0;
	virtual SWIG_VOID(RESULT) getPatPid(int &result) const = 0;
	virtual SWIG_VOID(RESULT) getPcrPid(int &result) const = 0;
	virtual SWIG_VOID(RESULT) getTxtPid(int &result) const = 0;
	virtual SWIG_VOID(RESULT) getServiceId(int &result) const = 0;
	virtual SWIG_VOID(RESULT) getAdapterId(int &result) const = 0;
	virtual SWIG_VOID(RESULT) getDemuxId(int &result) const = 0;
	virtual SWIG_VOID(RESULT) getCaIds(std::vector<int> &caids, std::vector<int> &ecmpids) const = 0;
};

class iStreamableService: public iObject
{
#ifdef SWIG
	iStreamableService();
	~iStreamableService();
#endif
public:
	virtual ePtr<iStreamData> getStreamingData() = 0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iStreamableService>, iStreamableServicePtr);

class iStreamBufferInfo: public iObject
{
public:
	virtual int getBufferPercentage() const = 0;
	virtual int getAverageInputRate() const = 0;
	virtual int getAverageOutputRate() const = 0;
	virtual int getBufferSpace() const = 0;
	virtual int getBufferSize() const = 0;
};

class iStreamedService: public iObject
{
#ifdef SWIG
	iStreamedService();
	~iStreamedService();
#endif
public:
	virtual ePtr<iStreamBufferInfo> getBufferCharge()=0;
	virtual int setBufferSize(int size)=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iStreamedService>, iStreamedServicePtr);

class iServiceKeys_ENUMS
{
#ifdef SWIG
	iServiceKeys_ENUMS();
	~iServiceKeys_ENUMS();
#endif
public:
	enum {
		keyLeft,
		keyRight,
		keyUp,
		keyDown,
		keyOk,
		keyUser = 0x100
	};
};

SWIG_IGNORE(iServiceKeys);
class iServiceKeys: public iServiceKeys_ENUMS, public iObject
{
#ifdef SWIG
	iServiceKeys();
	~iServiceKeys();
#endif
public:
	virtual SWIG_VOID(RESULT) keyPressed(int key)=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iServiceKeys>, iServiceKeysPtr);

class iPlayableService_ENUMS
{
#ifdef SWIG
	iPlayableService_ENUMS();
	~iPlayableService_ENUMS();
#endif
public:
	enum {
			/* these first two events are magical, and should only
			   be generated if you know what you're doing. */
		evStart,
		evEnd,

		evTunedIn,
		evTuneFailed,

			/* when iServiceInformation is implemented:*/
		evUpdatedEventInfo,
		evUpdatedInfo,
		evNewProgramInfo,

			/* when seek() is implemented: */
		evSeekableStatusChanged, /* for example when timeshifting */

		evEOF,
		evSOF, /* bounced against start of file (when seeking backwards) */

			/* when cueSheet is implemented */
		evCuesheetChanged,

			/* when rdsDecoder is implemented */
		evUpdatedRadioText,
		evUpdatedRtpText,

			/* Radio Screenshow Support */
		evUpdatedRassSlidePic,
		evUpdatedRassInteractivePicMask,

		evVideoSizeChanged,
		evVideoFramerateChanged,
		evVideoProgressiveChanged,

		evBuffering,
		evGstreamerPlayStarted,

		evStopped,

		evHBBTVInfo,

		evUser = 0x100
	};
};

SWIG_IGNORE(iPlayableService);
class iPlayableService: public iPlayableService_ENUMS, public iObject
{
#ifdef SWIG
	iPlayableService();
	~iPlaybleService();
#endif
	friend class iServiceHandler;
public:
#ifndef SWIG
	virtual RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection)=0;
#endif
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
	virtual SWIG_VOID(RESULT) rdsDecoder(ePtr<iRdsDecoder> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) stream(ePtr<iStreamableService> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) streamed(ePtr<iStreamedService> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) keys(ePtr<iServiceKeys> &SWIG_OUTPUT)=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iPlayableService>, iPlayableServicePtr);

class iRecordableService_ENUMS
{
#ifdef SWIG
	iRecordableService_ENUMS();
	~iRecordableService_ENUMS();
#endif
public:
	enum {
		evStart,
		evEnd,
		evTunedIn,
		evTuneFailed,
		evRecordRunning,
		evRecordStopped,
		evNewProgramInfo,
		evRecordFailed,
		evRecordWriteError,
		evNewEventInfo,
		evRecordAborted,
	};
	enum {
		NoError=0,
		errOpenRecordFile=-1,
		errNoDemuxAvailable=-2,
		errNoTsRecorderAvailable=-3,
		errDiskFull=-4,
		errTuneFailed=-255,
		errMisconfiguration = -256,
		errNoResources = -257,
	};
};

SWIG_IGNORE(iRecordableService);
class iRecordableService: public iRecordableService_ENUMS, public iObject
{
#ifdef SWIG
	iRecordableService();
	~iRecordableService();
#endif
public:
#ifndef SWIG
	virtual RESULT connectEvent(const Slot2<void,iRecordableService*,int> &event, ePtr<eConnection> &connection)=0;
#endif
	virtual SWIG_VOID(RESULT) getError(int &SWIG_OUTPUT)=0;
	virtual RESULT prepare(const char *filename, time_t begTime=-1, time_t endTime=-1, int eit_event_id=-1, const char *name=0, const char *descr=0, const char *tags=0, bool descramble = true, bool recordecm = false)=0;
	virtual RESULT prepareStreaming(bool descramble = true, bool includeecm = false)=0;
	virtual RESULT start(bool simulate=false)=0;
	virtual RESULT stop()=0;
	virtual SWIG_VOID(RESULT) frontendInfo(ePtr<iFrontendInformation> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) stream(ePtr<iStreamableService> &SWIG_OUTPUT)=0;
	virtual SWIG_VOID(RESULT) subServices(ePtr<iSubserviceList> &SWIG_OUTPUT)=0;
};
SWIG_TEMPLATE_TYPEDEF(ePtr<iRecordableService>, iRecordableServicePtr);

extern PyObject *New_iRecordableServicePtr(const ePtr<iRecordableService> &ref); // defined in enigma_python.i

inline PyObject *PyFrom(ePtr<iRecordableService> &c)
{
	return New_iRecordableServicePtr(c);
}

#ifndef SWIG
#ifdef PYTHON_REFCOUNT_DEBUG
inline ePyObject Impl_New_iRecordableServicePtr(const char* file, int line, const ePtr<iRecordableService> &ptr)
{
	return ePyObject(New_iRecordableServicePtr(ptr), file, line);
}
#define NEW_iRecordableServicePtr(ptr) Impl_New_iRecordableServicePtr(__FILE__, __LINE__, ptr)
#else
inline ePyObject Impl_New_iRecordableServicePtr(const ePtr<iRecordableService> &ptr)
{
	return New_iRecordableServicePtr(ptr);
}
#define NEW_iRecordableServicePtr(ptr) Impl_New_iRecordableServicePtr(ptr)
#endif
#endif // SWIG

SWIG_IGNORE(iServiceHandler);
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
SWIG_TEMPLATE_TYPEDEF(ePtr<iServiceHandler>, iServiceHandlerPtr);

#endif
