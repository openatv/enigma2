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
	struct oRefCount
	{
		volatile int count;
		oRefCount(): count(0) { }
		operator volatile int&() { return count; }
		~oRefCount()
		{ 
	#ifdef OBJECT_DEBUG
			if (count)
				eDebug("OBJECT_DEBUG FATAL: %p has %d references!", this, count);
			else
				eDebug("OBJECT_DEBUG refcount ok! (%p)", this); 
	#endif
		}
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
				{ \
					eSingleLocker l(ref_lock); \
					--object_total_remaining; \
					--ref; \
					eDebug("OBJECT_DEBUG " #c "-%p now %d", this, (int)ref); \
				} \
				if (!ref) \
					delete this; \
			}
	#elif defined(__mips__)
		#define DECLARE_REF(x) 			\
			public: void AddRef(); 		\
					void Release();		\
			private: oRefCount ref; 
		#define DEFINE_REF(c) \
			void c::AddRef() \
			{ \
				unsigned long temp; \
				__asm__ __volatile__( \
				"		.set	mips3											\n" \
				"1:		ll		%0, %1	# load counter							\n" \
				"		.set	mips0											\n" \
				"		addu	%0, 1	# increment								\n" \
				"		.set	mips3											\n" \
				"		sc		%0, %1	# try to store, checking for atomicity	\n" \
				"		.set	mips0											\n" \
				"		beqz	%0, 1b	# if not atomic (0), try again			\n" \
				: "=&r" (temp), "=m" (ref.count) \
				: "m" (ref.count) \
				: ); \
			} \
			void c::Release() \
			{ \
				unsigned long temp; \
				__asm__ __volatile__( \
				"		.set	mips3				\n" \
				"1:		ll		%0, %1				\n" \
				"		.set	mips0				\n" \
				"		subu	%0, 1	# decrement	\n" \
				"		.set	mips3				\n" \
				"		sc		%0, %1				\n" \
				"		.set	mips0				\n" \
				"		beqz	%0, 1b				\n" \
				: "=&r" (temp), "=m" (ref.count) \
				: "m" (ref.count) \
				: ); \
				if (!ref) \
					delete this; \
			}
	#elif defined(__ppc__) || defined(__powerpc__)
		#define DECLARE_REF(x) 			\
			public: void AddRef(); 		\
					void Release();		\
			private: oRefCount ref;
		#define DEFINE_REF(c) \
			void c::AddRef() \
			{ \
				int temp; \
				__asm__ __volatile__( \
				"1:		lwarx	%0, 0, %3	\n" \
				"		add		%0, %2, %0	\n" \
				"		dcbt	0, %3		# workaround for PPC405CR Errata\n" \
				"		stwcx.	%0, 0, %3	\n" \
				"		bne-	1b			\n" \
				: "=&r" (temp), "=m" (ref.count) \
				: "r" (1), "r" (&ref.count), "m" (ref.count) \
				: "cc"); \
			} \
			void c::Release() \
			{ \
				int temp; \
				__asm__ __volatile__( \
				"1:		lwarx	%0, 0, %3	\n" \
				"		subf	%0, %2, %0	\n" \
				"		dcbt	0, %3		# workaround for PPC405CR Errata\n" \
				"		stwcx.	%0, 0, %3	\n" \
				"		bne-	1b			\n" \
				: "=&r" (temp), "=m" (ref.count) \
				: "r" (1), "r" (&ref.count), "m" (ref.count) \
				: "cc"); \
				if (!ref) \
					delete this; \
			}
	#elif defined(__i386__) || defined(__x86_64__)
		#define DECLARE_REF(x) 			\
			public: void AddRef(); 		\
					void Release();		\
			private: oRefCount ref;
		#define DEFINE_REF(c) \
			void c::AddRef() \
			{ \
				__asm__ __volatile__( \
				"		lock ; incl	%0	\n" \
				: "=m" (ref.count) \
				: "m" (ref.count)); \
			} \
			void c::Release() \
			{ \
				__asm__ __volatile__( \
				"		lock ; decl	%0	\n" \
				: "=m" (ref.count) \
				: "m" (ref.count)); \
				if (!ref) \
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
				{ \
					eSingleLocker l(ref_lock); \
					--ref; \
				} \
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
