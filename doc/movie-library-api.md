# Movie library providers and actions (version 1)

The native movie selection remains the owner of service references, playback,
selection, resume/cut files and user file operations. Providers supply plain
metadata and catalogue pages. They do not replace core classes or widgets.

## Registration and lifecycle

Import `movieLibrary` from `Components.MovieLibrary` during plugin session startup.
Register a stable provider ID with `movieLibrary.register(name, provider,
version=1, priority=0)`. Unregister with `movieLibrary.unregister(name, provider)`
on shutdown. The object identity prevents one plugin from removing another
provider. A provider supplies `label`, `capabilities` and a synchronous
`request(operation, parameters)` method. Capability names are `details`, `browse`,
`members`, `seasons`, `filters` and `changes`; providers need only expose supported operations.
The supplied e2MDB adapter implements all six.

Core requests execute in a dedicated Twisted pool with at most two workers.
Only plain Python data may cross that boundary. Providers must not use sessions,
Enigma services, GUI widgets or callbacks from their request method. Network
providers must enforce their own deadlines. e2MDB uses an overall three-second
socket deadline and a four-MiB response limit. Core filesystem reads run in the
worker too; kernel mount timeouts cannot be cancelled by a Python thread.

One client allows one active request and one pending request. Navigation replaces
the pending request. Closing, cancelling, changing providers or replacing their
registration discards stale responses. Main-thread callbacks receive a dictionary;
failures return `error: "unavailable"` and available local details. Keep references
to the client and call `close()` when its owner closes.

## Request/response contract

| Operation | Parameters | Response |
| --- | --- | --- |
| `details` | `paths`: at most 64 unique absolute physical paths | `items`: dictionary keyed by that exact path; never substitute another episode or media variant |
| `browse` | one-based `page`, `type` (`all`, `movie`, `series`), `query`, `year`, `genre`, `cast`, `view` (`library`, `files`, `latest`, `pending`), `sort`, `hiddenFolders`; for `latest`: `since`, `limit`, `root` | `items`: at most 48 dictionaries, `hasMore`; optional `physical` and `indexing` |
| `members` | `id`: group ID or media ID, `page`, optional `season`, `sort`, `hiddenFolders` | exact physical `items`, `hasMore`, optional `seasons` and `indexing` |
| `seasons` | `id`, `hiddenFolders` | `seasons`: integer season numbers; -1 represents unassigned season |
| `filters` | `field` (`year`, `genre`, `cast`), one-based `filterPage`, optional `filterAfter` cursor, current `query`, `type`, filters and `hiddenFolders` | `values`: up to 100 strings, `hasMore`, optional `indexing` |
| `changes` | `events`: at most 64 ordered file-operation dictionaries | `acknowledged`: successfully applied operation IDs; optional `errors` dictionary |

An item contains `path`, `id`, `title`, `description`, `type`, `series`, `season`,
`episode`, `year`, `genres`, `rating`, `poster`, `backdrop`, `group`, `pending`,
`duration` (seconds) and `recordedAt` (Unix seconds). Optional fields may be empty.
Additional optional detail fields are `votes`, `runtime`, `released`, `ageRating`,
`countries`, `cast`, `crew`, `tagline`, `originalTitle` and `fileSize` (bytes;
the e2MDB adapter also retains the earlier `size` alias). Cast and
crew can contain strings or dictionaries with `name` and `character`/`job`/`role`.
The INFO screen uses these fields; technical streams are read from the selected
physical file asynchronously and do not require a metadata provider.
`group` is an opaque stable grouping key; a season and episode must describe the
exact physical file. Artwork paths must be absolute local paths. Providers own
downloads and cache files; UI code never downloads URLs while painting.

`poster` is portrait artwork: a season poster for episodes, falling back to the
series poster. Grouped series use the series poster. Optional `preview` supplies
the landscape episode still; never substitute it for a portrait poster.

The optional `filters` operation supplies native selection lists; free-text search
continues to use the keyboard. Exclude the requested field's own constraint when
listing its available values, but retain other filters and hidden folders.
Selections set `exactFilters: true` on subsequent catalogue requests. e2MDB keeps
filter values in an indexed SQLite table, updated with the existing bounded
256-record catalogue batches. Filter pages return at most 100 values and a
next-page indicator. Existing providers without this capability retain text
input. The filter index never scans movie storage or downloads artwork.
`filterAfter` is the last value of the previous page (empty on the first page).
Cursor-aware providers can seek directly to it instead of skipping earlier pages;
years sort descending, other fields ascending. Core retains cursors for going back.

Sort values are `title`, `titleDesc`, `newest`, `oldest`, `year` and `rating`;
members additionally accept `episode`. Sort the full result before applying the
page limit. Unknown sort values must use a safe default, never an SQL expression.

For `view="latest"`, `since` is an inclusive Unix recording-time cutoff (0 means
all dates), `root` optionally restricts results to that directory and descendants,
and `limit` selects the newest N records (0 means unlimited). Apply exclusions,
scope and cutoff first, then the newest-N limit, then the requested presentation
sort, and finally pagination. This keeps the same collection when changing its
display order. Use indexed paths and timestamps; do not stat media storage or read
exclusion files while serving the query. e2MDB falls back to indexed file mtime
when recording time is unknown.

Requests can include `databaseOnly: true`. In this mode the core skips local
sidecars, existence checks and `.cuts` reads. Providers must serve stored metadata
without opening or scanning the movie path. The catalogue uses cached service
information instead of native filesystem-backed service information; the live
player resume cache supplies available progress. Opening INFO stays in this mode;
playing a movie or explicitly requesting its technical file information may wake
storage. Database and artwork caches themselves must be on always-available storage
if the movie disk is to remain asleep. Cache keys separate this mode from ordinary
filesystem detail requests.

Outside database-only mode, the core overlays local manual title/description edits and local poster fallbacks.
Local posters are `<stem>.jpg`, `<stem>.png` or `<filename>.jpg`. Manual overrides
use `<filename>.aml.json`, version 1. Existing `.meta` files are updated too.
Series group titles are kept separate from individual episode overrides.

Metadata is cached for up to 60 seconds, at most 256 paths. Artwork is decoded
asynchronously through `ePicLoad` with a 12-MiB decoded cache per information
controller. Selection changes wait 180 ms and prepare at most 49 nearby paths.
Front displays share these sources. Unused poster/backdrop sources do not decode.
The native movie-detail screen requests larger artwork sizes through the same
bounded loader. e2MDB's compatibility EventView hook delegates to native AML movie
details when the core supplies the integrated views; older cores retain its
configured media EventView behaviour.
After file operations caches are invalidated. Progress uses existing `.cuts` and
the live core resume cache; the provider does not own a second watch-state database.

## Text companions, EIT and cuts

The existing `Tools.MovieInfoParser` accepts a service reference or physical path.
Description fallbacks are tried as `<filename>.txt`, `<filename>.info`,
`<stem>.txt`, `<stem>.info`, bounded to 256 KiB, using UTF-8/BOM or legacy Latin-1.
Native/provider descriptions take precedence. These companions also participate
in AML file bundles.

`config.movielist.eitMode` selects disabled, context-menu creation (default), or
automatic creation when filesystem movie information becomes available. Single
and marked files use normal E2 jobs and `Tools.EITFile`; MKV and other movie files
receive `<stem>.eit`. Existing EIT files are never replaced. Automatic creation is
not performed while browsing the database. The writer bounds DVB descriptor sizes,
splits UTF-8 descriptions on character boundaries and uses numbered extended-event
descriptors. It does not add another metadata scraper.

Cut records retain the standard big-endian 64-bit PTS plus 32-bit type format:
0 IN, 1 OUT, 2 chapter marker, 3 last position, 4 saved previous position, 5 length.
OUT boundaries are not treated as movie duration. Reset/status and marker actions
preserve unrelated cut entries. The context menu removes chapter markers or restores
the saved previous position; existing cut-list plugins remain available through
`WHERE_MOVIELIST`. Playback uses the native marker actions. The existing
`config.usage.nativeCuesheetSupport` controls extended position/length persistence;
`config.movielist.saveLastAsMarker` optionally keeps the previous position as a
chapter marker when starting a movie. Background preview respects the native
do-not-remember flag.

## File operations and catalogue synchronization

Core jobs support copy, move, rename, trash, restore, permanent delete, metadata
editing and watched/unwatched state. A bundle includes the media, TS split parts,
known sidecars, local artwork, language-qualified subtitles and AML sidecars.
Unknown unrelated files are left alone. Existing destinations are never replaced.
Symlinks, ambiguous shared companion files, active recording/playback and recently
written movies are rejected for mutation. A `dir.lock` blocks changes in that
directory. Bytes are copied in one-MiB chunks with progress and cancellation.
Source removal only starts after all destination files are complete.

The job records an intent before mutation in `/etc/enigma2/moviechanges.json`.
Each event has `id`, `action`, `path`, optional `target`, `timestamp` and action
data such as `title`/`description`. The journal additionally keeps local recovery
data; providers must ignore extra fields. Operations are ordered, replayable and
must be idempotent by ID. Acknowledge only changes committed to provider storage.
Do not acknowledge failed changes to unblock later dependent renames.

The journal is capped at 2048 outstanding intents. A full/unwritable journal
prevents further database-aware file mutation. Recovery retains ambiguous intents
while storage is unavailable and can recover a complete destination after partial
source cleanup as a copy. Synchronization retries while pending. Providers that
advertise `changes` remain recipients even while metadata display is disabled.

The e2MDB implementation uses transactions, preserves matches and artwork cache
aliases across moves/copies, stores manual overrides independently of provider
results, and prevents older scans from undoing a rename. Its incremental catalogue
index processes at most 256 changed rows per request and pages groups/members in
SQLite. It does not reuse the approximate offsets of the older web browser.

Native whole-directory operations, external filesystem tools and other plugins
remain scanner-owned: rescan e2MDB after those changes. The new per-movie journal
does not claim to monitor arbitrary filesystem changes. Trashed entries and
metadata-only orphan rows are excluded from the catalogue. Files not yet scanned
remain reachable in the ordinary folder view.

Trash stores `<filename>.aml.trash.json` with the original location. Restore does
not overwrite an existing original. Older trash without that sidecar can be moved
to a chosen directory. Existing trash retention/reserve settings remain native.

## Extension actions and playlists

`movieLibrary.registerAction(name, label, callback, multiple=False)` adds an action
to folder/movie and physical catalogue-entry menus. The callback runs on the GUI
thread as `callback(session, tupleOfServiceReferences)`. Set `multiple=True` only
if the action handles multiple references. Unregister using
`unregisterAction(name, callback)`. Long work belongs in jobs or a worker.
Existing `PluginDescriptor.WHERE_MOVIELIST` actions keep their single-service
calling convention in both views.

The play queue deduplicates physical paths, supports ordering/removal and contains
at most 1024 movies. M3U/M3U8 loading accepts local absolute paths and paths relative
to the playlist file, including mounted shares. Saving is UTF-8 and refuses to
overwrite an existing playlist. Network stream URLs and legacy EMC `.e2pls`
formats are outside this movie-file contract. Playback uses the released core
playlist and its existing EOF/loop preferences, with the normal timeshift check.
Queues accept video/audio files. DVD images open individually through the existing
DVD player handler, including when selected in the catalogue; they are not mixed
into the core player's queue. Pictures retain their native single-file handling
and are excluded from movie bulk selection.

No EMC settings or EMC-specific script paths are imported. Maintenance automation,
remote-recording detection and specialized players remain optional extension
responsibilities; the feed version of EMC remains available.
