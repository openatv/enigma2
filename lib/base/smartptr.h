#ifndef __smartptr_h
#define __smartptr_h

#include "object.h"
#include <stdio.h>

template<class T>
class ePtr
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
	T &operator*() { return *ptr; }
	ePtr(): ptr(0)
	{
	}
	ePtr(T *c): ptr(c)
	{
		if (c)
			c->AddRef();
	}
	ePtr(const ePtr &c)
	{
		ptr=c.ptr;
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
	
	T* grabRef() { if (!ptr) return 0; ptr->AddRef(); return ptr; }
	T* &ptrref() { assert(!ptr); return ptr; }
	ePtrHelper<T> operator->() { assert(ptr); return ePtrHelper<T>(ptr); }

			/* for const objects, we don't need the helper, as they can't */
			/* be changed outside the program flow. at least this is */
			/* what the compiler assumes, so in case you're using const */
			/* ePtrs note that they have to be const. */
	const T* operator->() const { assert(ptr); return ptr; }
	operator T*() const { return this->ptr; }
};


#endif
