#ifndef __misc_options_h
#define __misc_options_h

class Misc_Options
{
	static Misc_Options *instance;
	int m_12V_output_state;
#ifdef SWIG
	Misc_Options();
#endif
public:
#ifndef SWIG
	Misc_Options();
#endif
	static Misc_Options *getInstance();
	int set_12V_output(int val);
	int get_12V_output() { return m_12V_output_state; }
	bool detected_12V_output();
};

#endif // __misc_options_h
