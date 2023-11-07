#include <lib/gui/elistbox.h>
struct eActionList
{
	const char *m_context, *m_action;
	int m_id;
} actions[]={
	{"ListboxActions", "moveUp", eListbox::moveUp},
	{"ListboxActions", "moveDown", eListbox::moveDown},
	{"ListboxActions", "moveTop", eListbox::moveTop},
	{"ListboxActions", "moveBottom", eListbox::moveBottom},
	{"ListboxActions", "movePageUp", eListbox::movePageUp},
	{"ListboxActions", "movePageDown", eListbox::movePageDown},
	{"ListboxActions", "justCheck", eListbox::justCheck},
	{"ListboxActions", "refresh", eListbox::refresh},
	{"ListboxActions", "moveLeft", eListbox::moveLeft},
	{"ListboxActions", "moveRight", eListbox::moveRight},
	{"ListboxActions", "moveFirst", eListbox::moveFirst},
	{"ListboxActions", "moveLast", eListbox::moveLast},
	{"ListboxActions", "movePageLeft", eListbox::movePageLeft},
	{"ListboxActions", "movePageRight", eListbox::movePageRight},
	{"ListboxActions", "moveEnd", eListbox::moveEnd},
	{"ListboxActions", "pageUp", eListbox::pageUp},
	{"ListboxActions", "pageDown", eListbox::pageDown},
};