#ifndef __lib_driver_action_h
#define __lib_driver_action_h

#include <lib/base/object.h>

		/* avoid warnigs :) */
#include <features.h>
#undef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200112L
#include <Python.h>
#include <lib/python/python.h>
#include <string>
#include <map>

class eWidget;

class eActionMap: public iObject
{
DECLARE_REF(eActionMap);
#ifdef SWIG
	eActionMap();
	~eActionMap();
#endif
public:
#ifndef SWIG
	eActionMap();
	~eActionMap();
	void bindAction(const std::string &context, int priority, int id, eWidget *widget);
	void unbindAction(eWidget *widget, int id);
#endif

	void bindAction(const std::string &context, int priority, PyObject *function);
	void unbindAction(const std::string &context, PyObject *function);
	
	void bindKey(const std::string &device, int key, int flags, const std::string &context, const std::string &action);
	
	void keyPressed(const std::string &device, int key, int flags);
	
	static RESULT getInstance(ePtr<eActionMap> &ptr);
#ifndef SWIG
private:
	static eActionMap *instance;
	struct eActionBinding
	{
//		eActionContext *m_context;
		std::string m_context; // FIXME
		
		PyObject *m_fnc;
		
		eWidget *m_widget;
		int m_id;
	};
	
	std::multimap<int, eActionBinding> m_bindings;

	friend struct compare_string_keybind_native;
	struct eNativeKeyBinding
	{
		std::string m_device;
		int m_key;
		int m_flags;
		
//		eActionContext *m_context;
		int m_action;
	};
	
	std::multimap<std::string, eNativeKeyBinding> m_native_keys;
	
	friend struct compare_string_keybind_python;
	struct ePythonKeyBinding
	{
		std::string m_device;
		int m_key;
		int m_flags;
		
		std::string m_action;
	};
	
	std::multimap<std::string, ePythonKeyBinding> m_python_keys;
#endif
};

#endif
