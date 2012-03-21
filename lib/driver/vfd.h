#ifndef VFD_H_
#define VFD_H_

class evfd
{
protected:
	static evfd *instance;
	int file_vfd;
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

	void vfd_write_string(char * string);
	void vfd_led(char * led);
};


#endif
