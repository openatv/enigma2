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
};

#define DECLARE_REF private: oRefCount ref; public: void AddRef(); void Release();
#ifdef OBJECT_DEBUG
extern int object_total_remaining;
#define DEFINE_REF(c) void c::AddRef() { ++object_total_remaining; ++ref; eDebug("OBJECT_DEBUG " #c "+%p now %d", this, (int)ref); } void c::Release() { --object_total_remaining; eDebug("OBJECT_DEBUG " #c "-%p now %d", this, ref-1); if (!--ref) delete this; }
#else
#define DEFINE_REF(c) void c::AddRef() { ++ref; } void c::Release() { if (!--ref) delete this; }
#endif

#endif
