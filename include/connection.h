#ifndef __connection_h
#define __connection_h

#include <libsig_comp.h>
#include <lib/base/object.h>

class eConnection: public virtual iObject, public Connection
{
	int ref;
public:
DEFINE_REF(eConnection);
public:
	eConnection(const Connection &conn): Connection(conn), ref(0) { };
	virtual ~eConnection() { disconnect(); }
};

#endif
