GLES TestLab - OpenATV development option

Configure with --with-egl --enable-gles-testlab. Default is disabled.
--disable-gles-testlab omits the native diagnostic binding, recorder and plugin.
The actual renderer improvements are independent of this test option.

OE recipe override for a local test build:
EXTRA_OECONF:append:pn-enigma2 = " --enable-gles-testlab"
The normal plugin splitter produces enigma2-plugin-extensions-glestestlab.
Install that package together with the matching enigma2 package. Source-package
availability depends on the image recipe. No image-wide activation is required.

Open via Plugins or the extensions menu. Red closes, Green measures/stops the
current page, Yellow measures all pages, Blue/Right advances, Left goes back.
Keys 1 and 2 record a MANUAL visual verdict. No verdict means unreviewed.
Results: <configured debug log directory>/gles-testlab/<timestamp>-<pid>.json
and .csv (usually /home/root/logs/gles-testlab). Metadata includes the platform,
skin, relevant renderer environment switches and binary/plugin hashes.

Eight pages cover 8-bit palette alpha-test/blending, real 32-bit CPU/hardware
surfaces, opaque/transparent fills, selected rounded-corner masks and borders,
two/three-color horizontal/vertical gradients, overlapping layers, text and
new-texture upload pressure. Existing skin widget APIs are used for shapes.
This is a fixed initial matrix, not exhaustive coverage of all possible skins.

16-bit sources use E2's big-endian BGR565 storage and a real two-byte RGB565
GLES upload. rgb565Uploads counts this path. RGB565 has no pixel alpha.
8-bit palette entries have alpha; 32-bit fixtures contain straight BGRA alpha.
Gradient from transparent at the top to opaque at the bottom: red, green, blue,
white columns. Compare the lower 32-bit CPU/HW cases with the upper 8-bit blend
case, away from rounded edges. Neither channel order nor alpha should differ.
Blend-off intentionally writes source alpha; the video underneath may show.

Each run warms for 2 seconds then records 6 seconds of full-screen repaint
requests at 20 ms. These timer requests are NOT measured render FPS. Page 7
also recreates sources every tick; 8-bit sources may hit the content cache.
Page 8 recreates three CPU and three requested hardware targets every tick.
The pairs cover fills, rounded alpha gradients/borders and rounded alpha blits.
The color bars are checked through CPU memory; zero mismatches verifies all
51200 pixels. sharedNative=true proves a native shared target was created;
physicalBacking alone does not. On DM9x0, E2EGL_DREAMBCM_ION_TARGET=1 enables
the experimental shared write path; default off. Ineligible layouts/platforms
fall back to CPU. Initial ownership uses glFinish and an uncached ION mapping;
no asynchronous fence optimization or speed improvement is presumed.
The recorder retains at most 4096 frames and reports dropped records. The
first frame crossing capture start is excluded. The final queued work can
complete after capture stops. Boundaries therefore describe a timed sample.
The run stops with resource-growth if the one-second sample detects more than
64 additional FDs since measurement started. Check the log and idle resources
before repeating; an early stop is not a successful performance result.

drawUs and operation counters are existing CPU-side renderer wall timings;
swapUs measures present-call/wait cost. They are not GPU timer queries and
do not establish scanout time. intervalUs includes idle. Do not add overlapping
operation times to drawUs. CPU time covers the entire E2 process, including TV
and instrumentation. RSS and FD counts do not measure total physical GPU/ION
memory. Capture overhead and debug settings must match between comparisons.

The screen scales from a 1920x1080 design to the actual E2 desktop. This does
not switch HDMI or the skin. Compare FHD and WQHD after changing the active
skin and restarting E2. On DM920 the current WQHD scene still outputs 1080p.
Other platforms use the same tests; physicalBacking only means the allocator
provided a physical address. It does not by itself prove ION or successful
import. ionUploads is counted only by the actual DreamBCM import path.

Skinners: GlesTestLabScreen generates its geometry and stable label0..label63,
pixmap0..pixmap23, title/details/status/footer names. Keep diagnostic fixture
colors and rectangles fixed when comparing builds. Styling a separate shell
is possible; modifying test geometry changes the workload.

Hardware checks: inspect all pages, compare 8/32-bit colors and transparency,
check each rounded edge and gradient, run all pages twice, abort/restart a run,
close/reopen, then check FD/RSS return and E2 log. Repeat with PiG/TV and on each
target platform. A successful build or recorder run does not certify visuals.
