#include <stdio.h>
#include <errno.h>
#include <stdlib.h>

#include <lib/gui/eskin.h>
#include <lib/gui/ewidget.h>
#include <lib/gdi/gfbdc.h>
#include <lib/gdi/glcddc.h>
#include <lib/gdi/epng.h>
#include <lib/base/eerror.h>
#include <lib/gdi/font.h>
#include <lib/base/eptrlist.h>

std::map< eString,tWidgetCreator > eSkin::widget_creator;

eSkin *eSkin::active;

eNamedColor *eSkin::searchColor(const eString &name)
{
	for (std::list<eNamedColor>::iterator i(colors.begin()); i != colors.end(); ++i)
	{
		if (!i->name.compare(name))
			return &*i;
	}
	return 0;
}

void eSkin::clear()
{
}

void eSkin::addWidgetCreator(const eString &name, tWidgetCreator creator)
{
	widget_creator[name] = creator; // add this tWidgetCreator to map... if exist.. overwrite
}

void eSkin::removeWidgetCreator(const eString &name, tWidgetCreator creator)
{
	widget_creator.erase(name);
}

int eSkin::parseColor(const eString &name, const char* color, gRGB &col)
{
	if (color[0]=='#')
	{
		unsigned long vcol=0;
		if (sscanf(color+1, "%lx", &vcol)!=1)
		{
			eDebug("invalid color named \"%s\" (value: %s)", name.c_str(), color+1);
			return -1;
		}
		col.r=(vcol>>16)&0xFF;
		col.g=(vcol>>8)&0xFF;
		col.b=vcol&0xFF;
		col.a=(vcol>>24)&0xFF;
	} else
	{
		eNamedColor *n=searchColor(color);
		if (!n)
		{
			eDebug("invalid color named \"%s\" (alias to: \"%s\")", name.c_str(), color);
			return -1;
		}
		col=n->value;
	}
	return 0;
}

int eSkin::parseColors(XMLTreeNode *xcolors)
{
	XMLTreeNode *node;
	
	std::list<eNamedColor>::iterator newcolors=colors.end();
	
	for (node=xcolors->GetChild(); node; node=node->GetNext())
	{
		if (strcmp(node->GetType(), "color"))
		{
			eDebug("junk found in colorsection (%s)", node->GetType());
			continue;
		}
		
		const char *name=node->GetAttributeValue("name"), *color=node->GetAttributeValue("color"), *end=node->GetAttributeValue("end");

		if (!color || !name)
		{
			eDebug("no color/name specified");
			continue;
		}

		eNamedColor col;
		col.name=name;

		const char *size=node->GetAttributeValue("size");

		if (size)
			col.size=atoi(size);
		else
			col.size=0;
		
		if (!col.size)
			col.size=1;
		
		if ((col.size>1) && (!end))
		{
			eDebug("no end specified in \"%s\" but is gradient", name);
			continue;
		}

		if (parseColor(name, color, col.value))
			continue;

		if (end && parseColor(name, end, col.end))
			continue;

		colors.push_back(col);
		if (newcolors == colors.end())
			--newcolors;
	}
	
	for (std::list<eNamedColor>::iterator i(newcolors); i != colors.end(); ++i)
	{
		eNamedColor &col=*i;
		int d;
		for (d=0; d<maxcolors; d+=col.size)
		{
			int s;
			for (s=0; s<col.size; s++)
				if ((d+s>maxcolors) || colorused[d+s])
					break;
			if (s==col.size)
				break;
		}
		if (d==maxcolors)
			continue;
		col.index=gColor(d);
		for (int s=0; s<col.size; s++, d++)
		{
			colorused[d]=1;
			if (s)
			{
				int rdiff=-col.value.r+col.end.r;
				int gdiff=-col.value.g+col.end.g;
				int bdiff=-col.value.b+col.end.b;
				int adiff=-col.value.a+col.end.a;
				rdiff*=s; rdiff/=(col.size-1);
				gdiff*=s; gdiff/=(col.size-1);
				bdiff*=s; bdiff/=(col.size-1);
				adiff*=s; adiff/=(col.size-1);
				palette[d].r=col.value.r+rdiff;
				palette[d].g=col.value.g+gdiff;
				palette[d].b=col.value.b+bdiff;
				palette[d].a=col.value.a+adiff;
			} else
				palette[d]=col.value;
		}
	}
	return 0;
}

int eSkin::parseScheme(XMLTreeNode *xscheme)
{
	XMLTreeNode *node;
	for (node=xscheme->GetChild(); node; node=node->GetNext())
	{
		if (strcmp(node->GetType(), "map"))
		{
			eDebug("illegal scheme entry found: %s", node->GetType());
			continue;
		}
		char *name=node->GetAttributeValue("name"), *color=node->GetAttributeValue("color");
		if (!name || !color)
		{
			eDebug("no name or color specified in colorscheme");
			continue;
		}
		eString base=color;
		int offset=0, p;
		if ((p=base.find('+'))!=-1)
		{
			offset=atoi(base.mid(p).c_str());
			base=base.left(p);
		}
		eNamedColor *n=searchColor(base);
		if (!n)
		{
			eDebug("illegal color \"%s\" specified", base.c_str());
			continue;
		}
		scheme[name] = gColor(n->index+offset);
	}
	return 0;
}

int eSkin::parseFontAlias(XMLTreeNode *xscheme)
{
	XMLTreeNode *node;
	for (node=xscheme->GetChild(); node; node=node->GetNext())
	{
		if (strcmp(node->GetType(), "map"))
		{
			eDebug("illegal fontalias entry found: %s", node->GetType());
			continue;
		}
		char *font=node->GetAttributeValue("font"),
				 *name=node->GetAttributeValue("name"),
				 *size=node->GetAttributeValue("size");

		if (!name || !font || !size)
		{
			eDebug("no name, alias or size spezified in fontaliase");
			continue;
		}

		std::map<eString, gFont>::iterator it = fontAlias.find(name);
		if (it != fontAlias.end())
			continue;

		std::map<eString, eString>::iterator i = fonts.find(font);
		if (i == fonts.end())
		{
			eDebug("font %s not found, skip make alias %s", font, name);
			continue;
		}
		fontAlias[name]=gFont(i->second, atoi(size));
	}
	return 0;
}

int eSkin::parseImages(XMLTreeNode *inode)
{
	char *abasepath=inode->GetAttributeValue("basepath");
	if (!abasepath)
		abasepath="";
	eString basepath=eString("/enigma/pictures/");
	if (abasepath[0] == '/') // allow absolute paths
		basepath="";
	basepath+=abasepath;
	if (basepath[basepath.length()-1]!='/')
		basepath+="/";

	for (XMLTreeNode *node=inode->GetChild(); node; node=node->GetNext())
	{
		if (strcmp(node->GetType(), "img"))
		{
			eDebug("illegal image entry found: %s", node->GetType());
			continue;
		}
		const char *name=node->GetAttributeValue("name");
		if (!name)
		{
			eDebug("illegal <img> entry: no name");
			continue;
		}
		const char *src=node->GetAttributeValue("src");
		if (!src)
		{
			eDebug("image/img=\"%s\" no src given", name);
			continue;
		}
		std::map<eString, ePtr<gPixmap> >::iterator it = images.find(name);
		if (it != images.end())
		{
//			eDebug("Image with name %s already loaded, skip %s", name, src);
			continue;
		}
		ePtr<gPixmap> image=0;
		eString filename=basepath + eString(src);
		if (abasepath[0] != '/')
		{
			// search first in CONFIGDIR
			image=loadPNG((eString(CONFIGDIR)+filename).c_str());
			if (!image)
				image=loadPNG((eString(DATADIR)+filename).c_str());
		}
		else // abs path
			image=loadPNG(filename.c_str());

		if (!image)
		{
			eDebug("image/img=\"%s\" - %s: file not found", name, filename.c_str());
			continue;
		}

		if (paldummy && !node->GetAttributeValue("nomerge"))
		{
			gPixmapDC mydc(image);
			gPainter p(mydc);
			p.mergePalette(paldummy);
		}
		images[name] = image;
	}
	return 0;
}

int eSkin::parseImageAlias(XMLTreeNode *xvalues)
{
	for (XMLTreeNode *node=xvalues->GetChild(); node; node=node->GetNext())
	{
		if (strcmp(node->GetType(), "map"))
		{
			eDebug("illegal values entry %s", node->GetType());
			continue;
		}
		const char *name=node->GetAttributeValue("name"),
							 *img=node->GetAttributeValue("img");
		if (!name || !img)
		{
			eDebug("map entry has no name or img");
			continue;
		}
		std::map<eString, eString>::iterator it = imageAlias.find(name);
		if (it != imageAlias.end())
		{
			eDebug("imagealias %s does exist, skip make alias for image %s", name, img);
			continue;
		}
		std::map<eString, ePtr<gPixmap> >::iterator i = images.find(img);
		if (i == images.end())
		{
			eDebug("image %s not found, skip make alias %s", img , name);
			continue;
		}
		imageAlias[name]=img;
	}
	return 0;
}

int eSkin::parseFonts(XMLTreeNode *xfonts)
{
	const char *abasepath=xfonts->GetAttributeValue("basepath");
	eString basepath=abasepath?abasepath:FONTDIR;

	if (basepath.length())
		if (basepath[basepath.length()-1]!='/')
			basepath+="/";

	for (XMLTreeNode *node=xfonts->GetChild(); node; node=node->GetNext())
	{
		if (strcmp(node->GetType(), "font"))
		{
			eDebug("illegal fonts entry %s", node->GetType());
			continue;
		}
		const char *file=node->GetAttributeValue("file");
		if (!file)
		{
			eDebug("fonts entry has no file");
			continue;
		}
		const char *name=node->GetAttributeValue("name");
		if (!name)
		{
			eDebug("fonts entry has no name use filename %s as name", file);
			name = file;
		}
		std::map<eString, eString>::iterator it = fonts.find(name);
		const char *ascale=node->GetAttributeValue("scale");
		int scale=0;
		if (ascale)
			scale=atoi(ascale);
		if (!scale)
			scale=100;
		if (it != fonts.end())
		{
			eDebug("Font with name %s already loaded, skip %s", name, file);
			continue;
		}
		fonts[name]=fontRenderClass::getInstance()->AddFont(basepath+eString(file), name, scale);
		if (node->GetAttributeValue("replacement"))
			eTextPara::setReplacementFont(name);
	}
	return 0;
}

int eSkin::parseValues(XMLTreeNode *xvalues)
{
	for (XMLTreeNode *node=xvalues->GetChild(); node; node=node->GetNext())
	{
		if (strcmp(node->GetType(), "value"))
		{
			eDebug("illegal values entry %s", node->GetType());
			continue;
		}
		const char *name=node->GetAttributeValue("name");
		if (!name)
		{
			eDebug("values entry has no name");
			continue;
		}
		const char *value=node->GetAttributeValue("value");
		if (!value)
		{
			eDebug("values entry has no value");
			continue;
		}
		std::map<eString, int>::iterator it = values.find(name);
		if (it != values.end())
		{
			eDebug("value %s does exist, skip make value %s=%i", name, value);
			continue;
		}
		values[name]=atoi(value);
	}
	return 0;
}

gDC *eSkin::getDCbyName(const char *name)
{
	gPixmapDC *dc=0;
	if (!strcmp(name, "fb"))
		dc=gFBDC::getInstance();
#ifndef DISABLE_LCD
	else if (!strcmp(name, "lcd"))
		dc=gLCDDC::getInstance();
#endif
	return dc;
}

int eSkin::build(eWidget *widget, XMLTreeNode *node)
{
//	 eDebug("building a %s", node->GetType());
/*	 if (widget->getType() != node->GetType())
			return -1;*/
	
	for (XMLAttribute *attrib=node->GetAttributes(); attrib; attrib=attrib->GetNext())
	{
//		eDebug("setting %s := %s", attrib->GetName(), attrib->GetValue());
		if (widget->setProperty(attrib->GetName(), attrib->GetValue()))
		{
			eDebug("failed");
			return -1;
		}
	}
	for (XMLTreeNode *c=node->GetChild(); c; c=c->GetNext())
	{
		eWidget *w=0;

		const char *name=c->GetAttributeValue("name");

		if (name)
			w=widget->search(name);

		if (!w)
		{
			std::map< eString, tWidgetCreator >::iterator it = widget_creator.find(c->GetType());

			if ( it == widget_creator.end() )
			{
				eWarning("widget class %s does not exist", c->GetType());
				return -ENOENT;
			}
			w = (it->second)(widget);
		}
		if (!w)
		{
			// eDebug("failed.");
			return -EINVAL;
		}
		w->zOrderRaise();
		int err;
		if ((err=build(w, c)))
		{
			return err;
		}
	}
	return 0;
}

eSkin::eSkin()
{
	maxcolors=256;

	palette=new gRGB[maxcolors];
	
	memset(palette, 0, sizeof(gRGB)*maxcolors);
	paldummy=new gImage(eSize(1, 1), 8);
	paldummy->clut.data=palette;
	paldummy->clut.colors=maxcolors;

	colorused=new int[maxcolors];
	memset(colorused, 0, maxcolors*sizeof(int));
}

eSkin::~eSkin()
{
	if (active==this)
		active=0;

	clear();

	delete colorused;

	for (std::map<eString, ePtr<gPixmap> >::iterator it(images.begin()); it != images.end(); it++)
		delete it->second;	

	if (paldummy)
		delete paldummy;
}

int eSkin::load(const char *filename)
{
	eDebug("loading skin: %s", filename);
	FILE *in=fopen(filename, "rt");
	if (!in)
		return -1;

	parsers.push_front(new XMLTreeParser("ISO-8859-1"));
	XMLTreeParser &parser=*parsers.first();
	char buf[2048];

	int done;
	do
	{
		unsigned int len=fread(buf, 1, sizeof(buf), in);
		done=len<sizeof(buf);
		if (!parser.Parse(buf, len, done))
		{
			eDebug("parse error: %s at line %d",
				parser.ErrorString(parser.GetErrorCode()),
				parser.GetCurrentLineNumber());
			parsers.pop_front();
			fclose(in);
			return -1;
		}
	} while (!done);
	fclose(in);

	XMLTreeNode *root=parser.RootNode();
	if (!root)
		return -1;
	if (strcmp(root->GetType(), "eskin"))
	{
		eDebug("not an eskin");
		return -1;
	}
	
	return 0;
}

void eSkin::parseSkins()
{
	for (ePtrList<XMLTreeParser>::reverse_iterator it(parsers); it != parsers.rend(); it++)
	{
		XMLTreeNode *node=it->RootNode();
	
		for (node=node->GetChild(); node; node=node->GetNext())
			if (!strcmp(node->GetType(), "colors"))
				parseColors(node);
	 }

	for (ePtrList<XMLTreeParser>::reverse_iterator it(parsers); it != parsers.rend(); it++)
	{
		XMLTreeNode *node=it->RootNode();
	
		for (node=node->GetChild(); node; node=node->GetNext())
			if (!strcmp(node->GetType(), "colorscheme"))
				parseScheme(node);
	 }

	for (ePtrList<XMLTreeParser>::iterator it(parsers); it != parsers.end(); it++)
	{
		XMLTreeNode *node=it->RootNode();
	
		for (node=node->GetChild(); node; node=node->GetNext())
			if (!strcmp(node->GetType(), "fonts"))
				parseFonts(node);
	 }

	for (ePtrList<XMLTreeParser>::iterator it(parsers); it != parsers.end(); it++)
	{
		XMLTreeNode *node=it->RootNode();
	
		for (node=node->GetChild(); node; node=node->GetNext())
			if (!strcmp(node->GetType(), "fontalias"))
				parseFontAlias(node);
	 }

	for (ePtrList<XMLTreeParser>::iterator it(parsers); it != parsers.end(); it++)
	{
		XMLTreeNode *node=it->RootNode();
	
		for (node=node->GetChild(); node; node=node->GetNext())
			if (!strcmp(node->GetType(), "images"))
				parseImages(node);

	 }

	for (ePtrList<XMLTreeParser>::iterator it(parsers); it != parsers.end(); it++)
	{
		XMLTreeNode *node=it->RootNode();
	
		for (node=node->GetChild(); node; node=node->GetNext())
			if (!strcmp(node->GetType(), "imagealias"))
				parseImageAlias(node);

	 }

	for (ePtrList<XMLTreeParser>::iterator it(parsers); it != parsers.end(); it++)
	{
		XMLTreeNode *node=it->RootNode();
	
		for (node=node->GetChild(); node; node=node->GetNext())
			if (!strcmp(node->GetType(), "values"))
				parseValues(node);
	}
}


int eSkin::build(eWidget *widget, const char *name)
{
	for (parserList::iterator i(parsers.begin()); i!=parsers.end(); ++i)
	{
		XMLTreeNode *node=i->RootNode();
			node=node->GetChild();
		while (node)
		{
			if (!strcmp(node->GetType(), "object"))
			{
				const char *oname=node->GetAttributeValue("name");
				if (!std::strcmp(name, oname))
				{
					node=node->GetChild();
					return build(widget, node);
				}
			}
			node=node->GetNext();
		}
	}
	eDebug("didn't found it");
	return -ENOENT;
}

void eSkin::setPalette(gPixmapDC *pal)
{
	if (palette)
	{
		gPainter p(*pal);
		p.setPalette(palette, 0, 256);
	}
}

eSkin *eSkin::getActive()
{
	if (!active)
		eFatal("no active skin");
	return active;
}

void eSkin::makeActive()
{
	active=this;
}

gColor eSkin::queryScheme(const eString& name) const
{
	eString base=name;
	int offset=0, p;
	if ((p=base.find('+'))!=-1)
	{
		offset=atoi(base.mid(p).c_str());
		base=base.left(p);
	}

	std::map<eString, gColor>::const_iterator it = scheme.find(base);

	if (it != scheme.end())
		return it->second + offset;

//	eWarning("%s does not exist", name.c_str());
	
	return gColor(0);
}

RESULT eSkin::queryImage(ePtr<gPixmap> &ptr, const eString& name) const
{
	eString img;

	std::map<eString, eString>::const_iterator i = imageAlias.find(name);
		
	if (i != imageAlias.end())
		img = i->second;
	else
		img = name;

	std::map<eString, ePtr<gPixmap> >::const_iterator it = images.find(img);

	if (it != images.end())
		ptr = it->second;
	
	return 0;
}

int eSkin::queryValue(const eString& name, int d) const
{
	std::map<eString, int>::const_iterator it = values.find(name);

	if (it != values.end())
		return it->second;
	
	return d;
}

gColor eSkin::queryColor(const eString& name)
{
	char *end;

	int numcol=strtol(name.c_str(), &end, 10);

	if (!*end)
		return gColor(numcol);

	eString base=name;
	int offset=0, p;
	if ((p=base.find('+'))!=-1)
	{
		offset=atoi(base.mid(p).c_str());
		base=base.left(p);
	}

	eNamedColor *col=searchColor(base);

	if (!col)
	{
		return queryScheme(name);
	} else
		return col->index + offset;
}

gFont eSkin::queryFont(const eString& name)
{
	std::map<eString, gFont>::iterator it = fontAlias.find(name);  // check if name is a font alias
	
	if ( it != fontAlias.end() )		// font alias found
		return it->second;

	eString family;
	int size=0;

	unsigned int sem = name.rfind(';');		// check if exist ';' in name
	if (sem != eString::npos) 						// then exist
	{
		family=name.left(sem);	   	
		size = atoi( name.mid(sem+1).c_str() );
		if (size<=0)
			size=16;
	}
	
	std::map<eString, eString>::iterator i = fonts.find(family);   // check if family is a font name
	if ( i != fonts.end() ) // font exist
		return gFont(i->second, size);

	for (i = fonts.begin() ; i != fonts.end(); i++)				// as last check if family name is a complete font Face
		if ( i->second == family)
			return gFont(i->second, size);

	eFatal("Font %s does not exist", name.c_str() );			//  halt Programm now... Font does not exist

	return gFont();
}
