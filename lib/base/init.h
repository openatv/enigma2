#ifndef __init_h
#define __init_h

#include <list>
#include <utility>

class eAutoInit;

class eInit
{
	static std::list<std::pair<int,eAutoInit*> > *cl;
	friend class eAutoInit;
	static int rl;
public:
	eInit();
	~eInit();
	static void setRunlevel(int rlev);
	static void add(int trl, eAutoInit *c);
	static void remove(int trl, eAutoInit *c);
};

class eAutoInit
{
	friend class eInit;
	virtual void initNow()=0;
	virtual void closeNow()=0;
protected:
	int rl;
	char *description;
public:
	eAutoInit(int rl, char *description): rl(rl), description(description)
	{
	}
	virtual ~eAutoInit();
	const char *getDescription() const { return description; };
};

template<class T1, class T2> class
eAutoInitP1: protected eAutoInit
{
	T1 *t;
	const T2 &arg;
	void initNow()
	{
		t=new T1(arg);
	}
	void closeNow()
	{
		delete t;
	}
public:
	operator T1*()
	{
		return t;
	}
	eAutoInitP1(const T2 &arg, int runl, char *description): eAutoInit(runl, description), arg(arg)
	{
		eInit::add(rl, this);
	}
	~eAutoInitP1()
	{
		eInit::remove(rl, this);
	}
};

template<class T1> class
eAutoInitP0: protected eAutoInit
{
	T1 *t;
	void initNow()
	{
		t=new T1();
	}
	void closeNow()
	{
		delete t;
	}
public:
	operator T1*()
	{
		return t;
	}
	T1 *operator->()
	{
		return t;
	}
	eAutoInitP0(int runl, char *description): eAutoInit(runl, description)
	{
		eInit::add(rl, this);
	}
	~eAutoInitP0()
	{
		eInit::remove(rl, this);
	}
};

#endif
