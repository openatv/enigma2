#ifndef __lib_system_init_num_
#define __lib_system_init_num_

namespace eAutoInitNumbers
{
	enum { increment=5 };
	enum
	{
		configuration=0,
		lowlevel=configuration+increment,
		network=lowlevel,
		graphic=lowlevel+increment,
		skin=graphic+increment,
		rc=skin+increment,
		guiobject=rc+increment,
		actions=guiobject+increment,
		dvb=actions+increment,
		service=dvb+increment,
		osd=service+increment,
		wizard=osd+increment,
		main=osd+increment*5,
	};
};

#endif
