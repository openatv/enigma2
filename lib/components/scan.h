#ifndef __lib_components_scan_h
#define __lib_components_scan_h

#include <lib/base/object.h>

class eDVBScan;

class eComponentScan: public Object, public iObject
{
DECLARE_REF(eComponentScan);
private:
	void scanEvent(int event);
	ePtr<eConnection> m_scan_event_connection;
	ePtr<eDVBScan> m_scan;
	
	int m_done, m_failed;
public:
	eComponentScan();
	~eComponentScan();
	
	PSignal0<void> statusChanged;
	
		/* progress between 0 and 100 */
	int getProgress();
	
		/* get number of services */
	int getNumServices();
	
		/* true when done. */
	int isDone();
	
	int start();
};

#endif
