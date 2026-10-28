# e2egl: GLES OSD backend

`gEGLDC` is a `gMainDC` implementation that renders the enigma2 OSD with
OpenGL ES 2.0 or 3.0 through EGL instead of drawing into the framebuffer with
the CPU. It consumes the normal `gRC` opcode stream, so skins, widgets and
Python code keep working unchanged. If the backend cannot initialise, enigma2
falls back to `gFBDC`.

Main files:

| Area | Files |
| --- | --- |
| Device context | `lib/gdi/egl/gegldc.cpp`, `lib/gdi/egl/gegldc.h` |
| Startup | `lib/gdi/egl/egl_init.cpp`, `lib/gdi/egl/egl_config.*` |
| Runtime GLES version | `lib/gdi/egl/gles_version.*` |
| Textures, offscreen pixmaps | `lib/gdi/egl/gtexture_manager.*` |
| Shaders | `lib/gdi/egl/shader/gshader.*`, `gadvanced_shader.*`, `gtexture_shader.*`, `gtext_shader.*` |
| Glyph atlas | `lib/gdi/gfont_atlas.*` |
| Native windows | `lib/gdi/egl/inative_window_provider.h`, `lib/gdi/egl/platform/*` |
| DreamNextGen output | `lib/gdi/egl/platform/amlogic/amlogic_fb_output.*` |
| Opcodes, render thread | `lib/gdi/grc.*` |
| Backend interface | `lib/gdi/gmaindc.*` |

## Build

The backend is enabled with `--with-egl`. In OE the recipe passes it when the
machine has `e2egl` in `MACHINE_FEATURES` and then also depends on
`virtual/egl` and `virtual/libgles2` (`enigma2.bb`).

`configure.ac` looks up `egl` and `glesv2` via pkg-config (falling back to
`-lEGL`/`-lGLESv2`) and selects the native window integration from
`$BOXTYPE`. After the machine consolidation `BOXTYPE` is the platform name for
consolidated machines (`dms922x`, `dm7252s`, `dm7435`, `vu7376`, `vu7376duo`,
`ocmv200`, `abmv200`, `ed72604`, ...); single boxes still use the box name.

| configure list | Define / conditional | Provider | `BOXTYPE` values |
| --- | --- | --- | --- |
| `DREAMNEXTGEN` | `DREAMNEXTGEN` | `amlogic` + `AmlogicFramebufferOutput` | `dms922x` |
| `is_vuplus_egl_box` | `HAVE_VUPLUS_EGL` (needs `nxpl`) | `vuplus` | `vu7376duo vu7376 vuuno4k vuuno4kse vuzero4k` |
| `is_vuplus_mips_egl_box` | `HAVE_VUPLUS_MIPSEL_EGL` (needs `libvupl`) | `vuplus_mips` | `vuduo2 vusolo2 vusolose` |
| `is_nxpl_egl_box` | `HAVE_NXPL_EGL` (needs `nxpl`) | `nxpl` | `et10000 et1x000 triplex hd2400 8100s gb7252 gb72604 dags72604 hd51 vs1500 h7 h17 sf4008 vuduo4klite`, plus `MACHINEBUILD=formuler1` |
| `is_v3dplatform_egl_box` | `HAVE_V3DPLATFORM_EGL` (needs `v3dplatform`) | `v3dplatform` | `ed72604 xc7346` |
| `is_dreambcm_egl_box` | `HAVE_DREAMBCM_EGL`, adds `-DBROADCOM_PLATFORM` | `dreambcm` | `dm520 dm525 dm7435 dm7252s` |
| `is_hisilicon_egl_box` | `HAVE_HISILICON_EGL` | `hisilicon` | the HiSilicon list in `configure.ac` (`u5 ... u57`, `ocmv200`, `abmv200`, `gbmv200`, `sfx6008`, `h9`, `hd60`, ...) |

With `--with-egl`, configure fails if EGL/GLESv2 or the platform library
required for the box (`nxpl`, `libvupl`, `v3dplatform`) is missing. `gb7252`
and `vuduo4klite` additionally define `E2EGL_NXPL_SYNC_FB_DST` (see "OSD
position").

`HAVE_GLES3` is defined only if `GLES3/gl3.h` exists **and** a test program
calling `glGenVertexArrays`/`glBindVertexArray` links, because some SDKs ship
the header with a GLES2-only library. The DreamNextGen output needs GLES3
(`glBlitFramebuffer`) and fails to compile without it.

`lib/gdi/Makefile.inc` builds `lib/gdi/egl/*` and the shaders under
`HAVE_EGL`, plus exactly the provider sources of the active conditional. The
`sdl` and `wayland` providers in `lib/gdi/egl/platform/` are not part of the
build.

## Startup

`gEGLDCAutoInit` (`lib/gdi/egl/egl_init.cpp`) runs at
`eAutoInitNumbers::graphic - 2`, before `gFBDC` (`graphic - 1`). It returns
without creating a DC if no provider define is set or a `gMainDC` already
exists. If `gEGLDC::initEGL()` fails, the DC is dropped and `gFBDC` takes over.

The `gEGLDC` constructor:

1. Opens its own `fbClass` on all platforms except Vu+ ARM and reads the
   current mode. HiSilicon instead takes the `<resolution>` of the configured
   skin from `/etc/enigma2/settings` (falling back to `MetrixHD`, then
   `skin_default`, then 1280x720).
2. Accepts only 720x576, 1280x720, 1920x1080 and 2560x1440 as logical size,
   otherwise 1280x720, and always sets the framebuffer to 32 bpp (EGL configs
   are RGBA8888; a 16 bpp mode left by the boot loader makes
   `eglCreateWindowSurface` fail with `EGL_BAD_MATCH`).
3. Creates the platform provider and calls `init(surfaceWidth, surfaceHeight)`.

`initEGL()` tries a GLES3 context first, then GLES2, and publishes the result
in `gles::version`. All shaders and the atlas choose their ES3 or ES2 code
path from `gles::isGLES3()`; without `HAVE_GLES3` only the ES2 sources are
compiled. The EGL config is RGBA8888 without depth/stencil. Outside
DreamNextGen a config with `EGL_SWAP_BEHAVIOR_PRESERVED_BIT` is preferred,
except on V3D, NXPL, Vu+ ARM and Vu+ MIPS, where destroyed swap is forced.
On Vu+ ARM a rejected video mode sized surface is retried at 1280x720.
Afterwards the shaders and the glyph atlas are created, `eglSwapInterval(1)`
is set, all pages/buffers are cleared ("primed") and the OSD capture socket is
started.

`getGraphicsInfo()` (`lib/python/enigma_python.i`) exposes the state to
Python: `backend` (`"e2egl"`), `window_provider`, `accelerator`, `buffering`,
`buffer_pages`, logical and surface size, EGL and GLES version,
`preserved_swap`, `suspended`, `hardware_accelerated`,
`animations_supported`. `lib/python/Components/SystemInfo.py` sets the mutable
`BoxInfo` item `e2egl` from `backend`.

## Threading

The EGL context is made current once on the `gRC` render thread (the thread
that runs `gEGLDC::exec()`, recorded on the first call) and is never released
there. The only exception is unbinding right before a window surface is
destroyed, because EGL keeps a current surface alive.

Public entry points that can be called from other threads hand their work to
the render thread with the `gOpcode::invoke` opcode and wait for it:
`setResolution()`, `refresh()`, `setOSDPosition()`, `suspendGraphics()`,
`resumeGraphics()`, `readOSDToBGRA()` (OSD capture) and `cleanupEGL()`
(`gEGLDC::runOnRenderThread()`). The invoke payload is a
`std::function<void()>*`; `exec()` makes the context current if needed and
runs it. Until the render thread has executed its first opcode (or when there
is no `gRC`), these calls run directly on the calling thread while holding
`m_egl_mutex`, which `exec()` also takes.

GL objects owned by `gPixmap` surfaces may die on any thread. Their texture and
framebuffer names are queued in `gTextureManager` under a mutex
(`egl_queue_texture_deletion()`, `egl_queue_framebuffer_deletion()`) and
deleted by `processDeletions()` at the start of every `exec()`. The pointer to
the active manager is guarded by its own mutex.

## Render path

### Scene framebuffer

Drawing opcodes normally go into an offscreen scene FBO (RGBA texture) that
keeps its content between frames. Only the regions a widget invalidates are
redrawn into it, so a partial update costs only the redrawn area plus one
copy of the scene at present time. Whether the scene FBO is used
(`sceneFramebufferWanted()`):

- DreamNextGen: always.
- V3D, NXPL, Vu+ ARM, Vu+ MIPS: always (destroyed swap is forced).
- HiSilicon, Dreambox BCM: only if the window surface does not report
  `EGL_BUFFER_PRESERVED`. With preserved swap, drawing goes straight to the
  window surface.

The scene has the logical size. If that exceeds `GL_MAX_TEXTURE_SIZE` while
the surface size fits, the scene is created at surface size and all rects are
scaled. Without a scene FBO and without preserved swap, the presented frame is
captured into a texture before each flip and restored before the next draw.

### Present via window surface

On all platforms except DreamNextGen, `flip()` clears the default framebuffer,
draws the scene texture with the texture shader into the OSD destination
viewport and calls `eglSwapBuffers()`. Dreambox BCM adds a `glFinish()`
because its driver can otherwise expose an unfinished render-to-texture frame.

If the native window or the window surface cannot be recreated during
`setResolution()` or `refresh()`, the surface is marked lost and `exec()`
retries `refresh()` every 500 ms.

### Present on DreamNextGen (dreamone/dreamtwo)

There is no EGL window surface. The context is bound to a 1x1 pbuffer
placeholder and `AmlogicFramebufferOutput` renders into fb0 directly:

1. `FBIOGET_OSD_DMABUF` (`0x46fc`) exports the fb0 memory as one dma-buf.
   Each page is imported with `eglCreateImageKHR(EGL_LINUX_DMA_BUF_EXT,
   DRM_FORMAT_ARGB8888, offset = page * line_length * yres)`, bound to a
   texture with `glEGLImageTargetTexture2DOES` and attached to its own FBO.
2. Exactly three pages are required (`yres_virtual / yres` and `smem_len` must
   allow them); otherwise `create()` fails. The first back page is the one
   after the page currently shown (`yoffset`).
3. `presentSceneFramebuffer()` blits the scene into the back page with
   `glBlitFramebuffer`, Y-flipped (the scene is stored bottom-up, the page is
   scanned out top-down), with `GL_LINEAR` only if the OSD destination is
   scaled. The page is cleared first unless the destination is full screen.
4. `present()` calls `glFinish()`, pans to the page with `FBIOPAN_DISPLAY`
   (`fbClass::setOffset()`) and advances to the next page.

A pan takes effect at the next vsync, so the page just hidden may still be
scanned out. Instead of waiting after each pan, the time a page was hidden is
stored. Before a page is drawn into again (`waitBackPage()`), the code waits
with `FBIO_WAITFORVSYNC_64` (`_IOW('F', 0x21, ...)`, returns the
`CLOCK_MONOTONIC` vsync time) only if the page was hidden less than one vsync
period ago, and keeps waiting until a vsync stamped after the pan arrives. The
period is measured from consecutive waits (43 ms is assumed until then). With
three pages the page drawn next has usually been off screen long enough.

On a mode change the page objects are rebuilt for the new size; the context
and the placeholder surface stay. `getGraphicsAccelerator()` reports
`GLES/EGL, e2ge / Dream GE2D` (plus `active`), and the constructor sets
`DREAM_GE2D_SURFACE_ACCEL`, `DREAM_GE2D_ACCEL_FILL` and
`DREAM_GE2D_ACCEL_BLIT` to `1` unless already set.

## Drawing

### Shaders

| Shader | Use |
| --- | --- |
| `gShader` (basic) | solid quads, solid rect batches, per-vertex coloured batches, lines |
| `gAdvancedShader` | rounded rectangles (per-corner edge mask), gradients with up to 16 stops, orientation and alpha blend |
| `gTextureShader` | pixmaps and frame copies; global alpha, rounded clip mask, alpha test (`alpha < 0.5` is discarded), luminance textures |
| `gTextShader` | batched glyph quads sampling the 8-bit atlas |

Each shader has GLSL ES 3.00 and 1.00 sources; the ES2 variants replace the
integer edge mask by four per-corner floats. Projection matrices map logical
coordinates; `setFramebufferResolution()` installs a top-down projection for
drawing straight into a DreamNextGen page.

Colours: enigma2 stores `gRGB::a` as transparency (0 = opaque); GL alpha is
`1 - a/255`. Blending uses
`glBlendFuncSeparate(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA, GL_ONE, GL_ONE_MINUS_SRC_ALPHA)`.
A `clear` with a fully transparent background becomes `glClear` (full frame
or scissored per clip rect).

### Fills and rectangles

`fill`, `fillRegion` and opaque `clear` append coloured quads to a fill batch
that is drawn in one call; it is flushed when blending changes or another
operation overlaps its bounds. Plain rectangles are drawn as one basic shader
batch per clip region.

Rounded rectangles and their borders with a solid colour
(`drawRoundedSolidRect()`) run the advanced shader only over the up to four
corner squares (scissored), the remaining three bands are flat quads drawn
with the basic shader. Gradient rectangles still run the advanced shader over
the whole area, once per clip rect.

### Pixmaps and textures

`blit` uploads the pixmap through `gTextureManager::getTexture()` and draws it
per clip rect with the texture shader, honouring alignment, scaling, keep
aspect ratio, alpha test/blend and the corner radius. Alpha textures use
`GL_NEAREST`, others `GL_LINEAR`.

Upload paths (`gTextureManager::createTextureFromSurface()`):

- 32 bpp with a physical address: dma-buf import if
  `EGL_EXT_image_dma_buf_import` and `GL_OES_EGL_image` are available (on
  DreamNextGen via `dreamGE2DGetDmabuf()`, with `CONFIG_ION` via the accel
  memory fd).
- 32 bpp otherwise: per-pixel BGRA to RGBA conversion. Direct BGRA upload is
  only used on builds without a box provider and only with
  `GL_EXT_texture_format_BGRA8888`.
- 8 bpp with CLUT: expanded to RGBA.
- 8 bpp without CLUT: `GL_LUMINANCE` (ES2) or `GL_R8` (ES3).

Small CPU pixmaps are additionally deduplicated by content: 8 bpp surfaces
with CPU data, no physical address and at most 262144 pixels are hashed
(size, bpp, CLUT, transparency, pixels) and their texture is shared. The cache
is trimmed least recently used first to `E2EGL_TEXTURE_CACHE_ENTRIES` entries
and `E2EGL_TEXTURE_CACHE_MB`. If a 32 bpp upload fails with
`GL_OUT_OF_MEMORY`, the least recently used entries for the size of that
upload are released and the upload is retried; only if that fails as well is
the whole cache cleared and the upload tried once more.

`gPixmap` drawing into 32 bpp offscreen pixmaps (fill, rectangle, axis-aligned
lines, blit) can be done on the GPU through FBOs attached to the pixmap
texture (`egl_gpixmap_*()` in `gtexture_manager.cpp`, called from
`lib/gdi/gpixmap.cpp`). This needs a current context, so it only takes effect
on the render thread; elsewhere, or for unsupported cases, the CPU path is
used. Content is synced back to CPU memory on demand
(`egl_sync_surface_to_cpu()`).

### Text

`renderGlyph()` keys each glyph by a 64-bit FNV-1a hash of its 8-bit mask
(size, pitch, pixels) and packs it into a 2048x2048 8-bit atlas
(`gFontAtlas`, `stb_rect_pack`). Quads are clipped per clip rect and collected
in a text batch of up to 4096 quads that is drawn with one call. The batch is
flushed when a fill, rectangle, line, blit or clear overlaps it, on state
opcodes that cannot keep pending text, at present time, when it is full, or
before the atlas is reset. A full atlas is reset completely. Dirty atlas rects
are uploaded with `glTexSubImage2D` before drawing: GLES3 uploads only the
dirty rect (`GL_UNPACK_ROW_LENGTH`), GLES2 the full rows.

### Spinner

Both skin spinner pixmaps and the native spinner of `gSpinner` are drawn over
a saved copy of the background. While a video mode changes, `eAVControl`
suspends the spinner and resumes it after a 1000 ms hold
(`lib/driver/avcontrol.cpp`).

## Animations

### Opcodes

- `eWindow::show()`/`hide()` send `sendShow`/`sendHide` with the window
  geometry if the window's animation mode has the show (`0x01`) or hide
  (`0x10`) bit set; the default is `0x11` when the desktop's DC supports
  animations (`lib/gui/ewindow.cpp`).
- `eListbox` sends `sendListboxAnimation` from its paint when the selection
  moves within a stable viewport and old and new row are fully visible
  (`lib/gui/elistbox.cpp`). It carries both rects, the selection colour,
  gradient, corner radius and selection pixmap.

On `sendShow`/`sendHide` the backend keeps the current frame as the old frame:
with a scene FBO by copying it into a spare FBO and swapping the two, without
one by capturing the frame into a texture. At the next `flush`/`flip` the new
frame is complete and the animation runs instead of the plain present.

### Pacing

Animations run synchronously on the render thread. Progress is taken from the
elapsed time (`animationProgress()`), not from a frame count, and the loop
ends once progress reaches 1, so the duration does not depend on the output
rate. Frames are at least 16 ms apart (`waitForNextAnimationFrame()`), which
matters where presenting does not wait for the display.

- Windows: duration `speed * 6` ms (`* 12` on DreamNextGen), clamped to
  80-420 ms; toast-like windows use the toast speed, clamped to 60-240 ms.
  Ease-out.
- Listbox: duration `speed * 7` ms, clamped to 90-210 ms. Ease-in-out.

With a scene FBO each animation frame is composed from the old and new scene
textures. On DreamNextGen this is drawn straight into the back fb0 page with
a top-down viewport and projection and shown with a pan; elsewhere it goes to
the window surface. Without a scene FBO but with preserved swap, only the
damaged area is redrawn per frame (`E2EGL_ANIMATION_DAMAGE`).

### Window animation types

| Value | Type | Value | Type |
| --- | --- | --- | --- |
| 0 | off | 12 | zoom from left |
| 1 | simple fade | 13 | zoom from right |
| 2 | simple zoom | 14 | stripes (8 strips) |
| 3 | grow drop | 15 | basis (default) |
| 4 | grow from left | 16 | modern adaptive |
| 5 | extrude from left | 17 | fade in / fade out |
| 6 | popup | 18 | dialog pop |
| 7 | slide drop | 19 | toast slide |
| 8 | slide from left | 20 | side sheet |
| 9 | slide left to right | 21 | zoom and fade |
| 10 | slide right to left | | |
| 11 | slide top to bottom | | |

15 and 16 adapt to the window geometry (bottom/top panel, left/right panel,
small dialog, large window). With profiles enabled and a base animation of 15
or 16, the type is chosen per window: toast-like windows (8-94 % of the
screen width, under 28 % of its height, near the top or bottom) use the toast
profile, small dialogs (under 68 % in both directions) the dialog profile,
side panels and popup panels the popup profile.

### Listbox selection

The listbox animation draws the new frame, restores the target row from the
old frame and moves the selection bar (selection pixmap or advanced shader
rect) with 0.82 alpha. Inside the old and the new row the bar is taken from
the frame that shows that row selected, so the row text stays above it.
Because the listbox repaints both rows before it sends the opcode, the
presented frame is captured at every flip while listbox animations are on and
used as the old frame.

### Settings

`lib/python/Screens/AnimationSetup.py` and the `AnimationSetup` section of
`data/setup.xml` ("OSD Animation Settings", menu entry `requires="e2egl"`):

| Config | Default | Native setter |
| --- | --- | --- |
| `config.misc.animation.default` | 15 on e2egl, else 0; 100 = classic group | `setAnimation_current()` |
| `config.misc.animation.classic` | 1 (types 1-14) | |
| `config.misc.animation.speed` | 15, range 15-30 (5-30 on dreamone/dreamtwo) | `setAnimation_speed()` |
| `config.misc.animation.toast_speed` | 10, range 5-30 | `setAnimation_toast_speed()` |
| `config.misc.animation.listbox` | off | `setAnimation_current_listbox()` |
| `config.misc.animation.profiles` | on | `setAnimation_profiles()` |
| `config.misc.animation.dialog` / `popup` / `toast` | 18 / 16 / 17 | `setAnimation_profiles()` |

The setters (`main/enigma.cpp`) only forward to `gEGLDCSet*()` if the main DC
is `e2egl` with animations. Changes apply immediately; the blue key previews
the selected type. Screens with the skin attribute `animationPaused` disable
window animations while they are open. With e2egl, `Screens/Toast.py` skips
its own alpha fade.

## External GLES clients and teletext

`suspendGraphics()` frees the OSD for another GLES/framebuffer client:
pending batches are flushed, the texture cache, scene FBOs, frame textures and
the atlas are released, the window surface is destroyed and the CPU backing
pixmap is shrunk to 1x1. Queued opcodes are then discarded without drawing
(`gDC::discardOpcode()`) so their references are still released.
Platform specifics:

- Dreambox BCM: shaders, context and display are destroyed as well and
  `eglTerminate()`/`eglReleaseThread()` are called, because the driver holds
  an inter-process lock while a display/context exists. The texture manager
  starts a new context generation so stale GL names on surfaces are ignored.
  `resumeGraphics()` recreates everything via `initEGL()`.
- Vu+ ARM and NXPL: the native window is destroyed as well, because the
  compositor would keep showing the last buffer.
- DreamNextGen: the fb0 page imports are released.

`resumeGraphics()` (other platforms) restores the backing pixmap and the atlas
and calls `refresh()`; it fails if no surface could be created.

`eTuxtxtApp::startUi()` (`lib/components/tuxtxtapp.cpp`) and
`FlashManager.lockGraphics()` lock `fbClass` if an instance exists and call
`suspendGraphics()` only otherwise. While `fbClass` is locked, `gEGLDC::islocked()`
reports it and `gPainter` stops submitting. After teletext on Vu+ ARM the last
teletext page is pushed with `FBIO_BLIT`.

## Video mode, resolution and OSD position

`setResolution()` (skin resolution) and `refresh()` (video mode change)
release the scene FBO, frame textures and content texture cache before the
surface is reallocated, so old and new buffers are not held at the same time.
The surface size follows the platform:

- DreamNextGen, HiSilicon, Dreambox BCM: the framebuffer mode is set
  (`fbClass::SetMode`, 32 bpp) and its result used as surface size.
- Vu+ ARM: surface size from `/proc/stb/video/videomode`, capped to
  1920x1080; the logical size can be larger.
- NXPL on `hd2400`, `mutant2400`, `quadbox2400`, `triplex`, `et10000`,
  `formuler1`, `formuler1tc`, `f1` (by `machinebuild` or
  `/proc/stb/info/boxtype`): surface and framebuffer follow the video mode.
- V3D recreates its native window on refresh; Vu+ MIPS keeps an existing
  surface.

Dreambox BCM and DreamNextGen keep the scene content across `refresh()` and
present it again.

The OSD position is applied by the backend itself: `eAVControl::setOSDPosition()`
first calls `gMainDC::setOSDPosition()` and only falls back to
`/proc/stb/fb/dst_*` or the Amlogic `window_axis` (written as inclusive end
coordinates) if the DC does not handle it. `gEGLDC` stores the rect in logical
coordinates, presents the scene into that destination viewport (scaled) and
reports `getOSDAxis()` as `0 0 <logical width> <logical height>`. With
`E2EGL_NXPL_SYNC_FB_DST` (gb7252, vuduo4klite) the rect is also written to
`/proc/stb/fb/dst_*`, scaled to the 720x576 space the driver expects, and
applied.

## OSD capture

`initEGL()` starts a thread serving the Unix socket `/tmp/e2egl-osd.socket`.
Each connection receives one frame: a header (`char magic[8] = "E2EGL01"`,
`uint32_t width, height, stride, format`, format 1 = BGRA) followed by
straight (non-premultiplied) BGRA pixels, at logical size when a scene FBO
is active and at surface size otherwise. The read runs on the
render thread.

## Environment variables

All variables are read once at first use.

| Variable | Default | Effect |
| --- | --- | --- |
| `E2EGL_ANIMATION_DAMAGE` | on | Unset, empty or anything but `0`: window animations without a scene FBO but with preserved swap redraw only the damaged area per frame. `0` redraws the full frame. |
| `E2EGL_DREAMBCM_WINDOW` | unset | Dreambox BCM: unset, empty, `0`, `none` or `null` passes a null native window to `eglCreateWindowSurface` (driver default window); any other value passes an `fbdev_window` with the surface size. |
| `E2EGL_GPIXMAP_GLES` | on | A value starting with `0`, `n`, `N`, `f` or `F` disables the GPU path for `gPixmap` offscreen drawing. |
| `E2EGL_NXPL_RELEASE_NXPL` | off | NXPL: non-empty and not starting with `0` destroys the native window, unregisters the display and leaves the platform at shutdown; otherwise teardown is skipped. |
| `E2EGL_NXPL_UNINIT_NEXUS` | off | NXPL: with `E2EGL_NXPL_RELEASE_NXPL` on and a join via `NxClient_Join`, also calls `NxClient_Uninit` at shutdown; otherwise the client stays joined. |
| `E2EGL_TEXTURE_CACHE_ENTRIES` | 256 | Maximum entries of the content texture cache, clamped to 32-1024. |
| `E2EGL_TEXTURE_CACHE_MB` | 48 | Maximum size of the content texture cache in MiB, clamped to 4-256. |
| `E2EGL_TRACE_GL` | off | Non-empty and not `0`: one `[e2egl:frame]` line per presented frame (timings, op counts, uploads, cache hits/misses) plus `[e2egl:animation]`/`[e2egl:listbox]` start and end lines. |
| `E2EGL_TRACE_GL_LIMIT` | 240 | Number of frames logged by `E2EGL_TRACE_GL`, `0` = unlimited. The frame index restarts on `refresh()`. |
| `E2EGL_TRACE_GL_SLOW_US` | 0 | Log only frames taking at least this many microseconds, `0` = all. |
| `E2EGL_TRACE_GPIXMAP` | off | Logs `gPixmap` operations as `[e2egl:gPixmap]` and a per-operation summary at exit. Values starting with `0`, `n`, `f` or `o` (any case) leave it off, so use e.g. `1`. |
| `E2EGL_TRACE_GPIXMAP_LIMIT` | 256 | Number of logged `gPixmap` operations, `0` = unlimited. |
| `E2EGL_TRACE_OPS` | off | Non-empty and not `0`: one `[e2egl:op]` line per fill, rectangle, clear and blit. |
| `E2EGL_VUPLUS_RELEASE_NXPL` | off | Vu+ ARM: like `E2EGL_NXPL_RELEASE_NXPL`. |
| `E2EGL_VUPLUS_UNINIT_NEXUS` | off | Vu+ ARM: with `E2EGL_VUPLUS_RELEASE_NXPL` on, also calls `NxClient_Uninit` at shutdown. |

## Known limitations

- Animations block the render thread for their duration; no other opcode is
  executed meanwhile.
- Every present copies the whole scene; there is no damage-limited swap.
- DreamNextGen needs GLES3 and three fb0 pages; otherwise EGL init fails and
  `gFBDC` is used, or after a mode change the output is retried every 500 ms.
- 32 bpp CPU pixmaps on the supported boxes are converted per pixel on upload;
  only 8 bpp pixmaps are content cached.
- A full glyph atlas is reset completely, so all glyphs are uploaded again.
- GPU drawing into offscreen `gPixmap`s only happens on the render thread.
- The `sdl` and `wayland` window providers are not built.
