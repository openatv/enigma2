#ifndef __smartptr_h
#define __smartptr_h

#include "object.h"
#include <stdio.h>
#include <string.h>
#include <lib/python/swig.h>

inline void ptrAssert(void *p) { if (!p) *(unsigned long*)0=0; }

template<class T>
class ePtr
{
protected:
	T *ptr;
	char m_ptrStr[sizeof(void*)*2+1];
	void updatePtrStr()
	{
		if (ptr) {
			if (sizeof(void*) > 4)
				sprintf(m_ptrStr, "%llx", (unsigned long long)ptr);
			else
				sprintf(m_ptrStr, "%lx", (unsigned long)ptr);
		}
		else
			strcpy(m_ptrStr, "NIL");
	}
public:
	T &operator*() { return *ptr; }
	ePtr(): ptr(0)
	{
	}
	ePtr(T *c): ptr(c)
	{
		if (c)
			c->AddRef();
		updatePtrStr();
	}
	ePtr(const ePtr &c): ptr(c.ptr)
	{
		if (ptr)
			ptr->AddRef();
		updatePtrStr();
	}
	ePtr &operator=(T *c)
	{
		if (c)
			c->AddRef();
		if (ptr)
			ptr->Release();
		ptr=c;
		updatePtrStr();
		return *this;
	}
	ePtr &operator=(ePtr<T> &c)
	{
		if (c.ptr)
			c.ptr->AddRef();
		if (ptr)
			ptr->Release();
		ptr=c.ptr;
		updatePtrStr();
		return *this;
	}
	~ePtr()
	{
		if (ptr)
			ptr->Release();
	}
	char *getPtrString()
	{
		return m_ptrStr;
	}
#ifndef SWIG
	T* grabRef() { if (!ptr) return 0; ptr->AddRef(); return ptr; }
	T* &ptrref() { ASSERT(!ptr); return ptr; }
	operator bool() const { return !!this->ptr; }
#endif
	T* operator->() const { ptrAssert(ptr); return ptr; }
	operator T*() const { return this->ptr; }
};


template<class T>
class eUsePtr
{
protected:
	T *ptr;
public:
	T &operator*() { return *ptr; }
	eUsePtr(): ptr(0)
	{
	}
	eUsePtr(T *c): ptr(c)
	{
		if (c)
		{
			c->AddRef();
			c->AddUse();
		}
	}
	eUsePtr(const eUsePtr &c)
	{
		ptr=c.ptr;
		if (ptr)
		{
			ptr->AddRef();
			ptr->AddUse();
		}
	}
	eUsePtr &operator=(T *c)
	{
		if (c)
		{
			c->AddRef();
			c->AddUse();
		}
		if (ptr)
		{
			ptr->ReleaseUse();
			ptr->Release();
		}
		ptr=c;
		return *this;
	}
	eUsePtr &operator=(eUsePtr<T> &c)
	{
		if (c.ptr)
		{
			c.ptr->AddRef();
			c.ptr->AddUse();
		}
		if (ptr)
		{
			ptr->ReleaseUse();
			ptr->Release();
		}
		ptr=c.ptr;
		return *this;
	}
	~eUsePtr()
	{
		if (ptr)
		{
			ptr->ReleaseUse();
			ptr->Release();
		}
	}
#ifndef SWIG
	T* grabRef() { if (!ptr) return 0; ptr->AddRef(); ptr->AddUse(); return ptr; }
	T* &ptrref() { ASSERT(!ptr); return ptr; }
#endif
	T* operator->() const { ptrAssert(ptr); return ptr; }
	operator T*() const { return this->ptr; }
};



#ifndef SWIG
template<class T>
class eMutablePtr: public ePtr<T>
{
		/* read doc/iObject about the ePtrHelper */
	template<class T1>
	class ePtrHelper
	{
		T1 *m_obj;
	public:
		inline ePtrHelper(T1 *obj): m_obj(obj)
		{
			m_obj->AddRef();
		}
		inline ~ePtrHelper()
		{
			m_obj->Release();
		}
		inline T1* operator->() { return m_obj; }
	};
protected:
	T *ptr;
public:
	eMutablePtr(): ePtr<T>(0)
	{
	}
	eMutablePtr(T *c): ePtr<T>(c)
	{
	}
	eMutablePtr(const eMutablePtr &c): ePtr<T>(c)
	{
	}
	eMutablePtr &operator=(T *c)
	{
		ePtr<T>::operator=(c);
		return *this;
	}
	ePtrHelper<T> operator->() { ptrAssert(ptr); return ePtrHelper<T>(ptr); }
			/* for const objects, we don't need the helper, as they can't */
			/* be changed outside the program flow. at least this is */
			/* what the compiler assumes, so in case you're using const */
			/* eMutablePtrs note that they have to be const. */
	const T* operator->() const { ptrAssert(ptr); return ptr; }
};
#endif

#endif
