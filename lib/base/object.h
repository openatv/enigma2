#ifndef __base_object_h
#define __base_object_h

#include <assert.h>

// #define OBJECT_DEBUG

#include <lib/base/smartptr.h>
#ifdef OBJECT_DEBUG
#include <lib/base/eerror.h>
#endif

typedef int RESULT;

class iObject
{
private:
		/* we don't allow the default operator here, as it would break the refcount. */
	void operator=(const iObject &);
protected:
	virtual ~iObject() { }
public:
	virtual void AddRef()=0;
	virtual void Release()=0;
};

class oRefCount
{
	int ref;
public:
	oRefCount(): ref(0) { }
	operator int&() { return ref; }
	~oRefCount() { 
#ifdef OBJECT_DEBUG
		if (ref) eDebug("OBJECT_DEBUG FATAL: %p has %d references!", this, ref); else eDebug("OBJECT_DEBUG refcount ok! (%p)", this); 
#endif
	}
};

#ifndef SWIG
#define DECLARE_REF(x) private: oRefCount ref; public: void AddRef(); void Release();
#ifdef OBJECT_DEBUG
extern int object_total_remaining;
#define DEFINE_REF(c) void c::AddRef() { ++object_total_remaining; ++ref; eDebug("OBJECT_DEBUG " #c "+%p now %d", this, (int)ref); } void c::Release() { --object_total_remaining; eDebug("OBJECT_DEBUG " #c "-%p now %d", this, ref-1); if (!--ref) delete this; }
#else
#define DEFINE_REF(c) void c::AddRef() { ++ref; } void c::Release() { if (!--ref) delete this; }
#endif
#else
#define DECLARE_REF(x) private: void AddRef(); void Release();
#endif

#ifdef SWIG
class Object
{
};
#endif

#endif
