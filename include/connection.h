#ifndef __connection_h
#define __connection_h

#include <libsig_comp.h>
#include <lib/base/object.h>

class eConnection: public virtual iObject, public Connection
{
	int ref;
	ePtr<iObject> m_owner;
public:
DEFINE_REF(eConnection);
public:
	eConnection(iObject *owner, const Connection &conn): Connection(conn), ref(0), m_owner(owner) { };
	virtual ~eConnection() { disconnect(); }
};

#endif
