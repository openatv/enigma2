#include <lib/driver/rcsdl.h>
//#include <lib/actions/action.h>
#include <lib/base/init.h>
#include <lib/base/init_num.h>
#include <lib/driver/input_fake.h>

/*
 * eSDLInputDevice
 */

eSDLInputDevice::eSDLInputDevice(eRCDriver *driver) : eRCDevice("SDL", driver), m_escape(false), m_unicode(0)
{
}

eSDLInputDevice::~eSDLInputDevice()
{
}

void eSDLInputDevice::handleCode(long arg)
{
	const SDL_KeyboardEvent *event = (const SDL_KeyboardEvent *)arg;
	const SDL_keysym *key = &event->keysym;
	int km = input->getKeyboardMode();
	int code, flags;

	if (event->type == SDL_KEYDOWN) {
		m_unicode = key->unicode;
		flags = eRCKey::flagMake;
	} else {
		flags = eRCKey::flagBreak;
	}

	if (km == eRCInput::kmNone) {
		code = translateKey(key->sym);
		eDebug("[eSDLInputDevice] translated code: %d", code);
	} else {
		code = m_unicode;
		eDebug("[eSDLInputDevice] native virtual code: %d / sym: %d", code, key->sym);
		if ((code == 0) && (key->sym < 128)) {
			code = key->sym;
			eDebug("[eSDLInputDevice] ASCII code: %u", code);
		}

		if ((km == eRCInput::kmAscii) &&
		    ((code < SDLK_SPACE) ||
		     (code == 0x7e) ||
		     (code == SDLK_DELETE) ||
		     (code > 255))) {
			code = translateKey(key->sym);
		} else {
			// ASCII keys should only generate key press events
			if (flags == eRCKey::flagBreak)
				return;

			if (km == eRCInput::kmAscii) {
				// skip ESC c or ESC '[' c
				if (m_escape) {
					if (code != '[')
						m_escape = false;
					return;
				}
				if (code == SDLK_ESCAPE)
					m_escape = true;
			}
			flags |= eRCKey::flagAscii;
		}
	}

	eDebug("[eSDLInputDevice] code=%d (%#x) flags=%d (%#x)", code, code, flags, flags);
	input->keyPressed(eRCKey(this, code, flags));
}

const char *eSDLInputDevice::getDescription() const
{
	return "SDL";
}

int eSDLInputDevice::translateKey(SDLKey key)
{
	#define P(a)	case SDLK_##a: return KEY_##a
	#define P2(a,b)	case SDLK_##a: return KEY_##b

	switch (key) {
	P(BACKSPACE);
	P(TAB);
	P(CLEAR);
	P2(RETURN,ENTER);
	P(PAUSE);
	P2(ESCAPE,ESC);
	P(SPACE);
#if 0
	P(EXCLAIM);
	P(QUOTEDBL);
	P(HASH);
#endif
	P(DOLLAR);
#if 0
	P(AMPERSAND);
#endif
	P2(QUOTE,APOSTROPHE);
#if 0
	P(LEFTPAREN);
	P(RIGHTPAREN);
	P(ASTERISK);
	P(PLUS);
#endif
	P(COMMA);
	P(MINUS);
	P2(PERIOD,DOT);
	P(SLASH);
	P(0);
	P(1);
	P(2);
	P(3);
	P(4);
	P(5);
	P(6);
	P(7);
	P(8);
	P(9);
#if 0
	P(COLON);
#endif
	P(SEMICOLON);
#if 0
	P(LESS);
#endif
	P2(EQUALS,EQUAL);
#if 0
	P(GREATER);
#endif
	P(QUESTION);
#if 0
	P(AT);
#endif
	P2(LEFTBRACKET,LEFTBRACE);
	P(BACKSLASH);
	P2(RIGHTBRACKET,RIGHTBRACE);
	P2(CARET,GRAVE);
#if 0
	P(UNDERSCORE);
	P(BACKQUOTE);
#endif
	P2(a,A);
	P2(b,B);
	P2(c,C);
	P2(d,D);
	P2(e,E);
	P2(f,F);
	P2(g,G);
	P2(h,H);
	P2(i,I);
	P2(j,J);
	P2(k,K);
	P2(l,L);
	P2(m,M);
	P2(n,N);
	P2(o,O);
	P2(p,P);
	P2(q,Q);
	P2(r,R);
	P2(s,S);
	P2(t,T);
	P2(u,U);
	P2(v,V);
	P2(w,W);
	P2(x,X);
	P2(y,Y);
	P2(z,Z);
	P(DELETE);
#if 0
	P(WORLD_0);
	P(WORLD_1);
	P(WORLD_2);
	P(WORLD_3);
	P(WORLD_4);
	P(WORLD_5);
	P(WORLD_6);
	P(WORLD_7);
	P(WORLD_8);
	P(WORLD_9);
	P(WORLD_10);
	P(WORLD_11);
	P(WORLD_12);
	P(WORLD_13);
	P(WORLD_14);
	P(WORLD_15);
	P(WORLD_16);
	P(WORLD_17);
	P(WORLD_18);
	P(WORLD_19);
	P(WORLD_20);
	P(WORLD_21);
	P(WORLD_22);
	P(WORLD_23);
	P(WORLD_24);
	P(WORLD_25);
	P(WORLD_26);
	P(WORLD_27);
	P(WORLD_28);
	P(WORLD_29);
	P(WORLD_30);
	P(WORLD_31);
	P(WORLD_32);
	P(WORLD_33);
	P(WORLD_34);
	P(WORLD_35);
	P(WORLD_36);
	P(WORLD_37);
	P(WORLD_38);
	P(WORLD_39);
	P(WORLD_40);
	P(WORLD_41);
	P(WORLD_42);
	P(WORLD_43);
	P(WORLD_44);
	P(WORLD_45);
	P(WORLD_46);
	P(WORLD_47);
	P(WORLD_48);
	P(WORLD_49);
	P(WORLD_50);
	P(WORLD_51);
	P(WORLD_52);
	P(WORLD_53);
	P(WORLD_54);
	P(WORLD_55);
	P(WORLD_56);
	P(WORLD_57);
	P(WORLD_58);
	P(WORLD_59);
	P(WORLD_60);
	P(WORLD_61);
	P(WORLD_62);
	P(WORLD_63);
	P(WORLD_64);
	P(WORLD_65);
	P(WORLD_66);
	P(WORLD_67);
	P(WORLD_68);
	P(WORLD_69);
	P(WORLD_70);
	P(WORLD_71);
	P(WORLD_72);
	P(WORLD_73);
	P(WORLD_74);
	P(WORLD_75);
	P(WORLD_76);
	P(WORLD_77);
	P(WORLD_78);
	P(WORLD_79);
	P(WORLD_80);
	P(WORLD_81);
	P(WORLD_82);
	P(WORLD_83);
	P(WORLD_84);
	P(WORLD_85);
	P(WORLD_86);
	P(WORLD_87);
	P(WORLD_88);
	P(WORLD_89);
	P(WORLD_90);
	P(WORLD_91);
	P(WORLD_92);
	P(WORLD_93);
	P(WORLD_94);
	P(WORLD_95);
#endif
	P(KP0);
	P(KP1);
	P(KP2);
	P(KP3);
	P(KP4);
	P(KP5);
	P(KP6);
	P(KP7);
	P(KP8);
	P(KP9);
	P2(KP_PERIOD,KPDOT);
	P2(KP_DIVIDE,KPSLASH);
	P2(KP_MULTIPLY,KPASTERISK);
	P2(KP_MINUS,KPMINUS);
	P2(KP_PLUS,KPPLUS);
	P2(KP_ENTER,KPENTER);
	P2(KP_EQUALS,KPEQUAL);
	P(UP);
	P(DOWN);
	P(RIGHT);
	P(LEFT);
	P(INSERT);
	P(HOME);
	P(END);
	P(PAGEUP);
	P(PAGEDOWN);
	P(F1);
	P(F2);
	P(F3);
	P(F4);
	P(F5);
	P(F6);
	P(F7);
	P(F8);
	P(F9);
	P(F10);
	P(F11);
	P(F12);
	P(F13);
	P(F14);
	P(F15);
	P(NUMLOCK);
	P(CAPSLOCK);
	P2(SCROLLOCK,SCROLLLOCK);
	P2(RSHIFT,RIGHTSHIFT);
	P2(LSHIFT,LEFTSHIFT);
	P2(RCTRL,RIGHTCTRL);
	P2(LCTRL,LEFTCTRL);
	P2(RALT,RIGHTALT);
	P2(LALT,LEFTALT);
	P2(RMETA,RIGHTMETA);
	P2(LMETA,LEFTMETA);
#if 0
	P(LSUPER);
	P(RSUPER);
#endif
	P(MODE);
	P(COMPOSE);
	P(HELP);
	P(PRINT);
	P2(SYSREQ,SYSRQ);
	P(BREAK);
	P(MENU);
	P(POWER);
	P(EURO);
	P(UNDO);
	default:
		eDebug("[eSDLInputDevice] unhandled SDL keycode: %d", key);
		return KEY_RESERVED;
	}

	#undef P2
	#undef P
}

/*
 * eSDLInputDriver
 */

eSDLInputDriver *eSDLInputDriver::instance;

eSDLInputDriver::eSDLInputDriver() : eRCDriver(eRCInput::getInstance())
{
	ASSERT(instance == 0);
	instance = this;
}

eSDLInputDriver::~eSDLInputDriver()
{
	instance = 0;
}

void eSDLInputDriver::keyPressed(const SDL_KeyboardEvent *key)
{
	eDebug("[eSDLInputDevice] km=%d enabled=%d locked=%d",
		input->getKeyboardMode(), enabled, input->islocked());

	if (!enabled || input->islocked())
		return;

	std::list<eRCDevice*>::iterator i(listeners.begin());
	while (i != listeners.end()) {
		(*i)->handleCode((long)key);
		++i;
	}
}

class eRCSDLInit
{
private:
	eSDLInputDriver driver;
	eSDLInputDevice device;

public:
	eRCSDLInit(): driver(), device(&driver)
	{
	}
};

eAutoInitP0<eRCSDLInit> init_rcSDL(eAutoInitNumbers::rc+1, "SDL RC Driver");
