#ifndef __smartptr_h
#define __smartptr_h

#include "object.h"
#include <stdio.h>

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
	ePtr(const ePtr &c)
	{
		ptr=c.ptr;
		if (ptr)
			ptr->AddRef();
	}
	ePtr &operator=(T *c)
	{
		if (ptr)
			ptr->Release();
		ptr=c;
		if (ptr)
			ptr->AddRef();
		return *this;
	}
	
	ePtr &operator=(ePtr<T> &c)
	{
		if (ptr)
			ptr->Release();
		ptr=c.ptr;
		if (ptr)
			ptr->AddRef();
		return *this;
	}
	
	~ePtr()
	{
		if (ptr)
			ptr->Release();
	}
	T* &ptrref() { assert(!ptr); return ptr; }
	T* operator->() { assert(ptr); return ptr; }
	const T* operator->() const { assert(ptr); return ptr; }
	operator T*() const { return this->ptr; }
};


#endif
