#include <lib/actions/action.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/actions/actionids.h>
#include <lib/driver/rc.h>

/*

  THIS CODE SUCKS.

we need:
 - contexts that aren't compared as strings,
 - maybe a lookup "device,key,flags" -> actions? (lazy validation, on bindAction)
 - devices as ids
 - seperate native from python keys? (currently, if an action wasn't found, it's ignored.)

Sorry. I spent 3 days on thinking how this could be made better, and it just DID NOT WORKED OUT.

If you have a better idea, please tell me.

 */

DEFINE_REF(eActionMap);

eActionMap *eActionMap::instance;

eActionMap::eActionMap()
{
	instance = this;
}

eActionMap::~eActionMap()
{
	instance = 0;
}

RESULT eActionMap::getInstance(ePtr<eActionMap> &ptr)
{
	ptr = instance;
	if (!ptr)
		return -1;
	return 0;
}

void eActionMap::bindAction(const std::string &context, int priority, int id, eWidget *widget)
{
	eActionBinding bnd;

	//eDebug("[eActionMap] bind widget to %s: prio=%d id=%d", context.c_str(), priority, id);
	bnd.m_context = context;
	bnd.m_widget = widget;
	bnd.m_id = id;
	m_bindings.insert(std::pair<int,eActionBinding>(priority, bnd));
}

void eActionMap::bindAction(const std::string &context, int priority, ePyObject function)
{
	eActionBinding bnd;

	//eDebug("[eActionMap] bind function to %s: prio=%d", context.c_str(), priority);
	bnd.m_context = context;
	bnd.m_widget = 0;
	Py_INCREF(function);
	bnd.m_fnc = function;
	m_bindings.insert(std::pair<int,eActionBinding>(priority, bnd));
}

void eActionMap::unbindAction(eWidget *widget, int id)
{
	//eDebug("[eActionMap] unbind widget id=%d", id);
	for (std::multimap<int, eActionBinding>::iterator i(m_bindings.begin()); i != m_bindings.end(); ++i)
		if (i->second.m_widget == widget && i->second.m_id == id)
		{
			m_bindings.erase(i);
			return;
		}
}

void eActionMap::unbindAction(const std::string &context, ePyObject function)
{
	//eDebug("[eActionMap] unbind function from %s", context.c_str());
	for (std::multimap<int, eActionBinding>::iterator i(m_bindings.begin()); i != m_bindings.end(); ++i)
		if (i->second.m_fnc && (PyObject_Compare(i->second.m_fnc, function) == 0))
		{
			Py_DECREF(i->second.m_fnc);
			m_bindings.erase(i);
			return;
		}
	eFatal("[eActionMap] unbindAction with illegal python reference");
}


void eActionMap::bindKey(const std::string &domain, const std::string &device, int key, int flags, const std::string &context, const std::string &action)
{
	// start searching the actionlist table
	//eDebug("[eActionMap] bind key from %s to %s: domain=%s action=%s key=%d flags=%d", device.c_str(), context.c_str(), domain.c_str(), action.c_str(), key, flags);
	unsigned int i;
	for (i = 0; i < sizeof(actions)/sizeof(*actions); ++i)
	{
		if (actions[i].m_context == context && actions[i].m_action == action)
		{
			// found native action
			eNativeKeyBinding bind;
			bind.m_device = device;
			bind.m_key = key;
			bind.m_flags = flags;
			bind.m_action = actions[i].m_id;
			bind.m_domain = domain;
			m_native_keys.insert(std::pair<std::string,eNativeKeyBinding>(context, bind));
			return;
		}
	}

	// no action, so it must be a pythonAction
	ePythonKeyBinding bind;

	bind.m_device = device;
	bind.m_key = key;
	bind.m_flags = flags;
	bind.m_action = action;
	bind.m_domain = domain;
	m_python_keys.insert(std::pair<std::string,ePythonKeyBinding>(context, bind));
}


void eActionMap::bindTranslation(const std::string &domain, const std::string &device, int keyin, int keyout, int toggle)
{
	//eDebug("[eActionMap] bind translation for %s from %d to %d toggle=%d in %s", device.c_str(), keyin, keyout, toggle, domain.c_str());
	eTranslationBinding trans;

	trans.m_keyin  = keyin;
	trans.m_keyout = keyout;
	trans.m_toggle = toggle;
	trans.m_domain = domain;

	std::map<std::string, eDeviceBinding>::iterator r = m_rcDevices.find(device);
	if (r == m_rcDevices.end())
	{
		eDeviceBinding rc;
		rc.m_togglekey = KEY_RESERVED;
		rc.m_toggle = 0;;
		rc.m_translations.push_back(trans);
		m_rcDevices.insert(std::pair<std::string, eDeviceBinding>(device, rc));
	}
	else
		r->second.m_translations.push_back(trans);
}


void eActionMap::bindToggle(const std::string &domain, const std::string &device, int togglekey)
{
	//eDebug("[eActionMap] bind togglekey for %s togglekey=%d in %s", device.c_str(), togglekey, domain.c_str());
	std::map<std::string, eDeviceBinding>::iterator r = m_rcDevices.find(device);
	if (r == m_rcDevices.end())
	{
		eDeviceBinding rc;
		rc.m_togglekey = togglekey;
		rc.m_toggle = 0;;
		m_rcDevices.insert(std::pair<std::string, eDeviceBinding>(device, rc));
	}
	else
	{
		r->second.m_togglekey = togglekey;
		r->second.m_toggle = 0;
	}
}


void eActionMap::unbindKeyDomain(const std::string &domain)
{
	//eDebug("[eActionMap] unbindDomain %s", domain.c_str());
	for (std::multimap<std::string, eNativeKeyBinding>::iterator i(m_native_keys.begin()); i != m_native_keys.end(); ++i)
		if (i->second.m_domain == domain)
		{
			m_native_keys.erase(i);
			i = m_native_keys.begin();
		}

	for (std::multimap<std::string, ePythonKeyBinding>::iterator i(m_python_keys.begin()); i != m_python_keys.end(); ++i)
		if (i->second.m_domain == domain)
		{
			m_python_keys.erase(i);
			i = m_python_keys.begin();
		}
}

struct call_entry
{
	ePyObject m_fnc, m_arg;
	eWidget *m_widget;
	void *m_widget_arg, *m_widget_arg2;
	call_entry(ePyObject fnc, ePyObject arg): m_fnc(fnc), m_arg(arg), m_widget(0), m_widget_arg(0) { }
	call_entry(eWidget *widget, void *arg, void *arg2): m_widget(widget), m_widget_arg(arg), m_widget_arg2(arg2) { }
};

void eActionMap::keyPressed(const std::string &device, int key, int flags)
{
	//eDebug("[eActionMap] key from %s: %d %d", device.c_str(), key, flags);

	// Check for remotes that need key translations
	std::map<std::string, eDeviceBinding>::iterator r = m_rcDevices.find(device);
	if (r != m_rcDevices.end())
	{

		if (key == r->second.m_togglekey && flags == eRCKey::flagMake)
		{
			r->second.m_toggle ^= 1;
			//eDebug("[eActionMap]   toggle key %d: now %d", key, r->second.m_toggle);
			return;
		}
		std::vector<eTranslationBinding> *trans = &r->second.m_translations;
		for (std::vector<eTranslationBinding>::iterator t(trans->begin()); t != trans->end(); ++t)
		{
			if (t->m_keyin == key && (t->m_toggle == 0 || r->second.m_toggle))
			{
				//eDebug("[eActionMap]   translate from %d to %d", key, t->m_keyout);
				key = t->m_keyout;
				break;
			}
		}
	}

	std::vector<call_entry> call_list;
	// iterate active contexts
	for (std::multimap<int,eActionBinding>::iterator c(m_bindings.begin()); c != m_bindings.end(); ++c)
	{
		if (flags == eRCKey::flagMake)
			c->second.m_prev_seen_make_key = key;
		else if (c->second.m_prev_seen_make_key != key)  // ignore repeat or break when the make code for this key was not visible
			continue;

		// is this a native context?
		if (c->second.m_widget)
		{
			// is this a named context, i.e. not the wildcard?
			if (c->second.m_context.size())
			{
				//eDebug("[eActionMap]   native context %s", c->second.m_context.c_str());
				std::multimap<std::string,eNativeKeyBinding>::const_iterator
					k = m_native_keys.lower_bound(c->second.m_context),
					e = m_native_keys.upper_bound(c->second.m_context);

				for (; k != e; ++k)
				{
					if (	k->second.m_key == key &&
						k->second.m_flags & (1<<flags) &&
						(k->second.m_device == device || k->second.m_device == "generic") )
						call_list.push_back(call_entry(c->second.m_widget, (void*)c->second.m_id, (void*)k->second.m_action));
				}
			}
			else
			{
				// wildcard - get any keys.
				//eDebug("[eActionMap]    native wildcard");
				if (c->second.m_widget->event(eWidget::evtKey, (void*)key, (void*)flags))
					return;
			}
		}
		else if (c->second.m_fnc)
		{
			if (c->second.m_context.size())
			{
				//eDebug("[eActionMap]   python context %s", c->second.m_context.c_str());
				std::multimap<std::string,ePythonKeyBinding>::const_iterator
					k = m_python_keys.lower_bound(c->second.m_context),
					e = m_python_keys.upper_bound(c->second.m_context);

				for (; k != e; ++k)
				{
					if (	k->second.m_key == key &&
						k->second.m_flags & (1<<flags) &&
						(k->second.m_device == device || k->second.m_device == "generic") )
					{
						ePyObject pArgs = PyTuple_New(2);
						PyTuple_SET_ITEM(pArgs, 0, PyString_FromString(k->first.c_str()));
						PyTuple_SET_ITEM(pArgs, 1, PyString_FromString(k->second.m_action.c_str()));
						Py_INCREF(c->second.m_fnc);
						call_list.push_back(call_entry(c->second.m_fnc, pArgs));
					}
				}
			}
			else
			{
				//eDebug("[eActionMap]   python wildcard.");
				ePyObject pArgs = PyTuple_New(2);
				PyTuple_SET_ITEM(pArgs, 0, PyInt_FromLong(key));
				PyTuple_SET_ITEM(pArgs, 1, PyInt_FromLong(flags));
				Py_INCREF(c->second.m_fnc);
				call_list.push_back(call_entry(c->second.m_fnc, pArgs));
			}
		}
	}

	int res = 0;
	// iterate over all to not loose a reference
	for (std::vector<call_entry>::iterator i(call_list.begin()); i != call_list.end(); ++i)
	{
		if (i->m_fnc)
		{
			if (!res)
				res = ePython::call(i->m_fnc, i->m_arg);
			Py_DECREF(i->m_fnc);
			Py_DECREF(i->m_arg);
		}
		else if (i->m_widget && !res)
			res = i->m_widget->event(eWidget::evtAction, (void*)i->m_widget_arg, (void*)i->m_widget_arg2 );
	}
}

ePtr<eActionMap> NewActionMapPtr(void)
{
	ePtr<eActionMap> ptr;
	eActionMap::getInstance(ptr);
	return ptr;
}

eAutoInitPtr<eActionMap> init_eActionMap(eAutoInitNumbers::actions, "eActionMap");
