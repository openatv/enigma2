#ifndef __base_object_h
#define __base_object_h

#include <assert.h>

// #define OBJECT_DEBUG

#include <lib/base/smartptr.h>
#ifdef OBJECT_DEBUG
#include <lib/base/eerror.h>
#endif
#include <lib/base/elock.h>

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
	#if defined(__mips__)
		#define DECLARE_REF(x) 			\
			private: oRefCount ref; 	\
			public: void AddRef(); 		\
					void Release();
		#define DEFINE_REF(c) \
			void c::AddRef() \
			{ \
				unsigned long temp; \
				__asm__ __volatile__( \
				"		.set	mips3		\n" \
				"1:		ll		%0, %1		\n" \
				"		.set	mips0		\n" \
				"		addu	%0, 1		\n" \
				"		.set	mips3		\n" \
				"		sc		%0, %1		\n" \
				"		.set	mips0		\n" \
				"		beqz	%0, 1b		\n" \
				: "=&r" (temp), "=m" ((int)ref) \
				: "m" ((int)ref) \
				: "memory"); \
			} \
			void c::Release() \
			{ \
				unsigned long temp; \
				__asm__ __volatile__( \
				"		.set	mips3		\n" \
				"1:		ll		%0, %1		\n" \
				"		.set	mips0		\n" \
				"		subu	%0, 1		\n" \
				"		.set	mips3		\n" \
				"		sc		%0, %1		\n" \
				"		.set	mips0		\n" \
				"		beqz	%0, 1b		\n" \
				: "=&r" (temp), "=m" ((int)ref) \
				: "m" ((int)ref) \
				: "memory"); \
				if (!ref) \
					delete this; \
			}
	#else
		#define DECLARE_REF(x) 			\
			private:oRefCount ref; 	\
					eSingleLock ref_lock; \
			public: void AddRef(); 		\
					void Release();
		#ifdef OBJECT_DEBUG
			extern int object_total_remaining;
			#define DEFINE_REF(c) \
				void c::AddRef() \
				{ \
					eSingleLocker l(ref_lock); \
					++object_total_remaining; \
					++ref; \
					eDebug("OBJECT_DEBUG " #c "+%p now %d", this, (int)ref); \
				} \
				void c::Release() \
				{ \
					{ \
						eSingleLocker l(ref_lock); \
						--object_total_remaining; \
						--ref; \
						eDebug("OBJECT_DEBUG " #c "-%p now %d", this, ref); \
					} \
					if (!ref) \
						delete this; \
				}
				#error fix locking for debug
		#else
			#define DEFINE_REF(c) \
				void c::AddRef() \
				{ \
					eSingleLocker l(ref_lock); \
					++ref; \
				} \
				void c::Release() \
				{ \
					{ \
						eSingleLocker l(ref_lock); \
						--ref; \
					} \
					if (!ref) \
						delete this; \
				}
		#endif
	#endif
#else
	#define DECLARE_REF(x) \
		private: \
			void AddRef(); \
			void Release();
#endif

#ifdef SWIG
class Object
{
};
#endif

#endif
