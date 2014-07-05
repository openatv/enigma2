#ifndef _E_PTRLIST_
#define _E_PTRLIST_

#include <list>
#include <vector>
#include <algorithm>
#include <lib/base/smartptr.h>
#include <lib/base/eerror.h>

template <class T>
class ePtrList : public std::list<T*>
{
public:
	typedef typename std::list<T*, std::allocator<T*> >::iterator std_list_T_iterator;  // to remove compiler warnings
	typedef typename std::list<T*, std::allocator<T*> >::const_iterator std_list_T_const_iterator;
	typedef typename std::list<T*, std::allocator<T*> >::reverse_iterator std_list_T_reverse_iterator;
	typedef typename std::list<T*, std::allocator<T*> >::const_reverse_iterator std_list_T_const_reverse_iterator;
	typedef typename ePtrList<T>::iterator T_iterator;
	typedef typename ePtrList<T>::const_iterator T_const_iterator;
	typedef typename ePtrList<T>::reverse_iterator T_reverse_iterator;
	typedef typename ePtrList<T>::const_reverse_iterator T_const_reverse_iterator;

// Iterator classes
	class iterator;
	class const_iterator;
	class reverse_iterator;
	class const_reverse_iterator;

// Constructors
	inline ePtrList();
	inline ePtrList(const ePtrList&);
	inline ~ePtrList();

// overwritted sort method
	inline void sort();

// changed methods for autodelete and current implementation
	inline void remove(T* t);
	inline void singleremove(T* t);
	inline void clear();
	inline void pop_back();
	inline void pop_front();
	inline void push_back(T*);
	inline void push_front(T*);

// added methods for current implementation
	inline T* take();
	inline void take(T* t);
	inline T* current();
	inline T* next();
	inline T* prev();
	inline T* first();
	inline T* last();
	inline T* setCurrent(const T*);
	inline const T* current() const;
	inline const T* next() const;
	inline const T* prev() const;
	inline const T* first() const;
	inline const T* last() const;

// added operator methods
	inline operator bool() const;
	inline bool operator!() const;

// added compare struct ... to sort
	struct less;
private:
	iterator cur;
public:
	iterator begin()
	{
	//	makes implicit type conversion form std::list::iterator to ePtrList::iterator
		return std::list<T*>::begin();
	}

	iterator end()
	{
	//	makes implicit type conversion form std::list::iterator to ePtrList::iterator
		return std::list<T*>::end();
	}

	const_iterator begin() const
	{
	//	makes implicit type conversion form std::list::const_iterator to ePtrList::const_iterator
		return std::list<T*>::begin();
	}

	const_iterator end() const
	{
	//	makes implicit type conversion form std::list::const_iterator to ePtrList::const_iterator
		return std::list<T*>::end();
	}

	reverse_iterator rbegin()
	{
	//	makes implicit type conversion form std::list::reverse:_iterator to ePtrList::reverse_iterator
		return std::list<T*>::rbegin();
	}

	reverse_iterator rend()
	{
	//	makes implicit type conversion form std::list::reverse_iterator to ePtrList::reverse_iterator
		return std::list<T*>::rend();
	}

	const_reverse_iterator rbegin() const
	{
	//	makes implicit type conversion form std::list::const_reverse_iterator to ePtrList::const_reverse_iterator
		return std::list<T*>::rbegin();
	}

	const_reverse_iterator rend() const
	{
	//	makes implicit type conversion form std::list::const_reverse_iterator to ePtrList::const_reverse_iterator
		return std::list<T*>::rend();
	}

	iterator erase(iterator it)
	{
	// 	Remove the item it, if auto-deletion is enabled, than the list call delete for this item
	//  If current is equal to the item that was removed, current is set to the next item in the list
		if (cur == it)
			return cur = std::list<T*>::erase(it);
		else
			return std::list<T*>::erase(it);
	}

	iterator erase(iterator from, iterator to)
	{
	// 	Remove all items between the to iterators from and to
	//	If auto-deletion is enabled, than the list call delete for all removed items
		while (from != to)
			from = erase(from);

		return from;
	}

	operator iterator()
	{
	//	Returns a iterator that equal to begin() of the list
		return begin();
	}

	operator const_iterator() const
	{
	//	Returns a const_iterator that equal to begin() of the list
		return begin();
	}

	operator reverse_iterator()
	{
	//	Returns a reverse_iterator that equal to rbegin() of the list
		return rbegin();
	}

	operator const_reverse_iterator() const
	{
	//	Returns a const_reverse_iterator that equal to rbegin() of the list
		return rbegin();
	}

	std::vector<T>* getVector()
	{
		// Creates an vector and copys all elements to this vector
		// returns a pointer to this new vector ( the reserved memory must deletet from the receiver !! )
		std::vector<T>* v=new std::vector<T>();
		v->reserve( std::list<T>::size() );
		for ( std_list_T_iterator it( std::list<T*>::begin() ); it != std::list<T*>::end(); it++)
			v->push_back( **it );

		return v;
	}

	inline iterator insert_in_order( T* e )
	{
		// added a new item to the list... in order
		// returns a iterator to the new item
		return this->insert( std::lower_bound( std::list<T*>::begin(), std::list<T*>::end(), e, less()), e );
	}

};

/////////////////// iterator class /////////////////////////////
template <class T>
class ePtrList<T>::iterator : public std::list<T*>::iterator
{
public:
	// Constructors
	iterator(const std_list_T_iterator& Q)		: std_list_T_iterator(Q)	{	}

	// changed operator for pointer
	T* operator->() const
	{
		return *std::list<T*>::iterator::operator->();
	}

	operator T&() const
	{
		return *operator->();
	}

	operator T*() const
	{
		return operator->();
	}

	iterator& operator++()
	{
		std::list<T*>::iterator::operator++();
		return *this;
	}

	iterator operator++(int)
	{
		return std::list<T*>::iterator::operator++(0);
	}

	iterator& operator--()
	{
		std::list<T*>::iterator::operator--();
		return *this;
	}

	iterator operator--(int)
	{
		return std::list<T*>::iterator::operator--(0);
	}
};

/////////////////// const_iterator class /////////////////////////////
template <class T>
class ePtrList<T>::const_iterator : public std::list<T*>::const_iterator
{
public:
	// Constructors
	const_iterator(const std_list_T_const_iterator& Q)		:std_list_T_const_iterator(Q)	{	}

	// changed operator for pointer
	T* operator->() const
	{
		return *std::list<T*>::const_iterator::operator->();
	}

	operator T&() const
	{
		return *operator->();
	}

	operator T*() const
	{
		return operator->();
	}

	const_iterator& operator++()
	{
		std::list<T*>::const_iterator::operator++();
		return *this;
	}

	const_iterator operator++(int)
	{
		return std::list<T*>::const_iterator::operator++(0);
	}

	const_iterator& operator--()
	{
		std::list<T*>::const_iterator::operator--();
		return *this;
	}

	const_iterator operator--(int)
	{
		return std::list<T*>::const_iterator::operator--(0);
	}
};

/////////////////// reverse_iterator class /////////////////////////////
template <class T>
class ePtrList<T>::reverse_iterator : public std::list<T*>::reverse_iterator
{
public:
	// Constructors
	reverse_iterator(const std_list_T_reverse_iterator& Q)		:std_list_T_reverse_iterator(Q)	{	}

	// changed operators for pointer
	T* operator->() const
	{
		return *std::list<T*>::reverse_iterator::operator->();
	}

	operator T&() const
	{
		return *operator->();
	}

	operator T*() const
	{
		return operator->();
	}

	reverse_iterator& operator++()
	{
		std::list<T*>::reverse_iterator::operator++();
		return *this;
	}

	reverse_iterator operator++(int)
	{
		return std::list<T*>::reverse_iterator::operator++(0);
	}

	reverse_iterator& operator--()
	{
		std::list<T*>::reverse_iterator::operator--();
		return *this;
	}

	reverse_iterator operator--(int)
	{
		return std::list<T*>::reverse_iterator::operator--(0);
	}
};

/////////////////// const_reverse_iterator class /////////////////////////////
template <class T>
class ePtrList<T>::const_reverse_iterator : public std::list<T*>::const_reverse_iterator
{
public:
	// Constructors
	const_reverse_iterator(const std_list_T_const_reverse_iterator& Q)		:std_list_T_const_reverse_iterator(Q)	{	}

	// changed operators for pointer
	T* operator->() const
	{
		return *std::list<T*>::const_reverse_iterator::operator->();
	}

	operator T&() const
	{
		return *operator->();
	}

	operator T*() const
	{
		return operator->();
	}

	const_reverse_iterator& operator++()
	{
		std::list<T*>::const_reverse_iterator::operator++();
		return *this;
	}

	const_reverse_iterator operator++(int)
	{
		return std::list<T*>::const_reverse_iterator::operator++(0);
	}

	const_reverse_iterator& operator--()
	{
		std::list<T*>::const_reverse_iterator::operator--();
		return *this;
	}

	const_reverse_iterator operator--(int)
	{
		return std::list<T*>::const_reverse_iterator::operator--(0);
	}
};

/////////////////// Default Constructor /////////////////////////////
template <class T>
ePtrList<T>::ePtrList()
    :cur(std::list<T*>::begin())
{

}

/////////////////// Copy Constructor /////////////////////////////
template <class T>
ePtrList<T>::ePtrList(const ePtrList& e)
	:std::list<T*>(e), cur(e.cur)
{
}

/////////////////// ePtrList Destructor /////////////////////////////
template <class T>
inline ePtrList<T>::~ePtrList()
{
}

/////////////////// ePtrList sort() /////////////////////////
template <class T>
inline void ePtrList<T>::sort()
{
//	Sorts all items in the list.
// 	The type T must have a operator <.
	std::list<T*>::sort(typename ePtrList<T>::less());
}

/////////////////// ePtrList remove(T*) /////////////////////////
template <class T>
inline void ePtrList<T>::remove(T* t)
{
// 	Remove all items that, equals to t, if auto-deletion is enabled, than the list call delete for the removed items
//  If current is equal to one of the removed items, current is set to the next valid item
	T_iterator it(std::list<T*>::begin());

	while (it != std::list<T*>::end())
		if (*it == t)
		{
			it=erase(it);
			break;  // one item is complete removed an deleted
		}
		else
			it++;

	while (it != std::list<T*>::end())
		if (*it == t)
			it = std::list<T*>::erase(it);  // remove all other items that equals to t (no delete is called..)
		else
			it++;

}

/////////////////// ePtrList singleremove(T*) /////////////////////////
template <class T>
inline void ePtrList<T>::singleremove(T* t)
{
// 	Remove the first item equal to t, if auto-deletion is enabled, than the list call delete for the removed item
//  If current is equal to the removed item, current is set to the next valid item
	T_iterator it(std::list<T*>::begin());

	while (it != std::list<T*>::end())
		if (*it == t)
		{
			it=erase(it);
			break;  // one item is complete removed an deleted
		}
		else
			it++;
}

/////////////////// ePtrList clear() //////////////////
template <class T>
inline void ePtrList<T>::clear()
{
// 	Remove all items from the list
//	If auto-deletion is enabled, than the list call delete for all items in the list
	erase(std::list<T*>::begin(), std::list<T*>::end());
}

/////////////////// ePtrList pop_back() ////////////////////
template <class T>
inline void ePtrList<T>::pop_back()
{
//	Removes the last item from the list. If the current item ist the last, than the current is set to the new
//	last item in the list;
//	The removed item is deleted if auto-deletion is enabled.
	erase(--end());
}

/////////////////// ePtrList pop_front() ////////////////////
template <class T>
inline void ePtrList<T>::pop_front()
{
//	Removes the first item from the list. If the current item ist the first, than the current is set to the new
//	first item in the list;
//	The removed item is deleted if auto-deletion is enabled.
	erase(begin());
}

/////////////////// ePtrList push_back(T*) ////////////////////
template <class T>
inline void ePtrList<T>::push_back(T* x)
{
// Add a new item at the end of the list.
// The current item is set to the last item;
	std::list<T*>::push_back(x);
	last();
}

/////////////////// ePtrList push_front(T*) ////////////////////
template <class T>
inline void ePtrList<T>::push_front(T* x)
{
// Add a new item at the begin of the list.
// The current item is set to the first item;
	std::list<T*>::push_front(x);
	first();
}

/////////////////// ePtrList take() ////////////////////
template <class T>
inline T* ePtrList<T>::take()
{
// Takes the current item out of the list without deleting it (even if auto-deletion is enabled).
// Returns a pointer to the item taken out of the list, or null if the index is out of range.
// The item after the taken item becomes the new current list item if the taken item is not the last item in the list. If the last item is taken, the new last item becomes the current item.
// The current item is set to null if the list becomes empty.
	T* tmp = *cur;
	cur = std::list<T*>::erase(cur);
	return tmp;
}

/////////////////// ePtrList take(T*) ////////////////////
template <class T>
inline void ePtrList<T>::take(T* t)
{
// Takes all item with T* out of the list without deleting it (even if auto-deletion is enabled).
	std::list<T*>::remove(t);
}

/////////////////// ePtrList setCurrent(T*) ////////////////////
template <class T>
inline T* ePtrList<T>::setCurrent(const T* t)
{
	// Sets the internal current iterator to the first element that equals to t, and returns t when a item is found,
	// otherwise it returns 0 !
	for (T_iterator it(std::list<T*>::begin()); it != std::list<T*>::end(); ++it)
		if (*it == t)
		{
			cur = it;
			return *it;
		}

	return 0;
}

/////////////////// ePtrList current() ////////////////////
template <class T>
inline T* ePtrList<T>::current()
{
//	Returns a pointer to the current list item. The current item may be null (implies that the current index is -1).
	return cur==end() ? 0 : *cur;
}

/////////////////// ePtrList next() ////////////////////
template <class T>
inline T* ePtrList<T>::next()
{
//	Returns a pointer to the item succeeding the current item. Returns null if the current items is null or equal to the last item.
//	Makes the succeeding item current. If the current item before this function call was the last item, the current item will be set to null. If the current item was null, this function does nothing.
	if (cur == end())
		return 0;
	else
		if (++cur == end())
			return 0;
		else
			return *cur;
}

/////////////////// ePtrList prev() ////////////////////
template <class T>
inline T* ePtrList<T>::prev()
{
//	Returns a pointer to the item preceding the current item. Returns null if the current items is null or equal to the first item.
//	Makes the preceding item current. If the current item before this function call was the first item, the current item will be set to null. If the current item was null, this function does nothing.
	if (cur == begin())
		return 0;
	else
		return *--cur;
}

/////////////////// ePtrList first() ////////////////////
template <class T>
inline T* ePtrList<T>::first()
{
// Returns a pointer to the first item in the list and makes this the current list item, or null if the list is empty.
	return *(cur = begin());
}

/////////////////// ePtrList last() ////////////////////
template <class T>
inline T* ePtrList<T>::last()
{
//	Returns a pointer to the last item in the list and makes this the current list item, or null if the list is empty.
	return *(cur = --end());
}

/////////////////// const ePtrList current() ////////////////////
template <class T>
inline const T* ePtrList<T>::current() const
{
//	Returns a pointer to the current list item. The current item may be null (implies that the current index is not valid)
	return cur==end() ? 0 : *cur;
}

/////////////////// const ePtrList next() ////////////////////
template <class T>
inline const T* ePtrList<T>::next() const
{
//	Returns a pointer to the item succeeding the current item. Returns null if the current items is null or equal to the last item.
//	Makes the succeeding item current. If the current item before this function call was the last item, the current item will be set to null. If the current item was null, this function does nothing.
	if (cur == end())
		return 0;
	else
		if (++cur == end())
			return 0;
		else
			return *cur;
}

/////////////////// const ePtrList prev() ////////////////////
template <class T>
inline const T* ePtrList<T>::prev() const
{
//	Returns a pointer to the item preceding the current item. Returns null if the current items is null or equal to the first item.
//	Makes the preceding item current. If the current item before this function call was the first item, the current item will be set to null. If the current item was null, this function does nothing.
	if (cur == begin())
		return 0;
	else
		return *--cur;
}

/////////////////// const ePtrList first() ////////////////////
template <class T>
inline const T* ePtrList<T>::first() const
{
// Returns a pointer to the first item in the list and makes this the current list item, or null if the list is empty.
	return *(cur = begin());
}

/////////////////// const ePtrList last() ////////////////////
template <class T>
inline const T* ePtrList<T>::last() const
{
//	Returns a pointer to the last item in the list and makes this the current list item, or null if the list is empty.
	return *(cur = --end());
}

////////////////// struct less //////////////////////////////
template <class T>
struct ePtrList<T>::less
{
// 	operator() is used internal from the list to sort them
	bool operator() (const T* t1, const T* t2)
	{
		return (*t1 < *t2);
	}
};

/////////////////// ePtrList operator bool ////////////////////
template <class T>
ePtrList<T>::operator bool() const
{
//	Returns a bool that contains true, when the list is NOT empty otherwise false
	return !std::list<T*>::empty();
}

template <class T>
bool ePtrList<T>::operator!() const
{
//	Returns a bool that contains true, when the list is empty otherwise false
	return std::list<T*>::empty();
}

template <class T>
class eSmartPtrList : public std::list<ePtr<T> >
{
public:
	typedef typename std::list<ePtr<T>, std::allocator<ePtr<T> > >::iterator std_list_T_iterator;  // to remove compiler warnings
	typedef typename std::list<ePtr<T>, std::allocator<ePtr<T> > >::const_iterator std_list_T_const_iterator;
	typedef typename std::list<ePtr<T>, std::allocator<ePtr<T> > >::reverse_iterator std_list_T_reverse_iterator;
	typedef typename std::list<ePtr<T>, std::allocator<ePtr<T> > >::const_reverse_iterator std_list_T_const_reverse_iterator;
	typedef typename eSmartPtrList<T>::iterator T_iterator;
	typedef typename eSmartPtrList<T>::const_iterator T_const_iterator;
	typedef typename eSmartPtrList<T>::reverse_iterator T_reverse_iterator;
	typedef typename eSmartPtrList<T>::const_reverse_iterator T_const_reverse_iterator;

// Iterator classes
	class iterator;
	class const_iterator;
	class reverse_iterator;
	class const_reverse_iterator;

// Constructors
	inline eSmartPtrList();
	inline eSmartPtrList(const eSmartPtrList&);
	inline ~eSmartPtrList();

// overwritted sort method
	inline void sort();

// changed methods for autodelete and current implementation
	inline void remove(T* t);
	inline void clear();
	inline void pop_back();
	inline void pop_front();
	inline void push_back(T*);
	inline void push_front(T*);

// added methods for current implementation
//	inline T* take();
//	inline void take(T* t);
	inline T* current();
	inline T* next();
	inline T* prev();
	inline T* first();
	inline T* last();
	inline T* setCurrent(const T*);
	inline const T* current() const;
	inline const T* next() const;
	inline const T* prev() const;
	inline const T* first() const;
	inline const T* last() const;

// added operator methods
	inline operator bool() const;
	inline bool operator!() const;

// added compare struct ... to sort
	struct less;
private:
	iterator cur;
public:
	iterator begin()
	{
	//	makes implicit type conversion form std::list::iterator to eSmartPtrList::iterator
		return std::list<ePtr<T> >::begin();
	}

	iterator end()
	{
	//	makes implicit type conversion form std::list::iterator to eSmartPtrList::iterator
		return std::list<ePtr<T> >::end();
	}

	const_iterator begin() const
	{
	//	makes implicit type conversion form std::list::const_iterator to eSmartPtrList::const_iterator
		return std::list<ePtr<T> >::begin();
	}

	const_iterator end() const
	{
	//	makes implicit type conversion form std::list::const_iterator to eSmartPtrList::const_iterator
		return std::list<ePtr<T> >::end();
	}

	reverse_iterator rbegin()
	{
	//	makes implicit type conversion form std::list::reverse:_iterator to eSmartPtrList::reverse_iterator
		return std::list<ePtr<T> >::rbegin();
	}

	reverse_iterator rend()
	{
	//	makes implicit type conversion form std::list::reverse_iterator to eSmartPtrList::reverse_iterator
		return std::list<ePtr<T> >::rend();
	}

	const_reverse_iterator rbegin() const
	{
	//	makes implicit type conversion form std::list::const_reverse_iterator to eSmartPtrList::const_reverse_iterator
		return std::list<ePtr<T> >::rbegin();
	}

	const_reverse_iterator rend() const
	{
	//	makes implicit type conversion form std::list::const_reverse_iterator to eSmartPtrList::const_reverse_iterator
		return std::list<ePtr<T> >::rend();
	}

	iterator erase(iterator it)
	{
	// 	Remove the item it, if auto-deletion is enabled, than the list call delete for this item
	//  If current is equal to the item that was removed, current is set to the next item in the list

		if (cur == it)
			return cur = std::list<ePtr<T> >::erase(it);
		else
			return std::list<ePtr<T> >::erase(it);
	}

	iterator erase(iterator from, iterator to)
	{
	// 	Remove all items between the to iterators from and to
	//	If auto-deletion is enabled, than the list call delete for all removed items
		while (from != to)
			from = erase(from);

		return from;
	}

	operator iterator()
	{
	//	Returns a iterator that equal to begin() of the list
		return begin();
	}

	operator const_iterator() const
	{
	//	Returns a const_iterator that equal to begin() of the list
		return begin();
	}

	operator reverse_iterator()
	{
	//	Returns a reverse_iterator that equal to rbegin() of the list
		return rbegin();
	}

	operator const_reverse_iterator() const
	{
	//	Returns a const_reverse_iterator that equal to rbegin() of the list
		return rbegin();
	}

	std::vector<T>* getVector()
	{
		// Creates an vector and copys all elements to this vector
		// returns a pointer to this new vector ( the reserved memory must deletet from the receiver !! )
		std::vector<T>* v=new std::vector<T>();
		v->reserve( std::list<T>::size() );
    for ( std_list_T_iterator it( std::list<ePtr<T> >::begin() ); it != std::list<ePtr<T> >::end(); it++)
			v->push_back( **it );

		return v;
	}

	inline iterator insert_in_order( T* e )
	{
		// added a new item to the list... in order
		// returns a iterator to the new item
		return insert( std::lower_bound( std::list<ePtr<T> >::begin(), e, std::list<ePtr<T> >::end()), e );
	}

};

/////////////////// iterator class /////////////////////////////
template <class T>
class eSmartPtrList<T>::iterator : public std::list<ePtr<T> >::iterator
{
public:
	// Constructors
	iterator(const std_list_T_iterator& Q)		: std_list_T_iterator(Q)	{	}

	// changed operator for pointer
	T* operator->() const
	{
		return *std::list<ePtr<T> >::iterator::operator->();
	}

	operator T&() const
	{
		return *operator->();
	}

	operator T*() const
	{
		return operator->();
	}

	iterator& operator++()
	{
		std::list<ePtr<T> >::iterator::operator++();
		return *this;
	}

	iterator operator++(int)
	{
		return std::list<ePtr<T> >::iterator::operator++(0);
	}

	iterator& operator--()
	{
		std::list<ePtr<T> >::iterator::operator--();
		return *this;
	}

	iterator operator--(int)
	{
		return std::list<ePtr<T> >::iterator::operator--(0);
	}
};

/////////////////// const_iterator class /////////////////////////////
template <class T>
class eSmartPtrList<T>::const_iterator : public std::list<ePtr<T> >::const_iterator
{
public:
	// Constructors
	const_iterator(const std_list_T_const_iterator& Q)		:std_list_T_const_iterator(Q)	{	}

	// changed operator for pointer
	T* operator->() const
	{
		return *std::list<ePtr<T> >::const_iterator::operator->();
	}

	operator T&() const
	{
		return *operator->();
	}

	operator T*() const
	{
		return operator->();
	}

	const_iterator& operator++()
	{
		std::list<ePtr<T> >::const_iterator::operator++();
		return *this;
	}

	const_iterator operator++(int)
	{
		return std::list<ePtr<T> >::const_iterator::operator++(0);
	}

	const_iterator& operator--()
	{
		std::list<ePtr<T> >::const_iterator::operator--();
		return *this;
	}

	const_iterator operator--(int)
	{
		return std::list<ePtr<T> >::const_iterator::operator--(0);
	}
};

/////////////////// reverse_iterator class /////////////////////////////
template <class T>
class eSmartPtrList<T>::reverse_iterator : public std::list<ePtr<T> >::reverse_iterator
{
public:
	// Constructors
	reverse_iterator(const std_list_T_reverse_iterator& Q)		:std_list_T_reverse_iterator(Q)	{	}

	// changed operators for pointer
	T* operator->() const
	{
		return *std::list<ePtr<T> >::reverse_iterator::operator->();
	}

	operator T&() const
	{
		return *operator->();
	}

	operator T*() const
	{
		return operator->();
	}

	reverse_iterator& operator++()
	{
		std::list<ePtr<T> >::reverse_iterator::operator++();
		return *this;
	}

	reverse_iterator operator++(int)
	{
		return std::list<ePtr<T> >::reverse_iterator::operator++(0);
	}

	reverse_iterator& operator--()
	{
		std::list<ePtr<T> >::reverse_iterator::operator--();
		return *this;
	}

	reverse_iterator operator--(int)
	{
		return std::list<ePtr<T> >::reverse_iterator::operator--(0);
	}
};

/////////////////// const_reverse_iterator class /////////////////////////////
template <class T>
class eSmartPtrList<T>::const_reverse_iterator : public std::list<ePtr<T> >::const_reverse_iterator
{
public:
	// Constructors
	const_reverse_iterator(const std_list_T_const_reverse_iterator& Q)		:std_list_T_const_reverse_iterator(Q)	{	}

	// changed operators for pointer
	T* operator->() const
	{
		return *std::list<ePtr<T> >::const_reverse_iterator::operator->();
	}

	operator T&() const
	{
		return *operator->();
	}

	operator T*() const
	{
		return operator->();
	}

	const_reverse_iterator& operator++()
	{
		std::list<ePtr<T> >::const_reverse_iterator::operator++();
		return *this;
	}

	const_reverse_iterator operator++(int)
	{
		return std::list<ePtr<T> >::const_reverse_iterator::operator++(0);
	}

	const_reverse_iterator& operator--()
	{
		std::list<ePtr<T> >::const_reverse_iterator::operator--();
		return *this;
	}

	const_reverse_iterator operator--(int)
	{
		return std::list<ePtr<T> >::const_reverse_iterator::operator--(0);
	}
};

/////////////////// Default Constructor /////////////////////////////
template <class T>
eSmartPtrList<T>::eSmartPtrList()
    :cur(std::list<ePtr<T> >::begin())
{

}

/////////////////// Copy Constructor /////////////////////////////
template <class T>
eSmartPtrList<T>::eSmartPtrList(const eSmartPtrList& e)
	:std::list<ePtr<T> >(e), cur(e.cur)
{
}

/////////////////// eSmartPtrList Destructor /////////////////////////////
template <class T>
inline eSmartPtrList<T>::~eSmartPtrList()
{
}


/////////////////// eSmartPtrList sort() /////////////////////////
template <class T>
inline void eSmartPtrList<T>::sort()
{
//	Sorts all items in the list.
// 	The type T must have a operator <.
	std::list<ePtr<T> >::sort(eSmartPtrList<T>::less());
}

/////////////////// eSmartPtrList remove(T*) /////////////////////////
template <class T>
inline void eSmartPtrList<T>::remove(T* t)
{
// 	Remove all items that, equals to t, if auto-deletion is enabled, than the list call delete for the removed items
//  If current is equal to one of the removed items, current is set to the next valid item
	T_iterator it(std::list<ePtr<T> >::begin());

	while (it != std::list<ePtr<T> >::end())
		if (*it == t)
		{
			it=erase(it);
			break;  // one item is complete removed an deleted
		}
		else
			it++;

	while (it != std::list<ePtr<T> >::end())
		if (*it == t)
			it = std::list<ePtr<T> >::erase(it);  // remove all other items that equals to t (no delete is called..)
		else
			it++;

}

/////////////////// eSmartPtrList clear() //////////////////
template <class T>
inline void eSmartPtrList<T>::clear()
{
// 	Remove all items from the list
//	If auto-deletion is enabled, than the list call delete for all items in the list
	erase(std::list<ePtr<T> >::begin(), std::list<ePtr<T> >::end());
}

/////////////////// eSmartPtrList pop_back() ////////////////////
template <class T>
inline void eSmartPtrList<T>::pop_back()
{
//	Removes the last item from the list. If the current item ist the last, than the current is set to the new
//	last item in the list;
//	The removed item is deleted if auto-deletion is enabled.
	erase(--end());
}

/////////////////// eSmartPtrList pop_front() ////////////////////
template <class T>
inline void eSmartPtrList<T>::pop_front()
{
//	Removes the first item from the list. If the current item ist the first, than the current is set to the new
//	first item in the list;
//	The removed item is deleted if auto-deletion is enabled.
	erase(begin());
}

/////////////////// eSmartPtrList push_back(T*) ////////////////////
template <class T>
inline void eSmartPtrList<T>::push_back(T* x)
{
// Add a new item at the end of the list.
// The current item is set to the last item;
	std::list<ePtr<T> >::push_back(x);
	last();
}

/////////////////// eSmartPtrList push_front(T*) ////////////////////
template <class T>
inline void eSmartPtrList<T>::push_front(T* x)
{
// Add a new item at the begin of the list.
// The current item is set to the first item;
	std::list<ePtr<T> >::push_front(x);
	first();
}

/////////////////// eSmartPtrList setCurrent(T*) ////////////////////
template <class T>
inline T* eSmartPtrList<T>::setCurrent(const T* t)
{
	// Sets the internal current iterator to the first element that equals to t, and returns t when a item is found,
	// otherwise it returns 0 !
	for (T_iterator it(std::list<ePtr<T> >::begin()); it != std::list<ePtr<T> >::end(); ++it)
		if (*it == t)
		{
			cur = it;
			return *it;
		}

	return 0;
}

/////////////////// eSmartPtrList current() ////////////////////
template <class T>
inline T* eSmartPtrList<T>::current()
{
//	Returns a pointer to the current list item. The current item may be null (implies that the current index is -1).
	return cur==end() ? 0 : *cur;
}

/////////////////// eSmartPtrList next() ////////////////////
template <class T>
inline T* eSmartPtrList<T>::next()
{
//	Returns a pointer to the item succeeding the current item. Returns null if the current items is null or equal to the last item.
//	Makes the succeeding item current. If the current item before this function call was the last item, the current item will be set to null. If the current item was null, this function does nothing.
	if (cur == end())
		return 0;
	else
		if (++cur == end())
			return 0;
		else
			return *cur;
}

/////////////////// eSmartPtrList prev() ////////////////////
template <class T>
inline T* eSmartPtrList<T>::prev()
{
//	Returns a pointer to the item preceding the current item. Returns null if the current items is null or equal to the first item.
//	Makes the preceding item current. If the current item before this function call was the first item, the current item will be set to null. If the current item was null, this function does nothing.
	if (cur == begin())
		return 0;
	else
		return *--cur;
}

/////////////////// eSmartPtrList first() ////////////////////
template <class T>
inline T* eSmartPtrList<T>::first()
{
// Returns a pointer to the first item in the list and makes this the current list item, or null if the list is empty.
	return *(cur = begin());
}

/////////////////// eSmartPtrList last() ////////////////////
template <class T>
inline T* eSmartPtrList<T>::last()
{
//	Returns a pointer to the last item in the list and makes this the current list item, or null if the list is empty.
	return *(cur = --end());
}

/////////////////// const eSmartPtrList current() ////////////////////
template <class T>
inline const T* eSmartPtrList<T>::current() const
{
//	Returns a pointer to the current list item. The current item may be null (implies that the current index is not valid)
	return cur==end() ? 0 : *cur;
}

/////////////////// const eSmartPtrList next() ////////////////////
template <class T>
inline const T* eSmartPtrList<T>::next() const
{
//	Returns a pointer to the item succeeding the current item. Returns null if the current items is null or equal to the last item.
//	Makes the succeeding item current. If the current item before this function call was the last item, the current item will be set to null. If the current item was null, this function does nothing.
	if (cur == end())
		return 0;
	else
		if (++cur == end())
			return 0;
		else
			return *cur;
}

/////////////////// const eSmartPtrList prev() ////////////////////
template <class T>
inline const T* eSmartPtrList<T>::prev() const
{
//	Returns a pointer to the item preceding the current item. Returns null if the current items is null or equal to the first item.
//	Makes the preceding item current. If the current item before this function call was the first item, the current item will be set to null. If the current item was null, this function does nothing.
	if (cur == begin())
		return 0;
	else
		return *--cur;
}

/////////////////// const eSmartPtrList first() ////////////////////
template <class T>
inline const T* eSmartPtrList<T>::first() const
{
// Returns a pointer to the first item in the list and makes this the current list item, or null if the list is empty.
	return *(cur = begin());
}

/////////////////// const eSmartPtrList last() ////////////////////
template <class T>
inline const T* eSmartPtrList<T>::last() const
{
//	Returns a pointer to the last item in the list and makes this the current list item, or null if the list is empty.
	return *(cur = --end());
}

////////////////// struct less //////////////////////////////
template <class T>
struct eSmartPtrList<T>::less
{
// 	operator() is used internal from the list to sort them
	bool operator() (const T* t1, const T* t2)
	{
		return (*t1 < *t2);
	}
};

/////////////////// eSmartPtrList operator bool ////////////////////
template <class T>
eSmartPtrList<T>::operator bool() const
{
//	Returns a bool that contains true, when the list is NOT empty otherwise false
	return !std::list<T>::empty();
}

template <class T>
bool eSmartPtrList<T>::operator!() const
{
//	Returns a bool that contains true, when the list is empty otherwise false
	return std::list<T>::empty();
}

#endif // _E_PTRLIST
