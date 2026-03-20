#pragma once
#include <lib/gdi/inative_window_provider.h>
#include <wayland-client.h>
#include <wayland-egl.h>

class WaylandWindowProvider : public INativeWindowProvider
{
private:
    struct wl_display *m_display;
    struct wl_registry *m_registry;
    struct wl_compositor *m_compositor;
    struct wl_surface *m_surface;
    struct wl_egl_window *m_egl_window;

    int m_width;
    int m_height;

    // Statische Callbacks für die Wayland-Registry
    static void registryHandleGlobal(void *data, struct wl_registry *registry, uint32_t name, const char *interface, uint32_t version);
    static void registryHandleGlobalRemove(void *data, struct wl_registry *registry, uint32_t name);

public:
    WaylandWindowProvider();
    virtual ~WaylandWindowProvider();

    bool init(int width, int height) override;
    EGLNativeDisplayType getNativeDisplay() override;
    EGLNativeWindowType getNativeWindow() override;
    void cleanup() override;
};

#endif
