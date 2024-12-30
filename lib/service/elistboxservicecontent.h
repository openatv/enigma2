/*
Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License

Copyright (c) 2023-2025 jbleyel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
1. Non-Commercial Use: You may not use the Software or any derivative works
   for commercial purposes without obtaining explicit permission from the
   copyright holder.
2. Share Alike: If you distribute or publicly perform the Software or any
   derivative works, you must do so under the same license terms, and you
   must make the source code of any derivative works available to the
   public.
3. Attribution: You must give appropriate credit to the original author(s)
   of the Software by including a prominent notice in your derivative works.
THE SOFTWARE IS PROVIDED "AS IS," WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE, AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT, OR OTHERWISE,
ARISING FROM, OUT OF, OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more details about the CC BY-NC-SA 4.0 License, please visit:
https://creativecommons.org/licenses/by-nc-sa/4.0/
*/

#ifndef __lib_service_elistboxservicecontent_h
#define __lib_service_elistboxservicecontent_h

#include <lib/gdi/gpixmap.h>
#include <lib/gui/elistbox.h>
#include <lib/gui/elistboxcontent.h>
#include <lib/service/iservice.h>
#include <lib/python/python.h>
#include <set>
#include <lib/nav/core.h>

class eListboxPythonServiceContent : public eListboxPythonMultiContent
{
	DECLARE_REF(eListboxPythonServiceContent);

public:
	eListboxPythonServiceContent();

	void addService(const eServiceReference &ref, bool beforeCurrent = false);
	void removeCurrent();
	void FillFinished();

	void setRoot(const eServiceReference &ref, bool justSet = false);
	void setRecordIndicatorMode(int mode) { m_record_indicator_mode = mode; }
	void setHideNumberMarker(bool doHide) { m_hide_number_marker = doHide; }
	void setHideMarker(bool doHide) { m_hide_marker = doHide; }
	void setNumberingMode(int numberingMode) { m_numbering_mode = numberingMode; }

	void getCurrent(eServiceReference &ref);
	void getPrev(eServiceReference &ref);
	void getNext(eServiceReference &ref);

	int getNextBeginningWithChar(char c);
	int getPrevMarkerPos();
	int getNextMarkerPos();

	/* support for marked services */
	void initMarked();
	void addMarked(const eServiceReference &ref);
	void removeMarked(const eServiceReference &ref);
	int isMarked(const eServiceReference &ref);

	/* this is NOT thread safe! */
	void markedQueryStart();
	int markedQueryNext(eServiceReference &ref);

	int lookupService(const eServiceReference &ref);
	bool setCurrent(const eServiceReference &ref);

	void sort();

	int setCurrentMarked(bool);
	bool isCurrentMarked();

	void refresh();

protected:
	bool getIsMarked(int selected);
	void setBuildArgs(int selected);
	void cursorHome();
	void cursorEnd();
	int cursorMove(int count = 1);
	int cursorValid();
	int cursorSet(int n);
	int cursorResolve(int);
	int currentCursorSelectable();
	int cursorGet();

	void cursorSave();
	void cursorRestore();
	int size();

private:
	typedef std::list<eServiceReference> list;

	bool checkServiceIsRecorded(eServiceReference ref, pNavigation::RecordType type);

	std::map<int, ePtr<gFont>> m_fonts;

	list m_service_list;
	list::iterator m_service_cursor, m_saved_service_cursor;

	int m_size;

	eSize m_selectionsize;
	ePtr<iServiceHandler> m_service_center;
	ePtr<iListableService> m_lst;

	eServiceReference m_root;

	/* support for marked services */
	std::set<eServiceReference> m_marked;
	std::set<eServiceReference>::const_iterator m_marked_iterator;

	/* support for movemode */
	bool m_current_marked;
	void swapServices(list::iterator, list::iterator);

	bool isServiceHidden(int flags);

	bool m_hide_number_marker, m_hide_marker, m_record_indicator_mode;
	int m_numbering_mode;
};

#endif
