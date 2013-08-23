#ifndef __smartptr_h
#define __smartptr_h

#include "object.h"
#include <stdio.h>
#include <string.h>
#include <lib/python/swig.h>

template<class T>
class ePtr
{
protected:
	T *ptr;
public:
	T &operator*() { return *ptr; }
	ePtr(): ptr(0)
	{
	}
	ePtr(T *c): ptr(c)
	{
		if (c)
			c->AddRef();
	}
	ePtr(const ePtr &c): ptr(c.ptr)
	{
		if (ptr)
			ptr->AddRef();
	}
	ePtr &operator=(T *c)
	{
		if (c)
			c->AddRef();
		if (ptr)
			ptr->Release();
		ptr=c;
		return *this;
	}
	ePtr &operator=(ePtr<T> &c)
	{
		if (c.ptr)
			c.ptr->AddRef();
		if (ptr)
			ptr->Release();
		ptr=c.ptr;
		return *this;
	}
	~ePtr()
	{
		if (ptr)
			ptr->Release();
	}
	/* Horribly misnamed now, but why waste >9 bytes on each object just
	 * to satisfy one ServiceEventTracker which doesn't even care about
	 * the actual type it returns. */
	unsigned int getPtrString() const
	{
		return (unsigned int)ptr;
	}
#ifndef SWIG
	T* grabRef() { if (!ptr) return 0; ptr->AddRef(); return ptr; }
	T* &ptrref() { return ptr; }
	operator bool() const { return !!this->ptr; }
#endif
	T* operator->() const { return ptr; }
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
	T* &ptrref() { return ptr; }
#endif
	T* operator->() const { return ptr; }
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
	ePtrHelper<T> operator->() { return ePtrHelper<T>(ptr); }
			/* for const objects, we don't need the helper, as they can't */
			/* be changed outside the program flow. at least this is */
			/* what the compiler assumes, so in case you're using const */
			/* eMutablePtrs note that they have to be const. */
	const T* operator->() const { return ptr; }
};
#endif

#endif
