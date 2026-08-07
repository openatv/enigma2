# e2egl / GLES OSD backend

Diese Datei beschreibt den technischen Stand des neuen EGL/GLES-Backends fuer
Enigma2. Der Name im Code und in den Build-Features ist `e2egl`. Das ist nicht
der alte VU/libvugles2-Pfad und hat nichts mit CU-GLES zu tun.

Ziel ist ein OpenATV-Master, der auf normalen Boxen weiter den bisherigen
Framebuffer-DC benutzt und auf DreamNextGen sowie testweise Vu+ optional einen
EGL/GLES-OSD-Pfad aktivieren kann. Ohne aktiviertes `e2egl`-Feature darf sich
am klassischen gFBC/gFBDC-Verhalten nichts aendern.

## Zielbild

Der langfristige Zielzustand ist:

- Enigma2 benutzt die bestehende `gPainter`/`gDC` API weiter.
- Die konkrete Ausgabe geht je nach Build/Box ueber den klassischen gFBDC oder
  ueber `gEGLDC`.
- Rechtecke, Linien, Text, Pixmaps, Alpha, Scaling, runde Ecken, Gradienten,
  Animationen und spaeter weitere OSD-Effekte laufen auf dem GLES-Pfad ueber
  GPU/Shader statt ueber CPU-gerechnete `gPixmap`-Zwischenbilder.
- DreamNextGen nutzt EGL/fbdev/Mali fuer die finale OSD-Ausgabe und GE2D fuer
  die Faelle, in denen Enigma2 weiterhin softwareseitige Surfaces braucht.
- Andere Boxen bleiben ungestoert. Vu+ nutzt keinen alten `libvugles2`-Pfad,
  sondern einen eigenen `e2egl`-Native-Window-Provider direkt ueber
  Broadcom `NxClient`/`NXPL`.

## Build-Gating

Der neue Pfad muss hart build- und feature-gesteuert bleiben.

Wichtige Schalter:

- `MACHINE_FEATURES += "e2egl"` aktiviert den EGL/GLES-Backend-Build.
- `HAVE_EGL` wird daraus in der Enigma2-Konfiguration abgeleitet.
- `HAVE_GLES3` aktiviert GLES3-Shader, sonst wird GLES2 verwendet.
- `DREAMNEXTGEN` ist die Plattform-Klammer fuer Dream One/Two spezifische
  Amlogic/fbdev/GE2D Teile.
- `HAVE_VUPLUS_EGL` aktiviert den Vu+ Broadcom/NXPL Native-Window-Provider.
- Auf Vu+ muss `virtual/egl virtual/libgles2` ein `nxpl.pc` in den Sysroot
  installieren. Das aktuelle Vu+-`libgles`-Recipe liefert dort
  `-lnxpl -ldvb_client -ldvb_base`.

Wichtige Build-Dateien:

- `configure.ac`
- `lib/gdi/Makefile.inc`
- `lib/python/Plugins/SystemPlugins/Makefile.am`
- Image/Recipe-/bbappend-Seite im jeweiligen OpenEmbedded-Layer

Wichtig: `DREAMNEXTGEN` allein bedeutet nicht automatisch, dass der EGL-Pfad
benutzt werden muss. Die Box soll ohne `e2egl` weiterhin auf dem heutigen
Framebuffer-Pfad laufen koennen.

## Initialisierung

Die Initialisierung liegt in:

- `lib/gdi/egl/egl_init.cpp`
- `lib/gdi/egl/gegldc.cpp`
- `lib/gdi/egl/gegldc.h`
- `lib/gdi/egl/platform/amlogic/amlogic_window_provider.cpp`
- `lib/gdi/egl/platform/vuplus/vuplus_window_provider.cpp`

Der Ablauf:

1. `gEGLDCAutoInit` wird frueh vor dem klassischen `gFBDC` initialisiert.
2. Wenn bereits ein `gMainDC` existiert, wird `gEGLDC` uebersprungen.
3. Auf DreamNextGen wird ein `AmlogicWindowProvider` verwendet.
   Auf Vu+ wird bei `HAVE_VUPLUS_EGL` ein `VuplusWindowProvider` verwendet.
4. `gEGLDC::initEGL()` versucht zuerst GLES3, dann GLES2.
5. Der erkannte GLES-Level wird in `gles::version` abgelegt, damit Shader zur
   Laufzeit zwischen GLES2/GLES3 unterscheiden koennen.
6. Wenn EGL/GLES nicht initialisiert werden kann, soll der klassische FBDC-Pfad
   als Fallback erhalten bleiben.

DreamNextGen benutzt hier einen Mali-fbdev/EGL-Pfad. Es gibt kein X11,
Wayland oder GBM-Fenster. `AmlogicWindowProvider` liefert im Kern nur die
fbdev-Window-Groesse und `EGL_DEFAULT_DISPLAY`.

Vu+ benutzt fuer den Broadcom-Port dieselbe Abstraktion, aber direkt ueber den
Nexus-Multi-Process-Pfad:

- `NxClient_Join(NULL)`
- `NXPL_RegisterNexusDisplayPlatform(&handle, NULL)`
- `NXPL_GetDefaultNativeWindowInfoEXT(&window_info)`
- `NXPL_CreateNativeWindowEXT(&window_info)`
- `eglGetDisplay(EGL_DEFAULT_DISPLAY)`
- `eglCreateWindowSurface(..., window, NULL)`

Das entspricht dem direkten V3D/NXPL-Weg aus den Broadcom-Nexus-Beispielen.
`KodiGLESPL`, `xbmc.helper`, der alte `libvugles2`-Pfad und Python-basierte
VU-Animationen werden fuer e2egl nicht verwendet.

## Haupt-Renderpfad

Enigma2 erzeugt weiterhin `gOpcode`-Kommandos ueber `gPainter`. Der aktive DC
entscheidet, wie diese Kommandos gerendert werden.

Klassischer Pfad:

- `gFBDC` rendert in ein `gPixmap`, das direkt den Framebuffer bzw. Backbuffer
  repraesentiert.
- `flip/flush` pannt oder kopiert Pages.
- Viele Operationen laufen CPU/GE2D-seitig.

EGL-Pfad:

- `gEGLDC` ist ein `gMainDC`.
- `gEGLDC::exec()` verarbeitet `gOpcode` direkt in der EGLSurface.
- `fill`, `clear`, `line`, `rectangle`, `blit`, `renderText`, Spinner und
  Animationen haben eigene GLES-Implementierungen.
- `flip()` ruft `eglSwapBuffers()`.
- Der Backbuffer muss erhalten bleiben, weil Enigma2 im Immediate-Mode oft nur
  Dirty-Regions neu malt.

Wichtige Datei:

- `lib/gdi/egl/gegldc.cpp`

## Externe GLES-Anwendungen und Speichersuspend

Chromium2 sperrt den klassischen Painter bereits ueber `fbClass::lock()`.
Das verhindert neue OSD-Draws, gab bislang aber weder die EGL-Window-Surface
noch deren Swap-Puffer frei. Fuer speicherarme 4K-Receiver stellt `gMainDC`
darum folgende plattformneutrale API bereit:

- `suspendGraphics()`
- `resumeGraphics()`
- `isGraphicsSuspended()`

`gEGLDC::suspendGraphics()` behaelt EGLDisplay und EGLContext, gibt aber die
Window-Surface, interne Framebuffer-/Frame-Texturen, den Glyph-Atlas und
transiente Textur-Caches frei. Auf NXPL wird zusaetzlich das native OSD-Window
entfernt, damit dessen letzter Buffer nicht durch transparente Videoflaechen
einer externen Anwendung sichtbar bleibt. Das kleine 1x1-CPU-Pixmap dient nur noch dazu,
bereits vor dem Lock eingereihte OpCodes korrekt zu entsorgen. Der EGLContext
bleibt absichtlich bestehen: So werden Textur-IDs noch lebender Skin-Pixmaps
nicht ungueltig.

Beim Beenden der externen Anwendung setzt das Plugin zuerst die urspruengliche
logische Aufloesung und OSD-Position. `resumeGraphics()` baut danach
CPU-Pixmap, Glyph-Atlas und EGL-Window-Surface neu auf; der folgende
Desktop-Resize erzwingt den kompletten OSD-Neuaufbau.

Die Reihenfolge fuer normale Portal-Anwendungen ist:

1. DVB-Service stoppen.
2. `fbClass.lock()` und RCU fuer Enigma2 sperren.
3. `gMainDC.suspendGraphics()`.
4. Chromium starten.
5. Chromium stoppen und Aufloesung/OSD-Ziel wiederherstellen.
6. Framebuffer entsperren, `gMainDC.resumeGraphics()` und Desktop neu zeichnen.

HbbTV verwendet diesen Vollsuspend nicht, weil Live-TV und transparente
Broadcast-Overlays aktiv bleiben muessen. Beim Entsperren verwendet das
HbbTV-Plugin deshalb `fbClass.unlock(False)`: Painter und Spinner werden wieder
freigegeben, ohne unter der noch lebenden EGL-Window-Surface erneut
`FBIOPUT_VSCREENINFO` auszufuehren. Der normale parameterlose `unlock()`-Aufruf
behaelt fuer alle bestehenden Nutzer den bisherigen Mode- und Palette-Restore.
Das ist insbesondere auf Dream BCM wichtig, weil ein Mode-Reset dort das
native ARGB-Layout aendern und anschliessend OSD-Farben vertauschen kann.

## Swap-Verhalten und Dirty-Regions

Ein wichtiger Unterschied zum klassischen Framebuffer ist, dass EGL nach
`eglSwapBuffers()` den Backbuffer nicht automatisch erhalten muss. Enigma2
erwartet aber im Immediate-Mode ein persistentes Ziel, weil viele Repaints nur
Dirty-Regions neu zeichnen.

Darum setzt `gEGLDC`:

- Config-Wunsch: `EGL_SWAP_BEHAVIOR_PRESERVED_BIT`
- Surface-Attribut: `EGL_SWAP_BEHAVIOR = EGL_BUFFER_PRESERVED`

Wenn der Treiber das nicht kann, gibt es einen Fallback:

- Vor dem Flip wird der aktuelle Frame in eine GL-Texture kopiert.
- Vor dem naechsten echten Draw wird dieser Frame zurueckgezeichnet.

Wichtige Logzeilen:

```text
[gEGLDC] EGL swap behavior: preserved
[gEGLDC] EGL preserved swap unavailable...
[gEGLDC] restoring previous frame after non-preserved swap
```

DreamNextGen/Mali kann aktuell `preserved`; dadurch bleibt das OSD stabil.

## Texturen und PNGs

Texturen werden in `gTextureManager` verwaltet:

- `lib/gdi/egl/gtexture_manager.cpp`
- `lib/gdi/egl/gtexture_manager.h`

Moegliche Upload-Pfade:

1. dma-buf Import ueber `EGL_EXT_image_dma_buf_import`
2. direkter CPU-Upload in eine GLES-Texture

Auf DreamNextGen wird fuer 32-bit Pixmaps aktuell der sichere RGBA-Upload
verwendet. Das Rendering bleibt trotzdem GPU/GLES; nur das einmalige
Textur-Staging beim Upload konvertiert BGRA/ARGB-Layout in ein Format, das
der Mali-Treiber korrekt sampelt.

Das ist wichtig fuer kleine Skin-PNGs und Spinner:

- `alphatest="on"` muss wie der Softwarepfad einen Alpha-Threshold benutzen.
- Der GLES-Texture-Shader verwirft bei Alpha-Test Pixel mit `alpha < 0.5`.
- Ohne diesen Threshold werden halbtransparente Randpixel als schwarze Bloecke
  sichtbar.
- Kleine CPU-seitige 8-bit Pixmaps werden content-basiert gecacht. Das hilft
  bei Skins, die gleiche CLUT/PNG-Icons wiederholt neu erzeugen. Im Frame-Log
  zeigt `tex_cache=hits/misses`, ob dieser Cache greift.

Der GLES-Content-Cache ist fuer Picons groesser als der reine Dateicache-Pfad
und kann zur Diagnose angepasst werden:

```sh
export E2EGL_TEXTURE_CACHE_MB=48
export E2EGL_TEXTURE_CACHE_ENTRIES=256
```

Bei 256x256-CLUT-Picons entspricht 48 MiB grob 192 RGBA-Texturen. Wenn beim
Scrollen weiterhin viele `tex_cache=0/1`-Misses auftauchen, kann dieser Wert
testweise erhoeht werden. Das ist nur der GLES-Content-Cache; der klassische
FBDC-Pfad nutzt ihn nicht.

Wichtige Datei:

- `lib/gdi/egl/shader/gtexture_shader.cpp`

## SVG

SVG wird aktuell weiterhin ueber NanoSVG geladen:

- `lib/gdi/epng.cpp` / `loadSVG()`
- `lib/gdi/picload.cpp` / `svg_load()`

GLES kann SVG nicht direkt rendern. OpenGL ES rendert Texturen und Dreiecke;
SVG ist dagegen XML mit Pfaden, Strokes, Fills, Gradienten, Transforms und
Clipping. Ein Parser und ein Umsetzungs-Schritt bleiben also immer noetig.

Der aktuelle stabile Pfad ist:

1. SVG mit NanoSVG parsen.
2. In ein 32-bit `gPixmap` rasterisieren.
3. Das Pixmap als GLES-Textur hochladen und cachen.

Das ist fuer Skin-Icons und selten geladene Bilder akzeptabel, weil der teure
Teil nicht pro Frame passieren sollte. Ein spaeterer GPU-Pfad waere moeglich,
aber nicht automatisch durch GLES vorhanden:

- NanoSVG oder ein anderer Parser liefert Pfade.
- Ein Tessellator erzeugt Dreiecke fuer Fills/Strokes, oder einfache Icons
  werden als SDF/MSDF-Texturen gecacht.
- Gradienten, Alpha und Transforms werden per Shader umgesetzt.
- Nicht unterstuetzte SVG-Features fallen auf den heutigen Rasterizer zurueck.

Darum NanoSVG im ersten DreamNextGen-`e2egl`-Schritt nicht entfernen. Erst wenn
Tracing zeigt, dass SVG-Laden wirklich ein relevanter Block ist, lohnt ein
gezielter SVG-GPU-Cache oder Vector-Renderer.

## Text-Rendering

Text wird nicht als komplette CPU-Pixmap fuer jeden Label-Fall gerendert,
sondern ueber Glyph-Masken und einen Atlas:

- `lib/gdi/gfont_atlas.*`
- `lib/gdi/egl/shader/gtext_shader.*`
- `gEGLDC::renderGlyph()`
- `gEGLDC::flushTextBatch()`

Der Ablauf:

1. Font-Code liefert 8-bit Glyph-Masken.
2. `gEGLDC::renderGlyph()` legt Glyphen in den Atlas.
3. Glyph-Quads werden gesammelt.
4. `flushTextBatch()` rendert viele Glyphen mit einem Shader-Batch.

Damit ist normaler UI-Text auf dem GLES-Pfad.

Der EGL-Pfad sammelt Text ueber mehrere `renderText`/`renderPara`-OpCodes,
solange kein echter Draw oder Clip-relevanter State-Wechsel dazwischenkommt.
Dadurch sollen Listboxen und Menues weniger kleine Text-Drawcalls erzeugen.
Im Frame-Log ist das an kleineren `text_batches=*/...`-Werten und weniger
`text_us` bei aehnlicher `glyph=`-Zahl zu erkennen.

Der Textshader nutzt einen dynamisch wachsenden VBO. `gEGLDC` darf dadurch
groessere Textmengen, z. B. ChannelSelection mit EPG-Text, in einem Batch
sammeln, ohne bei 1024 Glyphen kuenstlich zu splitten. Die aktuelle
Batch-Obergrenze im DC liegt bei 4096 Glyphen.

Draw-Operationen wie Fill, Rectangle, Clear, Blit, Line und
Text-Hintergruende leeren einen pending Textbatch nur noch, wenn ihre
tatsaechlich geclippte Zielregion den pending Textbereich schneidet. Das ist
fuer Listboxen wichtig: ein Hintergrund der naechsten Zeile muss den Text der
vorherigen Zeile nicht flushen, solange sich die Bereiche nicht ueberlappen.
Die Overlap-Pruefung benutzt nicht nur die grosse Union-Box des Textbatches,
sondern die tatsaechlich geclippten Glyph-Rechtecke. Dadurch loesen Fills
zwischen Zeilen keinen falschen Textflush mehr aus.
Damit diese Pruefung bei langen EPG-Zeilen nicht selbst teuer wird, werden
benachbarte Glyph-Rechtecke innerhalb eines Textlaufs zu groesseren Run-
Rechtecken zusammengefasst. Das bleibt konservativ fuer die Zeichenreihenfolge,
reduziert aber die Anzahl der Rechtecktests deutlich.

Glyphen werden beim Aufbau des Textbatches direkt gegen die aktuell gueltige
Clip-Region geschnitten. Dadurch ist `flushTextBatch()` nicht mehr vom
aktuellen `m_current_clip` abhaengig und `setClip`/`addClip`/`popClip` koennen
pending Text stehen lassen. Im Frame-Log bedeutet `text_batches=a/b` nun:
`a` echte GLES-Textdraws, `b` geclippte Glyph-Quads im Batch.

Einfache Fill- und Textbackground-Flaechen werden ebenfalls gesammelt. Der
DC legt Solid-Fill-Rechtecke mit Vertex-Farben in einen Batch und flushed ihn
erst vor Text, ueberlappenden Blits/Rectangles/Lines/Clears, Frame-Copies oder
Flip. Farbwechsel trennen den Batch dadurch nicht mehr; nur Blend-State und
echte Ueberlappungs-/Frame-Grenzen bleiben Barrieren. `fill=` zaehlt weiterhin
die Skin-/Opcode-Fills, waehrend `solid=` zeigt, wie viele echte GLES-Solid-
Draws daraus geworden sind.

Der Atlas laedt nach der ersten Textur-Anlage nicht mehr zwingend eine grosse
Bounding-Box hoch, sondern mehrere zusammengefuehrte Dirty-Rechtecke. Dadurch
soll `font_up=*/...px` im Frame-Log weniger Pixel enthalten, auch wenn die Zahl
der Sub-Uploads in manchen Frames hoeher sein kann.

Cached Scrolling-Text in `eLabel` und `eListboxPythonStringContent` wird bei
aktivem Hardware-DC nicht mehr zuerst in eine CPU-`gPixmap` gerendert. Der
e2egl-Pfad rendert den scrollenden Text direkt ueber `gPainter::renderText`;
der alte Pixmap-Cache bleibt fuer Software-DC/gFBC erhalten.
Im Glyph-Blit werden fuer Hardware-DC ausserdem keine Software-Farblookup-
Tabellen mehr aufgebaut; der Pfad geht direkt in den Glyph-Atlas und
Textbatch.
Einfache scrollende Texte ohne Border/Underline/Marked-Text koennen den
fertigen `eTextPara` wiederverwenden. Dadurch muss bei jedem Scrolltick nicht
mehr der komplette Text neu geformt und ausgerichtet werden; nur der
Glyph-/Batch-Ausgabepfad laeuft pro Frame weiter.

Noch nicht vollstaendig geloest sind andere Sonderfaelle, die Text oder
Text-nahe Inhalte zuerst in eine separate `gPixmap` rendern und diese dann
wieder blitten. Diese Pfade sollten spaeter auf FBO/Texture-Render-Targets
oder direkte GLES-Kommandos umgestellt werden.

## Rechtecke, Gradienten und runde Ecken

Der EGL-Pfad hat Shader fuer einfache und komplexere Rechtecke:

- `lib/gdi/egl/shader/gshader.*`
- `lib/gdi/egl/shader/gadvanced_shader.*`
- `gEGLDC::executeRectangle()`

`gAdvancedShader` kann bereits:

- runde Ecken
- einzelne Corner-Masks
- Gradienten
- Alpha-Blending

Das gilt fuer direkte `gPainter::drawRectangle()`-Kommandos auf dem aktiven
`gEGLDC`.

Wichtig: Nicht alle runden Ecken im heutigen Enigma2 laufen direkt ueber diesen
Pfad. Es gibt weiterhin Code, der zuerst in ein CPU-`gPixmap` rendert:

- `gPixmap::drawRectangle()`
- Skin-/Listbox-/Selection-Hintergruende
- gecachte Text-/Scroll-Pixmaps
- einige `ePixmap`/Canvas-Sonderfaelle

Diese CPU-Pfade sind der naechste grosse Optimierungsblock. Ziel ist nicht, sie
dauerhaft in CPU zu lassen, sondern sie schrittweise auf GPU-Render-Targets
oder direkte GLES-Kommandos zu bringen.

## GE2D im aktuellen Stand

DreamNextGen nutzt GE2D weiter fuer klassische Surface-Faelle:

- `lib/gdi/dreamge2d.cpp`
- `lib/gdi/dreamge2d.h`
- `lib/gdi/accel.cpp`

GE2D ist aktuell nuetzlich fuer:

- beschleunigte Fills/Blits auf softwareseitigen `gPixmap`-Surfaces
- dma-buf Surface-Allokation
- Page-/OSD-Kopien im klassischen FBDC-Pfad

Im EGL-Zielbild ist GE2D nicht der finale Compositor fuer das OSD, sondern ein
Hilfsbeschleuniger fuer kompatible Altpfade. Neue visuelle Features sollten
moeglichst direkt als GLES-Shader oder FBO-Pass implementiert werden.

## gPixmap-Altpfad-Tracing

Damit die naechsten Optimierungen nicht geraten werden muessen, gibt es eine
abschaltbare Laufzeit-Instrumentierung fuer klassische `gPixmap`-Operationen.
Sie ist per Default aus und aendert ohne Env-Flag kein Verhalten.

Aktivieren auf der Box:

```sh
export E2EGL_TRACE_GPIXMAP=1
export E2EGL_TRACE_GPIXMAP_LIMIT=512
enigma2
```

Die Logzeilen beginnen mit:

```text
[e2egl:gPixmap]
```

Erfasst werden aktuell:

- `fill-*-cpu` und `fill-*-ge2d`
- `fill-*-gles` fuer 32-bit Pixmap-Fills, die direkt in eine GLES/FBO-Texture
  geschrieben wurden
- `drawRectangle-solid-gles` fuer einfache solide 32-bit Offscreen-Rechtecke
- `drawRectangle-gradient-gles`, `drawRectangle-rounded-gles` und
  `drawRectangle-new-gles` fuer komplexere 32-bit Offscreen-Rechtecke, die
  ueber den Advanced-Shader in eine FBO-Texture geschrieben wurden
- `blit-rounded-gles` und `blit-rounded-scale-gles` fuer 32-bit nach 32-bit
  Offscreen-Blits mit Radius, die ueber den Texture-Shader in eine FBO-Texture
  geschrieben wurden
- `drawRectangle-*-cpu`
- `blit-cpu`, `blit-scale-cpu`, `blit-rounded-cpu`
- `blit-ge2d`, `blit-scale-ge2d`
- `mergePalette-cpu`
- `line-gles` fuer horizontale/vertikale 32-bit Offscreen-Linien
- `line-cpu`

Wenn `E2EGL_TRACE_GPIXMAP_LIMIT` erreicht wird, und noch einmal beim sauberen
Beenden von Enigma2, wird eine Summary mit Zaehlern, Pixel-Byte-Summe und
Laufzeit pro Operation ausgegeben:

```text
[e2egl:gPixmap] summary op=drawRectangle-gradient-cpu count=42 bytes=6720000 time_us=58000 avg_us=1380 max_us=6100 kib_s=113
[e2egl:gPixmap] summary op=blit-rounded-cpu count=18 bytes=921600 time_us=19000 avg_us=1055 max_us=2400 kib_s=47
```

Beispiel:

```text
[e2egl:gPixmap] drawRectangle-gradient-cpu path=cpu dst=1920x1080x32 ... area=0,0 500x80 bytes=160000 rects=1 flags=0x0 radius=12 edges=0xf
```

Wichtige Felder:

- `path=cpu`: Dieser Pfad rendert in CPU-Speicher und ist ein Kandidat fuer
  GLES/FBO-Umbau.
- `path=ge2d`: Dieser Pfad nutzt die bestehende GE2D-Beschleunigung fuer ein
  klassisches Pixmap. Das ist besser als reine CPU, aber noch kein GLES-Shader.
- `path=gles`: Dieser Pfad hat ein klassisches `gPixmap` ueber eine
  GLES-Texture/FBO bearbeitet.
- `gltex`: Wenn hier vor der Operation eine Texture-ID stand, wurde ein bereits
  hochgeladenes Pixmap durch CPU/GE2D-Schreibzugriff wieder ungueltig.
- `fbo`, `glvalid`, `cpuvalid`: zeigen, ob ein Pixmap aktuell eine
  Offscreen-FBO-Texture besitzt und ob der gueltige Inhalt auf GPU, CPU oder
  beiden Seiten liegt.
- `flags`, `radius`, `edges`: Helfen zu erkennen, ob Alpha, Scaling oder
  gerundete Ecken den langsamen Pfad ausloesen.
- `time_us`: Gesamtzeit dieses Operationstyps seit Trace-Start.
- `avg_us`: Durchschnitt pro Operation.
- `max_us`: langsamster Einzelaufruf.
- `kib_s`: grober Pixeldurchsatz. Dieser Wert ist nur ein Vergleichswert fuer
  denselben Box-Test, kein absoluter Benchmark.

Typische Testreihen:

- StartWizard oeffnen und die ersten sichtbaren Logs sichern.
- Hauptmenue/Listbox schnell hoch/runter scrollen.
- Skin mit vielen runden Ecken/Gradienten testen.
- OSD Animation Settings mit Fade/Slide testen und auf `blit-scale-cpu` achten.

Diese Daten bestimmen die Reihenfolge des naechsten Umbaus. Wenn z. B.
`drawRectangle-gradient-cpu` dominiert, muss zuerst `gPixmap::drawRectangle()`
einen GLES/FBO-Pfad bekommen. Wenn `blit-rounded-cpu` dominiert, ist rounded
texture compositing der naechste Hebel. Wenn fast nur `blit-ge2d` auftaucht,
ist der Altpfad zwar noch nicht ideal, aber nicht der schlimmste CPU-Block.

Der erste Offscreen-Schritt ist vorhanden: 32-bit `gPixmap::fill()` kann bei
aktivem EGL-Kontext direkt in eine GLES-Texture mit FBO schreiben. Wenn danach
ein alter CPU/GE2D-Pfad die Pixel lesen oder veraendern muss, wird der
GPU-Inhalt vor dem CPU-Zugriff zurueckgelesen. Zum Gegencheck kann der Pfad
deaktiviert werden:

```sh
export E2EGL_GPIXMAP_GLES=0
```

`E2EGL_TRACE_GL=1` schreibt ausserdem `draw_us` in die Frame-Zeile. Im
Gegensatz zu `frame_us` misst dieser Wert nur die Zeit, in der der EGL-Pfad
mit aktivem Kontext Renderarbeit erledigt. EGL-Context-Bind/Release wird
separat als `ctx_make_us` und `ctx_release_us` geloggt.

`other_us` ist der Rest von `draw_us`, der nicht bereits durch die
Render-Teilzaehler unten erklaert wird. Wenn `other_us` gross ist, steckt die
Zeit also nicht in den bekannten GLES-Fill/Text/Blit/Rectangle-Timern, sondern
in noch nicht einzeln instrumentiertem Render-State, Sync-Kosten innerhalb des
Draw-Aufrufs oder sonstiger Arbeit in `gEGLDC::exec()`. Swap steht separat in
`swap_us`; Frame-Texture-Copies und Animation-Captures werden separat in
`copy_us`/`cap_us` gezeigt und nicht mehr als `other_us` gewertet.

`ctx_make_us` und `ctx_release_us` zeigen die EGL-Kontextkosten. `ctx=a/b`
zaehlt Make-/Release-Vorgaenge. Der Kontext wird nach den Opcodes wieder
freigegeben, weil Enigma2 auch Spinner- und Nebenpfade aus anderen Threads
treffen kann. Ein Test mit gehaltenem Kontext blockierte auf DreamNextGen die
OSD-Ausgabe und bleibt deshalb aus dem stabilen Pfad entfernt.

Reine State-Opcodes wie Font/Farbe/Clip/Offset/Gradient/Radius/Border laufen
ohne EGL-Context-Bind durch `gDC::exec()`, solange sie pending Text sicher
stehen lassen koennen. Damit sollten `ctx=*/...` und `ctx_release_us` in
Listbox-/Menue-Frames deutlich sinken, ohne den Spinnerpfad zu blockieren.

Zusaetzlich gibt es eine grobe Zeitaufteilung pro Frame:

- `fill_us`: Flush-Zeit fuer gesammelte Solid-Fills und Text-Hintergruende
- `rect_us`: Rectangle-Kommandos inklusive Gradienten und runden Ecken
- `clear_us`: Clear-Kommandos
- `line_us`: Linien-Kommandos
- `blit_us`: Pixmap-Blits inklusive Texturzugriff/Erst-Upload
- `text_build_us`: CPU-Zeit fuer `renderText`/`renderPara`, also Layout,
  Glyph-Aufbau und Atlas-Lookups vor dem eigentlichen Batch-Flush
- `text_us`: Glyph-Batch-Rendering inklusive Font-Atlas-Subuploads
- `state_us`: klassische `gDC::exec()`-Zeit fuer State-OpCodes wie Clip,
  Font, Farben, Radius, Border und aehnliche Nicht-Draw-Kommandos
- `overlap_us`: Zeit fuer die praezise Pending-Text-Overlap-Pruefung gegen
  geclippte Glyph-Rechtecke
- `tex_gc_us`: Zeit fuer verzoegerte GLES-Texture-Loeschungen im TextureManager
- `copy_us`: Frame-Texture-Copies fuer Animation/Restore-Compositing
- `ctx_make_us`/`ctx_release_us`: EGL-Context-Bind/Release ausserhalb der
  eigentlichen GLES-Draw-Timer

Bei ChannelSelection/EPG-Scrolltests ist wichtig, `draw_us`, `text_build_us`,
`text_us`, `glyph=`, `text_ops=` und `text_batches=*/...` zusammen zu lesen.
Wenn `text_build_us` dominiert, steckt der Blocker im CPU-Textaufbau/Layout.
Wenn `text_us` dominiert, liegt er im Font-Atlas-Upload oder in zu vielen
Glyph-Batch-Draws. Wenn `fill=` hoch bleibt, `solid=` aber niedrig ist, greift
das Fill-Batching. Bleiben `solid=` und `fill_us` hoch, werden die Fills noch
zu oft durch ueberlappende Draws, Blendwechsel oder Frame-Grenzen getrennt.

`text_flush=a/b/c/d/e/f/g/h` erklaert, warum pending Text innerhalb eines
Frames vorzeitig gezeichnet werden musste:

- `a`: ueberlappender Fill oder Text-Hintergrund
- `b`: ueberlappendes Rectangle, inklusive Gradient/runder Ecke
- `c`: ueberlappende Linie
- `d`: ueberlappender Pixmap-Blit, z. B. Picon oder Icon
- `e`: ueberlappender Clear
- `f`: sonstiger State-/Opcode-Wechsel, der pending Text nicht halten darf
- `g`: Font-Atlas musste erweitert werden
- `h`: Textbatch-Limit wurde erreicht

Wenn `text_batches=` hoch ist, aber `text_flush=` fast nur Nullen zeigt, kommt
die Trennung hauptsaechlich von normalen Frame-/Flip-Grenzen. Wenn dagegen
z. B. `text_flush=0/6/0/0/0/0/0/0` steht, trennen Rectangles/Gradienten den
Textbatch und der naechste Umbau muss dort ansetzen.

`text_overlap=a/b` zeigt, wie oft die praezise Pending-Text-Overlap-Pruefung
nach der schnellen Bounds-Pruefung aktiv wurde und wie viele zusammengefasste
Text-Run-Rechtecke dabei getestet wurden. Wenn `text_flush` sinkt,
`text_overlap` aber nur klein steigt, war die genauere Pruefung ein guter
Tausch.

Die Channellist-Picons sind im Frame-Log meist als 8-bit PNG/CLUT-Texturen zu
erkennen, z. B. `tex_up=1 clut8=1 tex_px=65536` fuer ein 256x256-Picon. Wenn
dabei `tex_cache=0/1` steht, wurde das Picon in diesem Frame erstmals als
GLES-Textur angelegt. Wiederholte Picons sollten spaeter als Cache-Hit
auftauchen. Die kleinen `240x80x16` gPixmap-Zeilen gehoeren zum
LCD/Summary-Pfad; sie koennen Picon/Summary-Inhalte enthalten, sind aber nicht
allein der Hauptindikator fuer das Channellist-Scrollen auf dem TV-OSD.

## Animationen

Animationen sind im EGL-Pfad wieder aktiv:

- `gEGLDC::supportsShowHideAnimations()`
- `gEGLDC::executeWindowAnimationOpcode()`
- `gEGLDC::runPendingWindowAnimation()`
- `lib/python/Screens/AnimationSetup.py`
- `data/setup.xml` mit dem Setup-Key `AnimationSetup`

e2egl-Systeme routen `setAnimation_current()` direkt auf
`gEGLDCSetAnimationCurrent()`. Profilwerte fuer Dialoge, Popup-/Panel-Fenster
und Toast-artige Hinweise laufen ueber `setAnimation_profiles()` nach
`gEGLDCSetAnimationProfiles()`. Auf nicht-e2egl Boxen bleiben die Python-Aufrufe
gueltig, der native Teil macht dort aber nichts. Der alte native
Framebuffer-Animationspfad wurde entfernt, damit es keine zwei
Animation-Backends gleichzeitig gibt. Die Konfiguration ist als Core-Screen
unter OSD eingebunden, wird aus `setup.xml` erzeugt und nur angezeigt, wenn
`BoxInfo["e2egl"]` aktiv ist.

Default ist sicher:

- `config.misc.animation.default = 15` auf e2egl-Systemen
- `config.misc.animation.default = 0` auf nicht-e2egl-Systemen
- Animationen laufen nur, wenn AnimationSetup einen Wert > 0 setzt.
- Im OSD-Animation-Menue kann der Nutzer jederzeit auf `Disable Animations`
  zurueckschalten.
- Die klassischen Modi `1` bis `14` stehen nicht mehr einzeln in der
  Hauptauswahl. Sie sind unter `Classic animation` zusammengefasst und werden
  ueber `Classic animation style` gewaehlt.
- Adaptive Profile koennen Dialoge/MessageBoxen, Popup-/Panel-Fenster und
  Toast-artige Hinweise getrennt animieren. Sie greifen nur bei den modernen
  Basis-Modi (`15`/`16`), damit klassische Effekte wie Slide, Zoom oder Stripes
  exakt unveraendert bleiben.
- Toast-Profile nutzen auf e2egl per Default `17` fuer Fade in / fade out.
  `Toast.py` laesst den alten Alpha-Timer nur auf nicht-e2egl-Systemen laufen;
  auf e2egl wird der Toast direkt sichtbar gesetzt und Show/Hide wird ueber
  den GLES-Animationspfad animiert. Damit gibt es keinen doppelten Fade.
- `config.misc.animation.toast_speed = 10` steuert nur die Toast-Fade-Dauer.
  Der Ablauf ist: kurzer Fade-in, Toast-Timeout als lesbare Standzeit, kurzer
  Fade-out. Die normale Fenster-Animationsgeschwindigkeit bleibt davon
  getrennt.

Die AnimationSetup-IDs sind einheitlich fuer alle Boxen:

- `0`: Disable Animations
- `1`: Simple fade
- `2`: Simple zoom
- `3`: Grow drop
- `4`: Grow from left
- `5`: Extrude from left
- `6`: Popup
- `7`: Slide drop
- `8`: Slide from left
- `9`: Slide left to right
- `10`: Slide right to left
- `11`: Slide top to bottom
- `12`: Zoom from left
- `13`: Zoom from right
- `14`: Stripes
- `15`: Basis animation, ein GLES-Modus mit positionsabhaengiger Bewegung:
  kleine Dialoge nutzen Fade/Popup, untere Panels gleiten leicht von unten,
  seitliche Panels gleiten leicht seitlich, grosse Screens bleiben ruhig und
  blenden nur dezent.
- `16`: Modern adaptive
- `17`: Fade in / fade out
- `18`: Dialog pop
- `19`: Toast slide
- `20`: Side sheet
- `21`: Zoom and fade

Der Animationspfad kopiert alten und neuen Frame in Texturen und rendert daraus
die Fade/Zoom/Slide/Stripe-Effekte im GLES-Pfad.

DreamOS hat zusaetzlich Widget-Crossfades fuer Text/Bilder. openATV/e2egl
aktiviert derzeit nur Fenster- und Profilanimationen; ein echter Widget-
Crossfade waere ein spaeterer separater Renderer-Umbau.

Auf Treibern mit `EGL_BUFFER_PRESERVED` nutzt der Animationspfad Dirty-Areas:
pro Animationsframe wird nur der betroffene Fensterbereich aus der alten bzw.
neuen Frame-Textur wiederhergestellt. Dadurch sollte `copies=*/...px` deutlich
kleiner werden als ein Fullscreen-Copy. Zum Gegencheck kann der alte
Fullscreen-Animationspfad erzwungen werden:

```sh
export E2EGL_ANIMATION_DAMAGE=0
```

## Video-Mode und Surface-Refresh

Wenn AVSwitch den Videomode setzt, muss die EGLSurface neu aufgebaut werden:

- `lib/python/Components/AVSwitch.py`
- `gMainDC::refresh()`
- `gEGLDC::refresh()`

Nach `refresh()` wird der Desktop einmal komplett neu gemalt, damit Dirty-State
und neue EGLSurface wieder synchron sind. Ohne diesen Repaint werden manche
Texte oder Widgets erst sichtbar, wenn eine spaetere Eingabe eine Dirty-Region
ausloest.

## Was aktuell funktioniert

Aktueller DreamNextGen-Teststand:

- EGL/GLES init auf Dream Two
- GLES3-Kontext
- Preserved swap
- OSD sichtbar
- PNGs sichtbar
- Spinner sichtbar
- Font/Glyph-Rendering sichtbar
- AnimationSetup funktioniert
- Videomode-Refresh funktioniert
- Alpha-Test fuer kleine PNGs
- mehrere framebuffer pages wieder moeglich, kein Single-Buffer-Diagnosemodus
- erstes GLES-Offscreen-FBO fuer 32-bit `gPixmap::fill()`
- einfache solide 32-bit `gPixmap::drawRectangle()`-Faelle ohne Radius,
  Gradient, Border und Alpha-Blend laufen ueber denselben GLES/FBO-Pfad
- komplexere 32-bit `gPixmap::drawRectangle()`-Faelle mit Gradient, Radius,
  Border oder New/Alpha-Blend koennen ueber den GLES/FBO-Advanced-Shader laufen
- 32-bit `gPixmap::blit()`-Faelle mit Radius, inklusive skalierter Radius-
  Blits, koennen ueber den GLES/FBO-Texture-Shader laufen
- horizontale/vertikale 32-bit `gPixmap::line()`-Faelle laufen ueber den
  GLES/FBO-Fill-Pfad; diagonale Linien bleiben Fallback
- Frame-Log zeigt neben `frame_us` auch `draw_us` und `*_us` pro Teilpfad
- Frame-Log trennt EGL-Context-Kosten in `ctx_make_us`/`ctx_release_us`
- reine State-Opcodes laufen ohne EGL-Context-Bind, damit Listbox-/Menue-
  Frames weniger `eglMakeCurrent`/`eglMakeCurrent(...NO_CONTEXT)` Paare haben
- Frame-Log trennt CPU-Textaufbau (`text_build_us`) und GLES-Textflush
  (`text_us`)
- Frame-Log zeigt `tex_cache=hits/misses`
- GLES-Content-Cache fuer kleine 8-bit/CLUT-Pixmaps ist per Env tunebar
- Font-Atlas nutzt Dirty-Rect-Uploads
- Text-OpCodes werden ueber sichere State-Grenzen hinweg gebatcht
- Textshader-VBO waechst dynamisch fuer grosse EPG-/Listbox-Batches
- Nicht ueberlappende Fill/Blit/Rect/Line/Textbackground-Draws duerfen pending
  Text stehen lassen, um Listbox-Text besser zu sammeln
- Glyph-Quads werden beim Batch-Aufbau geclippt, damit Clip-State-Wechsel den
  Textbatch nicht mehr zwangsweise leeren
- Fill-/Textbackground-Rechtecke werden mit Vertex-Farben als Solid-Batch
  gesammelt; `solid=` zeigt die echten GLES-Draws dafuer
- Animationen reduzieren bei preserved swap die Copy-Flaeche

## Bekannte Grenzen

Folgende Punkte sind noch nicht final:

- Nicht alle OSD-Operationen sind GPU-native; einige erzeugen weiterhin
  CPU-`gPixmap`-Zwischenbilder.
- `gPixmap::drawRectangle()` hat einen ersten GLES/FBO-Pfad fuer runde Ecken,
  Gradienten, Border und Alpha-Blend. Der alte CPU-Pfad bleibt Fallback, wenn
  kein aktiver EGL-Kontext/FBO vorhanden ist oder ein Sonderfall nicht sicher
  ueber den Shader abbildbar ist.
- Runde 32-bit Offscreen-Blits haben einen ersten GLES/FBO-Pfad. 8-bit
  Quellen, Self-Blits und andere Sonderfaelle bleiben bewusst auf dem alten
  Fallback.
- Cached scrolling text in `eLabel`/`eListbox` benutzt teils separate Pixmaps.
- dma-buf Import fuer kleine/CPU-geladene PNGs ist noch nicht als Standardpfad
  freigegeben; sicherer RGBA-Upload ist stabiler.
- Texture-Cache-Invalidation muss bei allen CPU/GE2D-mutierten Surfaces sauber
  bleiben.
- Animationen brauchen mehr Box-Tests mit verschiedenen Skins und
  Aufloesungen.
- Der Vu+ Broadcom/NXPL-Pfad ist neu und braucht Box-Tests mit `vuduo4kse`:
  `NxClient_Join`, `NXPL_RegisterNexusDisplayPlatform`, NativeWindow-Groesse,
  EGL-Init, Swap-Verhalten, OSD-Painting und Cleanup beim Beenden muessen im
  Log geprueft werden.

## Roadmap zu mehr GLES und weniger CPU

### 1. GPU-Render-Targets fuer Offscreen-Pixmaps

Viele CPU-Rueckfaelle entstehen, weil bestehender Code in ein `gPixmap` rendert
und dieses Pixmap spaeter blitted. Fuer `e2egl` sollte es einen
GPU-kompatiblen Offscreen-Typ geben:

- FBO + GL-Texture als Renderziel
- optional dma-buf/GE2D-kompatible Surface nur fuer Altpfade
- klare Ownership zwischen CPU-Daten, GE2D-Daten und GL-Texture
- Dirty/Sync-Regeln: CPU writes invalidate GL texture, GL writes invalidate CPU
  copy, GE2D writes brauchen Cache/texture invalidation

Damit koennen runde Ecken, Gradienten, gecachte Texte und Skin-Kompositionen
auf der GPU entstehen, statt vorher in CPU-Pixel geschrieben zu werden.

### 2. gPixmap-Operationen auf GLES abbilden

Aktuelle CPU-Kandidaten:

- `gPixmap::fill()`
- `gPixmap::drawRectangle()`
- weitere `gPixmap::blit()`-Sonderfaelle ausserhalb der ersten 32-bit
  Rounded-Texture-Pfade
- 8-bit/palettierte Blits
- AlphaBlend/AlphaTest-Sonderfaelle

Ziel:

- Wenn Ziel und Quelle GPU-faehig sind: GLES/FBO-Pfad.
- Wenn Quelle/Ziel nur CPU sind: alter Pfad bleibt Fallback.
- Wenn GE2D schneller/passender ist: GE2D nur fuer einfache copy/fill/blend
  verwenden, nicht fuer komplexe Shader-Effekte.

### 3. Kompositor modernisieren

Der aktuelle Immediate-Mode wurde fuer persistente Framebuffer entwickelt.
Ein moderner EGL-Pfad sollte mittelfristig besser zwischen diesen Modi waehlen:

- Immediate direkt in EGLSurface fuer einfache Faelle.
- Buffered/FBO-Komposition fuer komplexe Skins.
- Finale Composition als ein GLES-Pass auf die EGLSurface.
- Optional damage tracking, aber mit sicherem Full-Repaint nach Surface-Reset.

Das reduziert Flicker-/Dirty-Probleme und macht Animationen sauberer.

### 4. Shader-Bibliothek erweitern

Sinnvolle Shader-Bausteine:

- solid rect
- gradient rect
- rounded rect
- rounded texture
- texture alpha-test
- texture alpha-blend
- 8-bit mask + color
- glyph batch
- shadow/outline text
- simple blur/drop-shadow optional spaeter

Jeder Shader sollte GLES2-kompatible Fallbacks haben, solange GLES2 relevant
ist.

### 5. Textpfade vereinheitlichen

Normaler Text laeuft schon ueber Glyph-Atlas. Bereits umgebaut:

- cached scrolling text in `eLabel` bei Hardware-DC
- cached listbox text in `eListboxPythonStringContent` bei Hardware-DC
- einfacher `eTextPara`-Cache fuer scrollende Label-/StringContent-Texte bei Hardware-DC

Weiter zu pruefen/umzubauen:

- Text mit Border/Shadow
- RT_BLEND/RT_WRAP/Sonderausrichtungen
- sehr grosse Glyph-Atlanten und Atlas-Eviction

Ziel ist: Kein kompletter Text mehr als CPU-Bitmap, wenn ein aktiver
Hardware-DC vorhanden ist.

### 6. Texture-Upload und dma-buf stabilisieren

Fuer Performance sollten grosse Pixmaps spaeter wieder dma-buf-importiert
werden koennen. Dafuer fehlen noch sichere Regeln:

- Cache-Sync nach CPU writes
- Cache-Sync nach GE2D writes
- korrekte DRM FourCCs fuer ARGB/BGRA
- Pitch/Offset korrekt pruefen
- Fallback auf RGBA Upload bei Treiberproblemen
- Debug-Logs nur begrenzt, damit Startup nicht zugemuellt wird

Kleine Skin-PNGs sind mit normalem `glTexImage2D` oft schnell genug. Grosse
Picons/Hintergruende koennen spaeter gezielt dma-buf nutzen, wenn Sync und
Format sicher sind.

### 7. Tests und Debug

Sinnvolle Testfaelle:

- Spinner waehrend busy main thread
- StartWizard/LocaleWizard
- MetrixHD Hauptmenues
- Listbox Scroll hoch/runter
- kleine alphatest PNGs
- grosse Hintergrund-PNGs
- Picons
- RT_BLEND Text
- runde Ecken mit und ohne Gradient
- 720p, 1080p und 2160p Videomode-Wechsel
- OSD Animation Settings: fade, popup, slide, stripes

Wichtige Logs:

```text
[gEGLDC] EGL swap behavior: preserved
[gEGLDC] dmabuf import: yes/no
[gTextureManager] using RGBA texture upload...
[gTextureManager] glTexImage2D 32-bit upload failed...
[gFontAtlas] initialized...
[dreamGE2D] acceleration active...
[e2egl:gPixmap] drawRectangle-gradient-cpu...
[e2egl:gPixmap] blit-rounded-cpu...
```

## Leitlinien fuer neue Arbeit

- Neue Features zuerst ueber bestehende `gPainter`/`gDC` Semantik anbinden.
- Kein alter VU/libvugles2-Code reaktivieren.
- Kein DreamOS-Closed-Source blind nachbauen; nur beobachtetes Verhalten und
  offene Schnittstellen verwenden.
- Fallbacks erhalten: Wenn EGL oder ein Shader nicht geht, darf die Box nicht
  unbootbar werden.
- Nicht-`e2egl`-Boxen duerfen keine Verhaltensaenderung bekommen.
- Debug-Logs begrenzen, wenn ein Problem geloest ist.
- CPU-Pfade nur als Kompatibilitaets-Fallback behalten, nicht als Zielzustand.

## Kurzfassung fuer Entwickler

`e2egl` ersetzt nicht Enigma2s UI-Modell. Es ersetzt den Ausgabekanal unter der
bestehenden `gPainter`/`gDC` API. Alles, was direkt auf dem aktiven `gEGLDC`
landet, kann GPU-native gerendert werden. Alles, was vorher in ein klassisches
`gPixmap` rendert, bleibt vorerst CPU/GE2D-lastig. Die naechste grosse Aufgabe
ist deshalb nicht nur "mehr Shader", sondern ein sauberer GPU-Offscreen-Pfad
fuer Pixmaps/FBOs, damit auch runde Ecken, Gradienten, gecachte Texte und
komplexe Skin-Kompositionen vollstaendig ueber GLES laufen koennen.
