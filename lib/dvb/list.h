#ifndef __list_h
#define __list_h

class eDVBTransponderList: iDVBChannelList
{
	DECLARE_REF(eDVBTransponderList);
	std::map<eDVBChannelID, ePtr<iDVBFrontendParameters> > channels;
public:
	virtual RESULT getChannelFrontendData(const eDVBChannelID &id, ePtr<iDVBFrontendParameters> &parm)=0;
};

#endif
