#ifndef __eskin_h
#define __eskin_h

#include <list>
#include <map>
#include <xmltree.h>

#include <lib/base/estring.h>
#include <lib/base/eptrlist.h>
#include <lib/gdi/grc.h>

class eWidget;
class gPixmap;
typedef eWidget *(*tWidgetCreator)(eWidget *parent);

struct eNamedColor
{
	eString name;
	gRGB value, end;
	int index;
	int size;
};

class eSkin
{
	typedef ePtrList<XMLTreeParser> parserList;
	parserList parsers;
	void clear();
	
	int parseColor(const eString& name, const char *color, gRGB &col);
	int parseColors(XMLTreeNode *colors);
	int parseScheme(XMLTreeNode *scheme);
	int parseImages(XMLTreeNode *images);
	int parseImageAlias(XMLTreeNode *images);
	int parseValues(XMLTreeNode *values);
	int parseFonts(XMLTreeNode *fonts);
	int parseFontAlias(XMLTreeNode *fonts);
	
	gDC *getDCbyName(const char *name);
	
	gRGB *palette;
	int maxcolors;
	gImage *paldummy;
	int *colorused;
	
	static std::map< eString, tWidgetCreator > widget_creator;
	int build(eWidget *widget, XMLTreeNode *rootwidget);
	
	std::list<eNamedColor> colors;
	std::map<eString, gColor> scheme;
	std::map<eString, ePtr<gPixmap> > images;
	std::map<eString, int> values;
	std::map<eString, eString> fonts;
	std::map<eString, gFont> fontAlias;
	std::map<eString, eString> imageAlias;

	eNamedColor *searchColor(const eString &name);

	static eSkin *active;
public:
	eSkin();
	~eSkin();

	static void addWidgetCreator(const eString &name, tWidgetCreator creator);
	static void removeWidgetCreator(const eString &name, tWidgetCreator creator);

	int load(const char *filename);
	void parseSkins();
	
	int build(eWidget *widget, const char *name);
	void setPalette(gPixmapDC *pal);

	gColor queryColor(const eString &name);
	gColor queryScheme(const eString &name) const;
	RESULT queryImage(ePtr<gPixmap> &pixmap, const eString &name) const;
	int queryValue(const eString &name, int d) const;
	gFont queryFont(const eString &name);
	
	void makeActive();
	
	static eSkin *getActive();
};

#define ASSIGN(v, t, n) \
  v =(t*)search(n); if (! v ) { eWarning("skin has undefined element: %s", n); v=new t(this); }

#endif
