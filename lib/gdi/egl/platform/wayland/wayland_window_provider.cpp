#include <lib/base/eerror.h>
#include <lib/gdi/egl/platform/wayland/wayland_window_provider.h>

WaylandWindowProvider::WaylandWindowProvider() : m_display(nullptr), m_registry(nullptr), m_compositor(nullptr), m_surface(nullptr), m_egl_window(nullptr), m_width(0), m_height(0) {}

WaylandWindowProvider::~WaylandWindowProvider() {
	cleanup();
}

// Wayland Listener Callbacks
void WaylandWindowProvider::registryHandleGlobal(void* data, struct wl_registry* registry, uint32_t name, const char* interface, uint32_t version) {
	WaylandWindowProvider* provider = static_cast<WaylandWindowProvider*>(data);
	if (strcmp(interface, "wl_compositor") == 0) {
		provider->m_compositor = static_cast<struct wl_compositor*>(wl_registry_bind(registry, name, &wl_compositor_interface, 1));
	}
}

void WaylandWindowProvider::registryHandleGlobalRemove(void* data, struct wl_registry* registry, uint32_t name) {
	// Für dieses simple Beispiel ignorieren wir das Entfernen von Globals
}

bool WaylandWindowProvider::init(int width, int height) {
	m_width = width;
	m_height = height;

	m_display = wl_display_connect(nullptr);
	if (!m_display) {
		eDebug("[WaylandWindowProvider] Fehler: Kann nicht zum Wayland-Display verbinden.");
		return false;
	}

	m_registry = wl_display_get_registry(m_display);
	static const struct wl_registry_listener registry_listener = {registryHandleGlobal, registryHandleGlobalRemove};
	wl_registry_add_listener(m_registry, &registry_listener, this);

	wl_display_roundtrip(m_display);

	if (!m_compositor) {
		eDebug("[WaylandWindowProvider] Fehler: wl_compositor nicht gefunden.");
		return false;
	}

	m_surface = wl_compositor_create_surface(m_compositor);
	if (!m_surface) {
		eDebug("[WaylandWindowProvider] Fehler: Kann Wayland Surface nicht erstellen.");
		return false;
	}

	m_egl_window = wl_egl_window_create(m_surface, m_width, m_height);
	if (!m_egl_window) {
		eDebug("[WaylandWindowProvider] Fehler: wl_egl_window_create fehlgeschlagen.");
		return false;
	}

	return true;
}

EGLNativeDisplayType WaylandWindowProvider::getNativeDisplay() {
	return reinterpret_cast<EGLNativeDisplayType>(m_display);
}

EGLNativeWindowType WaylandWindowProvider::getNativeWindow() {
	return reinterpret_cast<EGLNativeWindowType>(m_egl_window);
}

void WaylandWindowProvider::cleanup() {
	if (m_egl_window) {
		wl_egl_window_destroy(m_egl_window);
		m_egl_window = nullptr;
	}
	if (m_surface) {
		wl_surface_destroy(m_surface);
		m_surface = nullptr;
	}
	if (m_compositor) {
		wl_compositor_destroy(m_compositor);
		m_compositor = nullptr;
	}
	if (m_registry) {
		wl_registry_destroy(m_registry);
		m_registry = nullptr;
	}
	if (m_display) {
		wl_display_disconnect(m_display);
		m_display = nullptr;
	}
}