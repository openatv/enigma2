#include <lib/gui/elabel.h>

#include <lib/gdi/fb.h>
#include <lib/gdi/font.h>
#include <lib/gdi/lcd.h>
#include <lib/gui/eskin.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>

eLabel::eLabel(eWidget *parent, int flags, int takefocus, const char *deco ):
	eDecoWidget(parent, takefocus, deco), blitFlags(0), flags(flags),
	para(0), align( eTextPara::dirLeft ), shortcutPixmap(0)
{
}

eLabel::~eLabel()
{
	if (para)
	{
		para->destroy();
		para=0;
	}
}

void eLabel::setPixmapPosition( const ePoint &p )
{
	pixmap_position = p;
	invalidate();
}

void eLabel::validate( const eSize* s )
{
	if (!para)
	{
		if (s)
			para=new eTextPara( eRect(text_position.x(), text_position.y(), s->width() - text_position.x(), s->height() - text_position.y()));
		else
			para=new eTextPara( eRect(text_position.x(), text_position.y(), size.width() - text_position.x(), size.height() - text_position.y()));

		para->setFont(font);
		para->renderString(text, flags);
		para->realign(align);
  }
}

void eLabel::invalidate()
{
	if (para)
	{
		para->destroy();
		para=0;
	}
	if (isVisible())
		eDecoWidget::invalidate();  // we must redraw...
}

void eLabel::setFlags(int flag)
{
	flags|=flag;
	if (flag)
		invalidate();
}

void eLabel::setBlitFlags( int flags )
{
	blitFlags |= flags;
}

void eLabel::removeFlags(int flag)
{
	flags &= ~flag;
	if (flag)
		invalidate();
}

void eLabel::setAlign(int align)
{
	this->align = align;
	invalidate();
}

void eLabel::redrawWidget(gPainter *target, const eRect &rc)
{
/*	eDebug("decoStr = %s, text=%s, name=%s, %p left = %d, top = %d, width=%d, height = %d", strDeco?strDeco.c_str():"no", text?text.c_str():"no" , name?name.c_str():"no", this, this->getPosition().x(), this->getPosition().y(), this->getSize().width(), this->getSize().height() ); 
	eDebug("renderContext left = %d, top = %d, width = %d, height = %d", rc.left(), rc.top(), rc.width(), rc.height() );*/

	target->clip( rc );
	eRect area=eRect(ePoint(0, 0), ePoint(width(), height()));
/*	eDebug("area left = %d, top = %d, width = %d, height = %d",
		area.left(), area.top(),
		area.width(), area.height() );*/

	if (deco_selected && have_focus)
	{
		deco_selected.drawDecoration(target, ePoint(width(), height()));
		area=crect_selected;
	} else if (deco)
	{
		deco.drawDecoration(target, ePoint(width(), height()));
		area=crect;
	}
/*	eDebug("area left = %d, top = %d, width = %d, height = %d",
		area.left(), area.top(),
		area.width(), area.height() );*/

	if (shortcutPixmap)
	{
		//area.setWidth(area.width()-area.height());
		area.setX(area.height());
	}

	if (text.length())
	{
		if ( area.size().height() < size.height() ||
				area.size().width() < size.width() )
		{
		// then deco is drawed
			eSize s=area.size();
			validate( &s );
		} else
			validate();

		if (flags & flagVCenter)
			yOffs = ( (area.height() - para->getBoundBox().height() ) / 2 + 0) - para->getBoundBox().top();
		else
			yOffs = 0;

		eWidget *w;
		if ((blitFlags & BF_ALPHATEST) && (transparentBackgroundColor >= 0))
		{
			w=this;
			target->setBackgroundColor(transparentBackgroundColor);
		} else
		{
			w=getNonTransparentBackground();
			target->setBackgroundColor(w->getBackgroundColor());
		}
		target->setFont(font);
		target->renderPara(*para, ePoint( area.left(), area.top()+yOffs) );
	}
	if (pixmap)
	{
//		eDebug("blit pixmap area left=%d, top=%d, right=%d, bottom=%d", rc.left(), rc.top(), rc.right(), rc.bottom() );
//		eDebug("pixmap_pos x = %d, y = %d, xsize=%d, ysize=%d", pixmap_position.x(), pixmap_position.y(), pixmap->x, pixmap->y );
		target->blit(pixmap, shortcutPixmap?pixmap_position+ePoint( area.left(), 0):pixmap_position, area, (blitFlags & BF_ALPHATEST) ? gPixmap::blitAlphaTest : 0);
	}
	if (shortcutPixmap)
		target->blit(shortcutPixmap, 
				ePoint((area.height()-shortcutPixmap->x)/2, area.top()+(area.height()-shortcutPixmap->y)/2),
				eRect(),
				gPixmap::blitAlphaTest);
	target->clippop();
}

int eLabel::eventHandler(const eWidgetEvent &event)
{
	switch (event.type)
	{
		case eWidgetEvent::changedFont:
		case eWidgetEvent::changedText:
		if (para)
		{
			para->destroy();
			para=0;
		}
		if ( have_focus && deco_selected )
			eDecoWidget::invalidate( crect_selected );
		else if ( deco )
			eDecoWidget::invalidate( crect );
		else
			eDecoWidget::invalidate();
	break;

	case eWidgetEvent::changedSize:
		invalidate();
	break;

	default:
		return eDecoWidget::eventHandler(event);
		break;
	}
	return 1;
}

eSize eLabel::getExtend()
{
	validate();
	return eSize(para->getBoundBox().width()+(shortcutPixmap?shortcutPixmap->x*2:0), para->getBoundBox().height());
}

ePoint eLabel::getLeftTop()
{
	validate();
	return ePoint(para->getBoundBox().left(), para->getBoundBox().top());
}

int eLabel::setProperty(const eString &prop, const eString &value)
{
	if (prop=="wrap" && value == "on")
		setFlags(RS_WRAP);
	else if (prop=="alphatest" && value == "on")
	{
		transparentBackgroundColor=getBackgroundColor();
		setBackgroundColor(-1);
		blitFlags |= BF_ALPHATEST;
	} else if (prop=="align")
	{
		if (value=="left")
			setAlign(eTextPara::dirLeft);
		else if (value=="center")
			setAlign(eTextPara::dirCenter);
		else if (value=="right")
			setAlign(eTextPara::dirRight);
		else if (value=="block")
			setAlign(eTextPara::dirBlock);
		else
			setAlign(eTextPara::dirLeft);
	}
	else if (prop=="vcenter")
		setFlags( flagVCenter );
	else if (prop == "shortcut")
	{
		setShortcutPixmap(value);
		return eWidget::setProperty(prop, value);
	} else
		return eDecoWidget::setProperty(prop, value);
	return 0;
}

void eLabel::setShortcutPixmap(const eString &shortcut)
{
	eSkin::getActive()->queryImage(shortcutPixmap, "shortcut." + shortcut);
}

static eWidget *create_eLabel(eWidget *parent)
{
	return new eLabel(parent);
}

class eLabelSkinInit
{
public:
	eLabelSkinInit()
	{
		eSkin::addWidgetCreator("eLabel", create_eLabel);
	}
	~eLabelSkinInit()
	{
		eSkin::removeWidgetCreator("eLabel", create_eLabel);
	}
};

eAutoInitP0<eLabelSkinInit> init_eLabelSkinInit(eAutoInitNumbers::guiobject, "eLabel");
