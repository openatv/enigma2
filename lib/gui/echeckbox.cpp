#include <lib/gui/echeckbox.h>

#include <lib/gdi/font.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/gui/eskin.h>

eCheckbox::eCheckbox(eWidget *parent, int checked, int takefocus, bool swapTxtPixmap, const char *deco)
	:eButton(parent, 0, takefocus, deco), swapTxtPixmap(swapTxtPixmap)
{
	align=eTextPara::dirLeft;
	ischecked = -1;
	setCheck(checked);
	CONNECT(selected, eCheckbox::sel);
}

eCheckbox::~eCheckbox()
{
}

void eCheckbox::sel()
{
	setCheck(ischecked?0:1);
	/*emit*/ checked(ischecked);
}

void eCheckbox::gotFocus()
{
#ifndef DISABLE_LCD
	if (parent && parent->LCDElement)
	{
		LCDTmp = new eLabel(parent->LCDElement);
		LCDTmp->hide();
		eSize s = parent->LCDElement->getSize();
		LCDTmp->move(ePoint(0,0));
		LCDTmp->resize(eSize(s.width(), s.height()));
		((eLabel*)LCDTmp)->setFlags(RS_WRAP);
		ePtr<gPixmap> pm;
		eSkin::getActive()->queryImage(pm, ischecked?"eCheckboxLCD.checked":"eCheckboxLCD.unchecked");
		LCDTmp->setPixmap(pm);
		((eLabel*)LCDTmp)->pixmap_position=ePoint(0, (size.height()-15)/2);
		((eLabel*)LCDTmp)->text_position=ePoint(21, 0);
		LCDTmp->setText(text);
		LCDTmp->show();
	}
#endif
	setForegroundColor(focusF, false);
	setBackgroundColor(focusB);
//	invalidate();
}

void eCheckbox::lostFocus()
{
#ifndef DISABLE_LCD
	if (LCDTmp)
	{
		delete LCDTmp;
		LCDTmp = 0;
	}
#endif
	eButton::lostFocus();
}


void eCheckbox::setCheck(int c)
{
	if (ischecked != -1 && ischecked == c)
		return;

	ischecked=c;

	ePtr<gPixmap> pixmap;
	eSkin::getActive()->queryImage(pixmap, ischecked?"eCheckbox.checked":"eCheckbox.unchecked");
	setPixmap(pixmap);
#ifndef DISABLE_LCD
	eSkin::getActive()->queryImage(pixmap, ischecked?"eCheckboxLCD.checked":"eCheckboxLCD.unchecked");
	if (LCDTmp)
		LCDTmp->setPixmap(pixmap);
#endif
}

int eCheckbox::setProperty(const eString &prop, const eString &value)
{
	if (prop=="swaptxtpixmap")	
	{
		swapTxtPixmap = (value != "off");
		event( eWidgetEvent::changedSize );
	}
	else
		return eButton::setProperty(prop, value);
	return 0;
}

int eCheckbox::eventHandler(const eWidgetEvent &event)
{
	switch (event.type)
	{
	case eWidgetEvent::changedSize:
		if (swapTxtPixmap)
		{
			text_position=ePoint(0,0);
			eLabel::invalidate();
			validate();
			pixmap_position=ePoint( para->getBoundBox().right()+5, (size.height()-pixmap->y) / 2 );
		}
		else
		{
			pixmap_position=ePoint(0, (size.height()-pixmap->y)/2);
			text_position=ePoint((int)(pixmap->x*1.25), 0);
		}
		//return eButton::eventHandler(event); // changed Size must seen by eLabel...
		break;

	default:
		return eButton::eventHandler(event);
	}
	return 1;
}

static eWidget *create_eCheckbox(eWidget *parent)
{
	return new eCheckbox(parent);
}

class eCheckboxSkinInit
{
public:
	eCheckboxSkinInit()
	{
		eSkin::addWidgetCreator("eCheckbox", create_eCheckbox);
	}
	~eCheckboxSkinInit()
	{
		eSkin::removeWidgetCreator("eCheckbox", create_eCheckbox);
	}
};

eAutoInitP0<eCheckboxSkinInit> init_eCheckboxSkinInit(eAutoInitNumbers::guiobject, "eCheckbox");
