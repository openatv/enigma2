#ifndef __lib_python_python_h
#define __lib_python_python_h

#include <string>

class ePython
{
public:
	ePython();
	~ePython();
	int execute(const std::string &pythonfile, const std::string &funcname);
private:
	
};

#endif
