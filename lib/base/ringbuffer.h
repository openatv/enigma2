#ifndef QueueRingBufferH
#define QueueRingBufferH

template <class T>
class queueRingBuffer
{
	template <class A>
	struct link
	{
		link ( const A &val )
			:value(val)
		{}
		A value;
		link *nextLink;
		link *prevLink;
	};

	link<T> *lastFilled;
	link<T> *lastFree;
	unsigned int max;
	int count;
public:
	queueRingBuffer( unsigned int max );
	~queueRingBuffer();
	int size() { return count; }
	T& queueRingBuffer::dequeue();
	T& queueRingBuffer::current();
	void queueRingBuffer::enqueue( const T &val );
};

template <class T>
queueRingBuffer<T>::queueRingBuffer( unsigned int max )
{
	count = 0;
	// constructor for queues based on ring buffers
	// create the first link
	T initialvalue;
	lastFree = new link<T>( initialvalue );
	lastFilled = lastFree;
	// make value point to itself
	lastFilled->nextLink = lastFilled;
	lastFilled->prevLink = lastFilled;
	// now add the remainder of the elements
	while ( max-- > 0 )
	{
		link<T> * newLink = new link<T>( initialvalue );
		newLink->prevLink = lastFilled;
		newLink->nextLink = lastFilled->nextLink;
		lastFilled->nextLink->prevLink = newLink;
		lastFilled->nextLink = newLink;
	}
}

template <class T>
queueRingBuffer<T>::~queueRingBuffer()
{
	// delete all memory associated with ring buffer
	link<T> * p = lastFree;
	link<T> * next;

	// walk around the circle deleting nodes
	while( p->nextLink != lastFree )
	{
		next = p->nextLink;
		delete p;
		p = next;
	}
}

template <class T>
T& queueRingBuffer<T>::dequeue()
{
	// remove element form front of queue
	// advance last free position
	lastFree = lastFree->nextLink;
	count--;
	// return value stored in last free position
	return lastFree->value;
}

template <class T>
T& queueRingBuffer<T>::current()
{
	// return value stored in current
	return lastFree->nextLink->value;
}

template <class T>
void queueRingBuffer<T>::enqueue( const T &val )
{
	// add new element to end of queue buffer
	// first check for potential overflow
	if( lastFilled->nextLink == lastFree )
	{
//		eDebug("increase size %d", count);
		link<T> * newLink = new link<T>( val );
		newLink->prevLink = lastFilled;
		newLink->nextLink = lastFilled->nextLink;
		lastFilled->nextLink->prevLink = newLink;
		lastFilled->nextLink = newLink;
	}
	else
	{
		// simply advance the last filled pointer
		lastFilled = lastFilled->nextLink;
		lastFilled->value = val;
	}
	count++;
}
#endif
