#ifndef VFD_H_
#define VFD_H_

class evfd
{
protected:
	static evfd *instance;
#ifdef SWIG
	evfd();
	~evfd();
#endif
public:
#ifndef SWIG
	evfd();
	~evfd();
#endif
	void init();
	static evfd* getInstance();

	void vfd_symbol_network(int net);
	void vfd_symbol_circle(int cir);
};


#endif
