#ifndef __base_object_h
#define __base_object_h

#include <assert.h>
#include <lib/base/smartptr.h>
#include <lib/base/elock.h>

//#define OBJECT_DEBUG

#include <lib/base/eerror.h>

typedef int RESULT;

class iObject
{
private:
		/* we don't allow the default operator here, as it would break the refcount. */
	void operator=(const iObject &);
protected:
	void operator delete(void *p) { ::operator delete(p); }
	virtual ~iObject() { }
#ifdef SWIG
	virtual void AddRef()=0;
	virtual void Release()=0;
#endif
public:
#ifndef SWIG
	virtual void AddRef()=0;
	virtual void Release()=0;
#endif
};

#ifndef SWIG

/* atomic inc/dec, borrowed from boost::smart_ptr */
#if defined(__mips__)
inline void atomic_increment(int * pw)
{
	/* ++*pw; */

	int tmp;

	__asm__ __volatile__
	(
		"0:\n\t"
		".set push\n\t"
		".set mips2\n\t"
		"ll %0, %1\n\t"
		"addiu %0, 1\n\t"
		"sc %0, %1\n\t"
		".set pop\n\t"
		"beqz %0, 0b":
		"=&r"(tmp), "=m"(*pw):
		"m"(*pw)
	);
}

inline int atomic_decrement(int * pw)
{
	/* return --*pw; */

	int rv, tmp;

	__asm__ __volatile__
	(
		"0:\n\t"
		".set push\n\t"
		".set mips2\n\t"
		"ll %1, %2\n\t"
		"addiu %0, %1, -1\n\t"
		"sc %0, %2\n\t"
		".set pop\n\t"
		"beqz %0, 0b\n\t"
		"addiu %0, %1, -1":
		"=&r"(rv), "=&r"(tmp), "=m"(*pw):
		"m"(*pw):
		"memory"
	);
	return rv;
}
#elif defined(__ppc__) || defined(__powerpc__)
inline void atomic_increment(int * pw)
{
	/* ++*pw; */

	int tmp;

	__asm__
	(
		"0:\n\t"
		"lwarx %1, 0, %2\n\t"
		"addi %1, %1, 1\n\t"
		"stwcx. %1, 0, %2\n\t"
		"bne- 0b":

		"=m"(*pw), "=&b"(tmp):
		"r"(pw), "m"(*pw):
		"cc"
	);
}

inline int atomic_decrement(int * pw)
{
	/* return --*pw; */

	int rv;

	__asm__ __volatile__
	(
		"sync\n\t"
		"0:\n\t"
		"lwarx %1, 0, %2\n\t"
		"addi %1, %1, -1\n\t"
		"stwcx. %1, 0, %2\n\t"
		"bne- 0b\n\t"
		"isync":

		"=m"(*pw), "=&b"(rv):
		"r"(pw), "m"(*pw):
		"memory", "cc"
	);
	return rv;
}
#elif defined(__i386__) || defined(__x86_64__)
inline int atomic_exchange_and_add(int * pw, int dv)
{
	/* 
	 * int r = *pw;
	 * *pw += dv;
	 * return r;
	 */

	int r;

	__asm__ __volatile__
	(
		"lock\n\t"
		"xadd %1, %0":
		"=m"(*pw), "=r"(r): // outputs (%0, %1)
		"m"(*pw), "1"(dv): // inputs (%2, %3 == %1)
		"memory", "cc" // clobbers
	);
	return r;
}

inline void atomic_increment(int * pw)
{
	/* atomic_exchange_and_add(pw, 1); */

	__asm__
	(
		"lock\n\t"
		"incl %0":
		"=m"(*pw): // output (%0)
		"m"(*pw): // input (%1)
		"cc" // clobbers
	);
}

inline int atomic_decrement(int * pw)
{
	return atomic_exchange_and_add(pw, -1) - 1;
}
#endif

	struct oRefCount
	{
		int count;
		oRefCount(): count(0) { }
		operator int&() { return count; }
#ifdef OBJECT_DEBUG
		~oRefCount()
		{ 
			if (count)
				eDebug("OBJECT_DEBUG FATAL: %p has %d references!", this, count);
			else
				eDebug("OBJECT_DEBUG refcount ok! (%p)", this); 
		}
#endif
	};

	#if defined(OBJECT_DEBUG)
		extern int object_total_remaining;
		#define DECLARE_REF(x) 			\
			public: void AddRef(); 		\
					void Release();		\
			private:oRefCount ref; 		\
					eSingleLock ref_lock;
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
				eSingleLocker l(ref_lock); \
				--object_total_remaining; \
				--ref; \
				eDebug("OBJECT_DEBUG " #c "-%p now %d", this, (int)ref); \
				if (!ref) \
					delete this; \
			}
	#elif defined(__mips__) || defined(__ppc__) || defined(__powerpc__) || defined(__i386__) || defined(__x86_64__)
		#define DECLARE_REF(x) 			\
			public: void AddRef(); 		\
					void Release();		\
			private: oRefCount ref; 
		#define DEFINE_REF(c) \
			void c::AddRef() \
			{ \
				atomic_increment(&ref.count); \
			} \
			void c::Release() \
			{ \
				if (!atomic_decrement(&ref.count)) \
					delete this; \
			}
	#else
		#warning use non optimized implementation of refcounting.
		#define DECLARE_REF(x) 			\
			public: void AddRef(); 		\
					void Release();		\
			private:oRefCount ref; 	\
					eSingleLock ref_lock;
		#define DEFINE_REF(c) \
			void c::AddRef() \
			{ \
				eSingleLocker l(ref_lock); \
				++ref; \
			} \
			void c::Release() \
	 		{ \
				eSingleLocker l(ref_lock); \
				--ref; \
				if (!ref) \
					delete this; \
			}
	#endif
#else  // SWIG
	#define DECLARE_REF(x) \
		private: \
			void AddRef(); \
			void Release();
#endif  // SWIG

#endif  // __base_object_h
