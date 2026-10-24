# Movie selection styles (AML)

AML adds configurable list and grid rendering to the existing `MovieSelection`
and `MovieList`, an optional catalogue, artwork, multiple selection, a movie
information bar and receiver display layouts. Local folders remain usable without
e2MDB. See [the provider and action contract](movie-library-api.md).

## Settings and compatibility

- `config.movielist.screenStyle` selects a screen with `base="MovieSelection"`.
  The empty value uses the existing `MovieSelection` / `MovieSelectionSlim` fallback.
- `config.movielist.widgetStyle` selects a `component="movieList"` template.
  The empty value uses the existing renderer and is the default.
- Default-skin styles are `compact`, `detailed`, `tiles`, `tilesLarge`, `posters`,
  `posterList`, `classic` and `classicExtended`.
  Their IDs are independent of their translated labels. Templates using `Poster`
  are hidden when no registered provider offers `details`; text grids remain
  available. A saved unavailable style falls back to the existing list.
- Screen layout and entry style can be combined independently. Saving setup applies
  the change in the current screen and restores the selected service. Up/down moves
  between grid rows; left/right uses the native listbox navigation. Playback next/
  previous still moves by one entry.
- Existing config paths, service references, `MovieList` constructor, list tuples,
  widget names and `WHERE_MOVIELIST` actions remain in place. EMC settings are not
  imported. EMC remains an optional feed package.
- `config.movielist.libraryProvider` defaults to `off`; `auto` selects the highest
  priority installed provider. `e2mdb` explicitly selects the e2MDB adapter.
- `config.movielist.startView` selects `folders` (default) or `library`. A missing
  provider always leaves folders available. Both views use the same `MovieSelection`
  instance. MENU opens its shared context menu; View switches between files/folders
  and movies/series. EXIT at catalogue root and RED close the selection directly;
  EXIT inside a series or season returns to its parent level.
- `config.movielist.playerStyle` selects a screen with `base="MoviePlayer"`.
  `MoviePlayerAdvanced` and `MoviePlayerClassic` provide metadata information bars;
  empty retains the skin default.
- `config.movielist.displayStyle` selects `legacy`, `information` or `artwork`.
  Artwork is offered with an active provider. Displays without an artwork layout
  use information instead.
- `config.movielist.hiddenFolders` contains paths hidden through the folder context
  menu. Hidden folders can be restored from that menu. This is a display preference,
  not access control or a database scanner exclusion.
- Holding PVR/FILE opens the temporary view menu. Screen layout, list/grid style,
  file/database view and sorting apply to the current selection only. The menu
  can restore configured defaults without changing the saved preferences.
- `libraryGrouping` chooses grouped movies/series or all indexed files.
  `librarySort` chooses title, recording date, year or rating; `libraryEpisodeSort`
  independently chooses episode order or one of those sorts. e2MDB applies sorting
  before pagination, so changing pages preserves the global order.

## Virtual folders and collections

`virtualGrouping` is disabled by default. Enable series/episode recognition or
title grouping, with a configurable `groupSeparator`, `groupMinimum` and
`groupFoldersFirst`. Grouping changes the displayed list; it never moves recordings.
The context menu can disable and re-enable grouping for individual directories.
Existing per-directory E2 sorting preferences continue to apply.

Virtual collections are named lists of physical movie references. The context menu
creates, opens, renames or removes collections and adds/removes selected movies.
Definitions and bounded display snapshots are kept in the native Enigma2 settings,
so they do not require new directories on media storage. Collections can contain
movies from different folders. Deleting a collection keeps its movie files.
Successful AML file operations update collection references; external filesystem
changes do not automatically update these saved references. Trashed members are
hidden until restored. Database view can display a collection from its snapshot
and cached provider data without testing each movie's existence.

## Adding a screen

Use a unique screen name with `base="MovieSelection"` and a `label`. The core
`MovieSelectionWide` is an example with explicit 1280 x 720 coordinates. Keep the
existing widget and source names, especially `list`, `Service`, `DescriptionBorder`,
`waitingtext`, `chosenletter`, the four colour keys and playback/sort indicators.
The existing description behavior reserves the height of `DescriptionBorder` at
the bottom of the list when description display is enabled.

The supplied movie screens are integrated into `oe-alliance-e2-skindefault` and
loaded through the existing emergency/default skin mechanism. Deploy that skin
update with the core changes. Active skins can override the same screen names.

An optional `libraryScreen` attribute on the selection screen names its matching
catalogue screen. For example, `MovieSelectionClassicLeft` selects
`MovieLibraryClassicLeft`. If that screen is missing, the library uses
`MovieLibrarySelection`. This uses the normal screen-name fallback mechanism.
These names select layouts within the existing screen, not nested dialogs.

An optional `simpleScreen` attribute names the layout to prefer without an active
provider. The original screen names remain in the fallback chain. Core selection,
detail and player screens use this for full-width text instead of empty artwork
areas. Third-party screens opt in through the same attribute.

The default selection and detail screens share the `MovieColorButtons` panel.
It accepts the existing colour-key sources and widgets. The legacy list keeps the
existing row-count and font-size settings, with a minimum height for readable text
and unclipped icons; excessive row counts are limited by that minimum.

## Familiar EMC layouts

The classic layouts follow the structure of EMC's left/bottom selection screens
and their video-window variants. They use existing E2 widgets and converters;
EMC installation, assets and settings are not required.

| Selection screen | Arrangement |
| --- | --- |
| `MovieSelectionClassicLeft` | Cover and details on the left, dense list on the right. |
| `MovieSelectionClassicBottom` | Wide list above cover and details. |
| `MovieSelectionClassicLeftPreview` | Native video window on the left, cover and details beneath it. |
| `MovieSelectionClassicBottomPreview` | Wide list above a native video window, cover and details. |

Each has a matching `MovieLibraryClassic...` screen. Choose `classic` for a
single-line list with progress, status and date, or `classicExtended` for an
additional description/service line. Other list and grid templates can be combined
with these screens. The video window displays the current service using `Pig`;
it does not introduce an automatic preview decoder or a separate playback policy.
`MoviePlayerClassic` provides the raised cover, title, timeline and technical
information familiar from EMC, using the existing player and PVR-state preference.
Its basic variant is a compact 180-pixel bar; `MoviePlayerAdvanced` adds a scrolling
description in a 220-pixel bar. Artwork variants add a raised cover above the bar.
Both show position, remaining time, duration, estimated end time, play/pause/seek
state, audio codec/language, subtitle state, video codec and resolution/frame rate.
They reuse `ServicePosition`, `TrackInfo` and `PliExtraInfo`. Resolution uses the
existing `ResolutionString`, avoiding reuse of a skin's `ServiceInfo` subclass
whose `VideoInfo` output may be an icon index. The existing
`config.usage.movieplayer_pvrstate` selects integrated or separate playback status.

`MovieSelectionOverview` and `MovieSelectionOverviewPreview` provide two additional
arrangements inspired by the former AMS: a cover and list above a broad information
area, optionally with a native video window. They have matching library screens
and simple variants without an active metadata provider. All use the shared colour
buttons and native scrolling text; no old AMS code or artwork is required.

## Adding a list or grid

Add a template to the skin's `skinTemplates.xml` or `skinUserTemplates.xml`:

```xml
<templates>
    <template component="movieList" name="MyMovieTiles" label="My movie tiles"
        orientation="grid" itemWidth="240" itemHeight="160"
        fonts="Regular;24,Regular;18">
        <text index="Title" position="10,10" size="e-20,64" font="0" wrap="on" />
        <text index="Status" position="10,80" size="e-20,26" font="1" />
        <text index="Date" position="10,112" size="e-20,26" font="1" />
        <progress index="Progress" position="10,150" size="e-20,3" />
    </template>
</templates>
```

The existing skin template loader also supports templates embedded under a widget
when no external template file is active, just as for the channel list. Movie
templates use the existing `MultiContentTemplateParser`. Use the implicit default
mode shown above, or a mode named `default`. Orientation is `vertical` or `grid`
on the template. Fonts and coordinates use the selected screen's scale; core
default-skin templates declare `resolution="1280,720"` and use 720-line coordinates
independently of that screen. The default skin installs its normal
`skinTemplates.xml`; active-skin and user templates override matching IDs through
the shared registry. There is no separate movie-template file or private registry.
Vertical templates fill the available width. Grid dimensions must fit the list.

| Field | Content |
| --- | --- |
| `Title` | Local recording title or directory name; existing extension/underscore preferences apply. |
| `Date` | Recording date, or directory/trash label. |
| `Description` | Local service information short description, when available. |
| `ServiceName` | Recorded service name, when available. |
| `Status` | Recording, playing or watched state; the watch-status preference is respected. |
| `Progress` | Numeric watched percentage for a `progress` element; unknown/hidden values are skipped. |
| `Kind` | Directory/trash label or file extension. |
| `Poster` | Decoded local/provider pixmap; use a `pixmap` element with `alpha="blend"`. |
| `Year` | Provider year, when available. |
| `Rating` | Provider rating, when available. |

The fields are read only when used in the compiled template and cached per entry.
Repainting a cached entry does not reread its metadata or cuts file. File duration,
online lookups, directory traversal and artwork decoding are not added to the
render path. Templates compile when the layout or settings change, not per row.
Styled rows consume asynchronously prepared progress. Legacy rows retain the
existing service/cuts behavior. Local service-name queries still run on the GUI
thread; filesystem and receiver performance must be measured on real mounts.

Dynamic fields bind to text, progress and poster pixmaps. Static images and
decorations use the normal template parser. There is no required e2MDB dependency.

## Screen and receiver display sources

Movie selection, the library and the player expose `MovieTitle`,
`MovieDescription`, `MovieDetails`, `MovieLibraryStatus` (text), `MoviePoster` and
`MovieBackdrop` (pixmaps). Selection screens also expose `MovieSelectionStatus`.
`MovieSelectionAdvanced` demonstrates a details column; `MovieLibrarySelection`
can be overridden by the active skin. Existing `Service` remains available.

The summary classes inherit the native `ScreenSummary`, which derives skin names
from the parent screen and adds the class-name fallback. The player uses
`InfoBarMoviePlayerSummary` in `InfoBarGenerics`; no separate player-summary module
or manually constructed name chain is needed. Every movie screen has a matching
display screen named `<parent skin name>Summary`: for example,
`MovieSelectionOverviewSummary`, `MovieLibraryOverviewSummary`,
`MoviePlayerClassicSummary` and `MovieDetailsSimpleSummary`. Skins can override
these names individually. A temporary view change reloads the summary using the
same native name resolution. `MovieContextMenuSummary` also uses `ScreenSummary`.

Shared XML layouts are ordinary panels named `MovieSelectionInformationPanel`,
`MovieSelectionArtworkPanel`, `MoviePlayerInformationPanel` and
`MoviePlayerArtworkPanel`. The original selection layout is shared through
`MovieSelectionLegacyPanel`. The native `condition` attribute reads
`config.movielist.displayStyle`; no extra Python marker sources select a layout.
Small displays only reference their information panel. `MovieDetailsSummary`
uses sources available on the detail screen, including in legacy mode.
`InfoBarMoviePlayerSummary` remains the fallback for other players without AML
metadata sources. Summary widgets use `parent.MovieTitle`,
`parent.MovieDetails` and `parent.MoviePoster`. Selection summaries additionally
provide `name` and `progress`; player summaries retain the native state/speed
sources and `session.CurrentService` for position. Third-party skins can keep their
existing summary screens. Numeric seven-segment displays retain their native layout.

The 22 shipped display XML files cover all 31 movie screen names. Existing
EMC summary screens are retained. Native decoding only runs when artwork is used
by a skin source or poster list template.

## Movie detail screen and long descriptions

INFO on a selected media file opens `MovieDetails`. The default skin provides a
fullscreen backdrop with native gradient overlays, poster, title, metadata and a native `ScrollLabel` named
`details`. GREEN switches movie/file information. Arrow keys scroll the complete
text; RED, EXIT, INFO or OK close the details and preserve the list selection.
Overflow also scrolls automatically using the existing `ScrollLabel.setPos` and an
E2 timer: four seconds at the start, five seconds at the end, then repeat. Manual
scrolling pauses automatic movement for ten seconds. Hidden/closed screens and
text that fits stop the timer; short text stays still.
The text widgets `pageTitle`, `key_red` and `key_green` label the page and actions.
The screen shares the movie information sources above, including
`MovieSelectionStatus`, and reuses the selection summary layouts on front displays.

Descriptions in the supplied list and player layouts use native `Label` scrolling:
`scrollText="direction=top, startDelay=3000, endDelay=4000, stepDelay=100, stepSize=1, repeat=-1, mode=cached"`.
Use `transparent="1"` on text and list widgets so the screen or player panel owns
the background. The supplied selection screens use the skin's `window-bg` colour
uniformly, including the basic layouts without a metadata provider. Cached labels
blend their text over the parent background without opaque rectangles.
Selection changes reset the text position; showing a hidden label restarts its
scrolling with the initial reading pause. No extra renderer, scrolling plugin or
Python animation timer is required.

`MovieContextMenu` requires the native `config` list widget. The standard skin
loader skips incompatible legacy screens that only offer `menu` and uses `Setup`
from the existing fallback list instead.

File details start an optional local `/usr/bin/ffprobe` process when GREEN selects
the file-information page, without starting playback. Probing is limited to eight
seconds and 256 KiB of output and is cancelled
when the screen closes. Missing tools or unreadable files leave the screen usable.
Movie metadata and artwork remain optional; the detail screen also works with the
provider disabled or uninstalled. Native `MovieInfo`/`ServiceEvent` supply the full
local recording description, channel and recording date. Missing provider replies
preserve these values; native file size remains available without `ffprobe`.

Skin templates override core templates with the same ID. Missing or invalid
templates fall back to the existing list. Errors are logged. An invalid template
is not a reason to discard recordings or stored legacy settings.

## Validation

Local syntax, import ordering, Ruff, XML, real temporary-file/SQLite checks and
targeted mocked lifecycle checks cover the implementation. These do not validate receiver rendering, remote key behavior
or performance. Native receiver checks must cover list and grid navigation,
selection, screen teardown, playback and the default-skin fallback.

The native listbox change normalizes `setTemplate(None)` to an empty template
pointer. Without it, returning to the legacy renderer can pass Python `None` to
list operations and crash. The updated native binary must accompany AML; deploying
only the Python and XML files does not contain this fix. The native label update
is also required for transparent cached scrolling, repeated end-position painting
and restarting scrolling after a screen is shown again.
