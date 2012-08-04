#ifndef __lib_base_paths_h
#define __lib_base_paths_h

#include <string>

class eEnv {
private:
	static bool initialized;
	static void initialize();
	static int resolveVar(std::string &dest, const char *src);
	static int resolveVar(std::string &dest, const std::string &src);
public:
	static std::string resolve(const std::string &path);
};

#endif
