#ifndef __ewidget_h
#define __ewidget_h

#include <lib/base/ebase.h>
#include <lib/base/estring.h>
#include <lib/gdi/epoint.h>
#include <lib/gdi/esize.h>
#include <lib/gdi/erect.h>
#include <lib/base/eptrlist.h>
#include <libsig_comp.h>
#include <lib/gdi/grc.h>
#include <lib/driver/rc.h>
#include <lib/gui/actions.h>

class eWidgetEvent
{
public:
	enum eventType
	{
		evtKey,
		willShow, willHide,
		execBegin, execDone,
		gotFocus, lostFocus,
		
		changedText, changedFont, changedForegroundColor, changedBackgroundColor,
		changedSize, changedPosition, changedPixmap, childChangedHelpText,

		evtAction, evtShortcut
	} type;
	union
	{
		int parameter;
		const eAction *action;
		const eRCKey *key;
	}; 
	eWidgetEvent(eventType type, int parameter=0): type(type), parameter(parameter) { }
	eWidgetEvent(eventType type, const eAction *action): type(type), action(action) { }
	eWidgetEvent(eventType type, const eRCKey &key): type(type), key(&key) { }
	
	/**
	 * \brief Event should be delivered to the focused widget.
	 *
	 * \return true if the event should be delivered to the focused widget instead of the widget itself.
	 */
	int toFocus() const
	{
		switch (type)
		{
		case evtKey:
			return 1;
		default:
			return 0;
		}
	}
};

/** \brief The main widget class. All widgets inherit this class.
 * eWidget handles focus management.
 */
class eWidget: public Object
{
	enum
	{
		/// Widget was shown with show() or implicit show()
		stateShow=1,
		/// Widget is visible on screen. Implies stateShow.
		stateVisible=2
	};
	
public:
	/**
	 * \brief Exits a (model) widget.
	 *
	 * Quit the local event loop, thus returning the control to the function which called \a exec.
	 * \sa eWidget::accept
	 * \sa eWidget::reject
	 */
	void close(int result);
	
	/**
	 * \brief Closes with a returncode of 0 (success).
	 *
	 * Synonym to \a close(0);. Useful to use as a slot.
	 * \sa eWidget::close
	 */
	void accept();

	/**
	 * \brief Closes with a returncode of -1 (failure).
	 *
	 * Synonym to \a close(-1);. Useful to use as a slot.
	 * \sa eWidget::close
	 */
	void reject();
	/**
	 * \brief Signal is send, when the focus Changed
	 *
	 * used from a existing statusbar.
	 * \sa eWidget::focusChanged
	 */
	Signal1<void, const eWidget*> focusChanged;
	static Signal2< void, ePtrList<eAction>*, int > showHelp;
protected:
	ePtrList<eAction> actionHelpList;
	int helpID;
	ePtrList<eWidget> childlist;
	static eWidget *root;
	eWidget *parent;
	eString name;
	eString helptext;
	ePoint position;
	ePoint absPosition;
	eSize size;
	eRect clientrect;
	eRect clientclip;
	
	eAction *shortcut;
	eWidget *shortcutFocusWidget;

	ePtrList<eWidget> _focusList;
	
	ePtrList<eWidget> actionListener;
	eWidget *focus, *TLW;

		/// old top-level focus
	eWidget *oldTLfocus;
	int takefocus;
	int state;
	
	gDC *target;

	inline eWidget *getTLW() // pseudoTLW !!
	{
		return TLW ? TLW : (TLW = (parent && parent->parent) ? parent->getTLW() : this );
	}
	int result, in_loop, have_focus, just_showing;
	void takeFocus();
	void releaseFocus();

	void _willShow();
	void _willHide();
	
	virtual void willShow();
	virtual void willHide();
	
	virtual void setPalette();

	void willShowChildren();
	void willHideChildren();
	
	/**
	 * \brief Hi priority event filter.
	 *
	 * This event filter is called before the event is delivered via \a event.
	 * \return 1 if the event should NOT be forwarded.
	 */
	virtual int eventFilter(const eWidgetEvent &event);

	/**
	 * \brief Handles an event.
	 *
	 * If re-implemented in a widget-sub-class, \c eWidget::event should be called whenever the event is
	 * not processed by the widget.
	 * \return 1 if the event was processed, 0 if ignored. it might be forwarded to other widgets then.
	 */

	virtual int keyDown(int rc);
	virtual int keyUp(int rc);

	virtual void gotFocus();
	virtual void lostFocus();
	
	virtual void recalcClientRect();
	void recalcClip();
	void checkFocus();

	typedef ePtrList<eActionMap> actionMapList;

	void findAction(eActionPrioritySet &prio, const eRCKey &key, eWidget *context);
	void addActionMap(eActionMap *map);
	void removeActionMap(eActionMap *map);
	actionMapList actionmaps;
	static actionMapList globalActions;

			// generic properties
	gFont font;
	eString text;
	gColor backgroundColor, foregroundColor;
	
	ePtr<gPixmap> pixmap;

	eString descr;

public:
	virtual int eventHandler(const eWidgetEvent &event);
	static void addGlobalActionMap(eActionMap *map);
	static void removeGlobalActionMap(eActionMap *map);
	inline eWidget *getNonTransparentBackground()
	{
		if (backgroundColor >= 0)
			return this;
		return parent?parent->getNonTransparentBackground():this;
	}

#ifndef DISABLE_LCD
	eWidget *LCDTitle;
	eWidget *LCDElement;
	eWidget *LCDTmp;
#endif

	void recalcAbsolutePosition();

	inline const ePoint &getAbsolutePosition() const
	{
		return absPosition;
	}

	inline ePoint getRelativePosition(eWidget *e) const
	{
		ePoint pos=position;
		if (this != e)
			for (eWidget *a=parent; a && (a != e); a=a->parent)
				pos+=a->clientrect.topLeft();
		return pos;
	}

	virtual void redrawWidget(gPainter *target, const eRect &area);

	virtual void eraseBackground(gPainter *target, const eRect &area);

	/**
	 * \brief Constructs a new eWidget. 
	 * \param parent The parent widget. The widget gets automatically removed when the parent gets removed.
	 * \param takefocus Specifies if the widget should be appended to the focus list of the TLW, i.e. if it can
	          receive keys.
	 */
	eWidget(eWidget *parent=0, int takefocus=0);

	/**
	 * \brief Destructs an eWidget and all its childs.
	 *
	 * hide() is called when the widget is shown. The set ePixmap is \e not
	 * freed. If the widget acquired focus, it will be removed from the focuslist.
	 * \sa eWidget::setPixmap
	 */
	virtual ~eWidget();
	
	/**
	 * \brief Returns a pointer to the focus list.
	 *
	 * The focus list is the list of childs which have the \c takefocus flag set.
	 * This list is only maintained for TLWs.
	 */
	ePtrList<eWidget> *focusList() { return &_focusList; }

	/**
	 * \brief Resizes the widget.
	 *
	 * Sets the size of the widget to the given size. The event \c changedSize event will be generated.
	 * \param size The new size, relative to the position.
	 */
	void resize(const eSize& size);
	
	/**
	 * \brief Resizes clientrect (and the widget).
	 *
	 * Sets the clientrect of the widget to the given size. The real size of the widget will be set to met
	 * these requirement. The event \c changedSize event will be generated.
	 * \param size The new size of the clientrect, relative to the position.
	 */
	void cresize(const eSize& size);
	
	/**
	 * \brief Moves the widget.
	 *
	 * Set the new position of the widget to the given position. The \c changedPosition event will be generated.
	 * \param position The new position, relative to the parent's \c clientrect.
	 */
	void move(const ePoint& position);
	
	/**
	 * \brief Moves the clientrect (and the widget).
	 *
	 * Set the new position of the clientrect to the given position. The \c changedPosition event will be generated.
	 * \param position The new position, relative to the parent's \c clientrect.
	 */
	void cmove(const ePoint& position);
	
	/**
	 * \brief Returns the current size.
	 *
	 * \return Current size of the widget, relative to the position.
	 */
	const eSize& getSize() const { return size; }
	
	/** 
	 * \brief Returns the current position.
	 *
	 * \return Current position, relative to the parent's \c clientrect.
	 */
	const ePoint& getPosition() const { return position; }
	
	/**
	 * \brief Returns the size of the clientrect.
	 *
	 * \return The usable size for the childwidgets.
	 */
	eSize getClientSize() const { return clientrect.size(); }
	
	/**
	 * \brief Returns the clientrect.
	 *
	 * \return The area usable for the childwidgets.
	 */
	const eRect& getClientRect() const { return clientrect; }

	/**
	 * \brief Recursive redraw of a widget.
	 *
	 * All client windows get repaint too, but no widgets above. Unless you have a good reason, you shouldn't
	 * use this function and use \c invalidate().
	 * \param area The area which should be repaint. The default is to repaint the whole widget.
	 * \sa eWidget::invalidate
	 */
	void redraw(eRect area=eRect());
	
	/**
	 * \brief Recursive (complete) redraw of a widget.
	 *
	 * Redraws the widget including background. This is the function to use if you want to manually redraw something!
	 * \param area The area which should be repaint. The default is to repaint the whole widget.
	 * \param force Forces a parent-invalidate even on non-visible widgets. Shouldn't be used outside eWidget.
	 * \sa eWidget::redraw
	 */
	void invalidate(eRect area=eRect(), int force=0);
	
	/**
	 * \brief Enters modal message loop.
	 *
	 * A new event loop will be launched. The function returns when \a close is called.
	 * \return The argument of \a close.
	 * \sa eWidget::close
	 */
	int exec();
	
	/**
	 * \brief Visually clears the widget.
	 *
	 * Clears the widget. This is done on \a hide().
	 * \sa eWidget::hide
	 */
	void clear();
	
	/**
	 * \brief Delivers a widget-event.
	 *
	 * Internally calles \a eventFilter, then \a eventHandler() (in some cases of the focused widget)
	 * \param event The event to deliver.
	 */
	int event(const eWidgetEvent &event);
	
	/**
	 * \brief Shows the widget.
	 *
	 * If necessary, the widget will be linked into the TLW's active focus list. The widget will
	 * visually appear.
	 * \sa eWidget::hide
	 */
	void show();
	
	/** 
	 * \brief Hides the widget.
	 *
	 * The widget will be removed from the screen. All childs will be hidden too.
	 * \sa eWidget::show
	 */
	void hide();
	
	/** 
	 * \brief Returns if the widget is vissible.
	 *
	 * \return If the widget and all parents are visible, \c true is returned, else false.
	 */
	int isVisible()	{		return (state&stateVisible) && ( (!parent) || parent->isVisible() );	}
	
	/**
	 * \brief Possible focus directions.
	 */
	enum focusDirection
	{
		focusDirNext, focusDirPrev, focusDirN, focusDirE, focusDirS, focusDirW
	};

	/**
	 * \brief changes the focused widget.
	 *
	 * Focuses the next or previous widget of the \c focuslist. An \c gotFocus and \c lostFocus event will be
	 * generated.
	 * \param dir The direction, \c focusDirection.
	 */
	void focusNext(int dir=0);
	
	/**
	 * \brief Gives focus to a widget.
	 *
	 * Set the focus to the specified widget. The \c focuslist is updated, too.
	 * An \c gotFocus and \c lostFocus event will be generated.
	 * \param newfocus The new widget to focus.
	 */
	void setFocus(eWidget *newfocus);
	
	/**
	 * \brief Sets the widget font.
	 *
	 * The font is used for example by the \c eLabel.
	 * \sa eLabel
	 * \param font The new font used by widget-specific drawing code.
	 */
	void setFont(const gFont &font);
	
	/**
	 * \brief Sets the widget caption or text.
	 *
	 * \param label The text to assign to the widget.
	 */
	void setText(const eString &label);
	
	const eString& getText() const { return text; }
	void setBackgroundColor(const gColor& color, bool inv=true);
	void setForegroundColor(const gColor& color, bool inv=true);
	void setPixmap(gPixmap *pmap);
	void setTarget(gDC *target);
	gDC *getTarget() { return target; }

#ifndef DISABLE_LCD
	void setLCD(eWidget *lcdtitle, eWidget *lcdelement);
#endif

	void setName(const char *name);
	const eString& getName() const { return name; }
	eWidget*& getParent() { return parent; }
	const gFont& getFont() const { return font; }
	
	const gColor& getBackgroundColor() const { return backgroundColor; }
	const gColor& getForegroundColor() const { return foregroundColor; }
	
	int width() { return getSize().width(); }
	int height() { return getSize().height(); }
	
	gPainter *getPainter(eRect area);

	const eString& getHelpText() const	{	return helptext;	}

	void setHelpText( const eString&);
	/**
	 * \brief Sets a property.
	 *
	 * A property is a value/data pair which is used for serializing widgets (like in skinfiles).
	 * These properties are available to all \c "eWidget"-based classes.
	 * \arg \c position, the position of the widget, relative to the parent's childarea. Consider using csize for TLWs.
	 * Positions are specified in a "x:y" manner.
	 * \arg \c cposition, the position of the widget's clientrect (upper left). 
	 * This is useful for specifing a position independant of a decoration which might be
	 * different sized. The real position will be calculated to match the requested position.
	 * \arg \c size, the size of the widget. Consider using csize for TLWs. Sizes are specified in a "width:height" manner.
	 * \arg \c csize, the size of the clientrect. The real size will be calculated to match the requested size.
	 * \arg \c text, the text/caption of the widget.
	 * \arg \c font, the primary font used in the widget.
	 * \arg \c name, the name of the widget for referring them.
	 * \arg \c pixmap, an already loaded, named pixmap to be used as the widget's pixmap.
	 * \arg \c foregroundColor, a named color, which will be used for the widget's foreground color.
	 * \arg \c backgroundColor
	 * \param prop The property to be set.
	 * \param value The value to be set.
	 */
	virtual int setProperty(const eString &prop, const eString &value);
	
	eWidget *search(const eString &name);

	eWidget* getFocus() { return focus; }
	
	void makeRoot();
	
	void zOrderLower();
	void zOrderRaise();
	
	/**
	 * \brief sets the shortcut (generate evtShortcut)
	 */
	void setShortcut(const eString &shortcut);
	void setShortcutFocus(eWidget *focus);
	
	void addActionToHelpList(eAction *action);
	void clearHelpList();
	void setHelpID(int fHelpID);
};

#endif
