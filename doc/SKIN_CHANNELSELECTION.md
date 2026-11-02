# Skinning the new ChannelSelection ServiceList

`Components/ServiceList.py` → class `ServiceList` (with its parser mixin
`ServiceListTemplateParser`), used by `Screens/ChannelSelection.py`.

This is Enigma2's second, template-driven service-list renderer, sitting
alongside the classic `ServiceListLegacy` (the old fixed-layout `eListboxServiceContent`
widget, still the default and still documented by the flat `list` widget
attributes such as `serviceNameFont`, `colorServiceRecorded`, `listMarginLeft`,
etc. — see the class itself, those are unaffected by this document).

The new renderer is driven by an `eListboxPythonServiceContent`-style Python
content builder (`buildEntry()`), and its per-row layout is not written in
the screen's `skin.xml` at all — it is described by a **separate
`skinTemplates.xml`** using the same building blocks (`panel`, `text`,
`pixmap`, `progress`, `rectangle`) as `Components/Listbox` templates, but
with a service-list-specific `index=` vocabulary.

A full worked example (five templates, all three modes, every feature)
ships in MetrixHD:
`/usr/share/enigma2/MetrixHD/skinTemplates.xml`.

---

## 1. Opting in

Nothing here is enabled unless the skin explicitly asks for it:

1. Provide one or more alternate `ChannelSelection` screens with `base="ChannelSelection"`
   and a `label`, e.g. (from MetrixHD's `skin_channelselection.xml`):

   ```xml
   <screen name="ChannelSelectionDefault" label="List and event details" base="ChannelSelection" ...>
       <panel name="ChannelSelection" />
   </screen>
   <screen name="ChannelSelectionFull" label="Full screen" base="ChannelSelection" ...>
       <widget name="list" position="70,100" size="1150,528" scrollbarMode="showNever"
           colorServiceRecorded="..." colorServicePseudoRecorded="..." colorServiceStreamed="..."
           foregroundColorServiceNotAvail="..." backgroundColor="..." foregroundColor="..."
           backgroundColorSelected="..." foregroundColorSelected="..." />
   </screen>
   ```

   `config.channelSelection.screenStyle` is populated (in Setup) from every
   skin screen that declares `base="ChannelSelection"`; its `label` is what
   the user sees in the picker. As long as `screenStyle` is empty
   ("Legacy mode", the default), `ChannelSelectionBase.__init__` instantiates
   `ServiceListLegacy` and none of this document applies.

2. Ship a `skinTemplates.xml` next to the skin's main `skin.xml`
   (`reloadSkinTemplates()` resolves it via `SCOPE_GUISKIN` as
   `<skin-dir>/skinTemplates.xml`). Every `<template component="serviceList" name="...">`
   found there populates `config.channelSelection.widgetStyle`'s choice list
   (`getcomponentTemplateNames("serviceList")`), keyed by its `name=` attribute.
   The `screens="..."` attribute on `<template>` is informational only — it is
   never read by the loader/parser; it just documents to humans which screens
   the author designed the layout for.

3. Once `screenStyle` **and** `widgetStyle` are both non-empty, `ChannelSelectionBase`
   uses `ServiceList` instead of `ServiceListLegacy`, and `ServiceList.applySkin()`
   calls `self.readTemplate(config.channelSelection.widgetStyle.value)` to load
   the chosen `<template>` block.

Changing either config value at runtime re-reads the template
(`ChannelSelectionSetup.keySave`) without needing a GUI restart.

---

## 2. `skinTemplates.xml` structure

```xml
<templates>
    <template component="serviceList" name="Single-line list" screens="ChannelSelectionDefault,ChannelSelectionPIG,ChannelSelectionFull" fonts="epg_event;20,epg_event;18,epg_text;15,epg_text;14">
        <mode name="services" itemHeight="24" foregroundColor="..." backgroundColor="..." ...>
            <panel position="10,0" size="e-20,24" layout="horizontal" spacing="10">
                ...
            </panel>
        </mode>
        <mode name="other" itemHeight="24" ...> ... </mode>
        <mode name="bouquets" itemHeight="24" ...> ... </mode>
    </template>
</templates>
```

- `component="serviceList"` — fixed, this is the only component type currently
  registered by `loadSkinTemplates()`.
- `name=` — shown to the user as the `widgetStyle` choice.
- `fonts=` — comma-separated `Name;Size` list, **not** the generic `font=` coordinate
  syntax. Each entry becomes font slot `0`, `1`, `2`, … referenced by widgets via
  `font="0"`, `font="1"`, etc.
- Exactly one `<mode>` per name is expected: `services`, `other`, `bouquets`.
  Missing modes simply render nothing in that list mode.

### 2.1 The three modes

| `mode name` | `ServiceList` constant | When it's used |
| --- | --- | --- |
| `services` | `MODE_SERVICES` | Flat "all services" list (`config.usage.multibouquet` off, or the "all services" bouquet). |
| `bouquets` | `MODE_BOUQUETS` | Normal channel/bouquet list — this is what users see 99% of the time. |
| `other` | `MODE_OTHER` | Everything else (history, favourites-as-flat-list, etc.) — entries use `EntryName` instead of `ServiceName`. |

Only `services` and `bouquets` rows ever get EPG data attached — `other` rows
never fetch events, so EPG-based fields (§4.2) are meaningless there.

### 2.2 Marker/Folder rows come for free — don't duplicate the mode

`other` and `bouquets` rows can be a marker (bouquet separator) or a folder
(sub-bouquet), in addition to a normal service row. You do **not** write
three separate `<mode>` blocks for this. Write **one** `<mode name="bouquets">`
(or `other`) containing all of: the normal `ServiceName`/`EntryName` widget,
a `MarkerImage` + `MarkerName` widget, and a `FolderImage` + `FolderName` widget,
exactly like MetrixHD's `bouquets` mode does. `ServiceListTemplateParser.readTemplate()`
compiles that single block into three variants internally
(`templateDataBouquets`, `templateDataBouquetsMarker`, `templateDataBouquetsFolder`)
by filtering which widgets survive:

- **Plain row**: everything except `MarkerName`, `FolderName`, `MarkerImage`, `FolderImage`.
- **Marker row**: only `ServiceName`/`EntryName` (if no `MarkerName` widget exists)
  *or* `MarkerName` (if one does) + `MarkerImage`.
- **Folder row**: same logic with `FolderName`/`FolderImage`.

`services` mode has no marker/folder variant at all — folders/markers are not
filtered there.

`Number`, `ServiceName`, `EntryName`, `MarkerName` and `FolderName` are
**aliases of the same content slot** (`index` 0 for Number, 1 for the rest) —
whichever one survives the filtering above receives the row's resolved
`info.getName(service)` string at render time. Give `MarkerName`/`FolderName`
their own `foregroundColor` etc. if you want them styled differently; the
*text* itself is the same regardless of which alias was used.

### 2.3 Config-driven item removal

Regardless of what the template contains, these config options strip items
before rendering (`ServiceListTemplateParser.collectAttributes` /
`parseTemplateModes`'s `excludeItemIndexes`):

| Config | Removes `index=` |
| --- | --- |
| `config.channelSelection.showPicon` (off) | `Picon` |
| `config.channelSelection.showNumber` (off), or `config.usage.numberMode == 2` for `services` mode | `Number` |
| `config.channelSelection.showServiceTypeIcon` (off) | `ServiceTypeImage` |
| `config.channelSelection.showCryptoIcon` (off) | `CryptoImage` |
| `config.channelSelection.recordIndicatorMode != 1` | `RecordingIndicator` |

`config.channelSelection.piconRatio` (a percentage) rescales any `Picon`
widget's declared `size=` width, keeping the declared height — set the size
you want at ratio 167 (the default) and it self-adjusts for the other choices.

---

## 3. Panel layout & positioning

`<panel layout="horizontal|vertical|stack|grid" position="..." size="..." spacing="N">`
wraps child widgets in a `SkinContext` (see `skin.py`). Inside a panel, `position=`
also accepts layout keywords in addition to normal coordinates:

| `position=` value | Meaning |
| --- | --- |
| `left` / `right` | Next free slot from that edge, cursor advances by the widget's width + `spacing` (horizontal panels). |
| `top` / `bottom` | Same, vertically (vertical panels). |
| `center` | Centered in the panel's remaining/original extent. |
| `fill` | Consume the panel's entire remaining space. |
| `left,N` / `top,N` etc. | Anchored edge plus a fixed offset on the other axis. |
| absolute (`"10,0"`) / edge-relative (`"e-65,9"`) | Normal skin coordinate syntax (see `SKINATTRIBUTES.md`). |

`autoGrow="1"` on a widget inside a `layout="horizontal"` panel makes it absorb
whatever horizontal space is left over after all `left`/`right` siblings are
placed (used for a flexible EPG title column, e.g. `Title1` in MetrixHD's
"Channel column view").

Nesting `<panel>` inside `<panel>` works (new `SkinContext` per panel); use
`layout="stack"` when you just want absolute positioning within a sub-region
(this is what MetrixHD uses for its picture-list `bouquets` mode).

---

## 4. Widgets and the `index=` vocabulary

Every leaf widget is `<text>`, `<pixmap>`, `<progress>` or `<rectangle>`,
picking its content via `index="<Name>"` (fixed vocabulary, case-sensitive)
or, for `<text>`, a literal `text="..."` (optionally `translate="1"`).
Common attributes: `position`, `size`, `font` (index into `fonts=`),
`foregroundColor`/`backgroundColor` (+`Selected` variants), `cornerRadius`
(`"N"` or `"N;edge,edge"`, same as the generic skin attribute),
`foregroundGradient`/`foregroundGradientSelected` (same syntax as the generic
`backgroundGradient` attribute), `conditional="<python expression>"` — a
single `eval()`-able boolean expression (not comma-separated conditions like
the generic engine's `conditional=`); when it evaluates false or raises, the
element is dropped entirely. `wrap="noWrap|wrap|ellipsis"`,
`horizontalAlignment`/`verticalAlignment` work as usual.

### 4.1 Non-event fields (always available, refer to the *service itself* or its *currently running* event)

| `index=` | Widget | Notes |
| --- | --- | --- |
| `Number` | text | Channel number (bouquets/services only). |
| `ServiceName` / `EntryName` / `MarkerName` / `FolderName` | text | Aliased content slot, see §2.2. |
| `Picon` | pixmap | Scaled by `piconRatio`, needs `config.usage.service_icon_enable`. |
| `ServiceTypeImage` | pixmap | DVB-S/C/T/DAB/stream/catchup icon. |
| `ServiceTypeName` | text | **Reserved, not currently rendered** by `buildEntry()` — mapped but not implemented. |
| `RecordingIndicator` | pixmap | Only shown if the service is recording/streamed/pseudo-recorded. |
| `CryptoImage` | pixmap | Only shown for encrypted services. |
| `ProviderName` | text | **Reserved, not currently rendered.** |
| `FolderImage` / `MarkerImage` | pixmap | See §2.2. |
| `ServiceResolutionImage` | pixmap | **Stub — `buildOptionEntryServiceResolutionPixmap()` always returns `None`.** |
| `IsInBouquetImage` | pixmap | Only shown when the row's "in bouquet" status bit is set. |
| `Progress` | progress | Progress bar of the *currently running* event (same event as the `1`-suffixed fields below). |
| `ProgressText` | text | `"NN%"` of the same event. |
| `Remain` | text | `"+NN min"` remaining. |
| `RemainDuration` | text | `"+remain/duration min"`. |
| `Elapsed` | text | `"NN min"` elapsed. |
| `ElapsedDuration` | text | `"elapsed/duration min"`. |
| `ElapsedRemainDuration` | text | `"elapsed/+remain/duration min"`. |

Only `Number` and `ServiceName`/`EntryName`/`MarkerName`/`FolderName` are
tinted by `recordColor`/`streamColor`/`pseudoColor` (see §5) — EPG text and
the progress fields always use the plain `foregroundColor`.

### 4.2 Event-suffixed fields — append a digit (`1`, `2`, …) for the Nth upcoming event, or `P` for the configured Primetime slot

Base names (append the suffix to these): `Title`, `ShortDescription`,
`ExtendedDescription`, `StartTime`, `EndTime`, `StartEndTime`, `Duration`,
`StartTimeDuration`, `StartTimeEndTimeDuration`, `Description`, `Image`,
`ImageOrPicon`.

```xml
<text index="Title1" .../>         <!-- currently running event's title -->
<text index="StartTime2" .../>     <!-- next event's start time -->
<text index="TitleP" .../>         <!-- the Primetime-hour event's title -->
```

- `Title1` (and `StartTime1`, `Remain`, `Progress`, … with **no** suffix) all
  refer to the **same, currently-running** event — the digit `1` is "current",
  `2` is "next", `3` is "the one after that", etc.
- The highest digit suffix used anywhere in a `bouquets`/`services` mode block
  determines how many upcoming events get fetched from the EPG cache for that
  row (`eEPGCache.lookupEvent(["BDTSE<n>", ...])`) — keep this number as low
  as your layout actually needs, it's a real EPG lookup per row per paint.
- `P` (Primetime) is looked up independently via a *separate*, dedicated EPG
  query keyed on `config.epgselection.graph_primetimehour`/`graph_primetimemins`
  (default 20:15) — it does not count toward, or depend on, the digit-suffix
  event count.
- `Image`/`ImageOrPicon` are pixmap widgets. They render nothing unless a
  provider is registered via `registerServiceListEventPixmapProvider()`
  (an optional plugin hook — the core has none); `ImageOrPicon` additionally
  falls back to the service's picon when the provider returns nothing.

### 4.3 `autoFit` — let one field's width follow another's content

```xml
<text index="ServiceName" position="left,0" size="150,24" autoFit="Title1" font="1" .../>
<text index="Title1" position="left,0" size="380,24" font="1" .../>
```

`autoFit="Title1"` on the `ServiceName` widget measures the actual rendered
text width of the service name; the *next* widget in the same row whose
resolved `index` matches `Title1`'s (i.e. `Title1`/`StartTime1`/… — anything
event-index `1`) has its `position`/`size` shrunk or grown by the difference,
so short channel names don't leave a gap and long ones don't get clipped
before the adjacent EPG column. This is how MetrixHD's single-line list keeps
the title column flush regardless of channel-name length; it is purely a
render-time position/size nudge, it doesn't change font size or wrap the text.

---

## 5. Colors

Two layers, same pattern as the legacy widget:

1. **Widget-level defaults** — set directly on `<widget name="list" .../>` in
   the screen's `skin.xml` (not in `skinTemplates.xml`). These seed
   `ServiceList.widgetAttributes`, which every mode's per-item defaults
   inherit from:

   | Widget attribute | Feeds template default | Default (alpha `00` = invisible) |
   | --- | --- | --- |
   | `colorServiceRecorded` (or legacy `colorServiceRecording`) | `recordColor` | `#00b40431` |
   | `colorServicePseudoRecorded` | `pseudoColor` | `#0041b1ec` |
   | `colorServiceStreamed` | `streamColor` | `#00f56712` |
   | `foregroundColorServiceNotAvail` | `serviceNotAvailColor` | `#00bbbbbb` |
   | `colorFallbackItem` | `fallbackColor` | — |
   | `colorServiceSelectedFallback` | `fallbackColorSelected` | — |

   The `...Selected` counterparts (`recordColorSelected`, `streamColorSelected`,
   `pseudoColorSelected`, `serviceNotAvailColorSelected`) have no legacy alias —
   set them directly under those names if needed. All default to alpha `00`
   (fully transparent), i.e. these features are invisible until either the
   widget tag or a template item gives them a real alpha channel.

2. **Per-mode / per-item overrides** — any of the same attribute names set on
   `<mode>` (mode-wide default) or on an individual widget (highest priority)
   in `skinTemplates.xml` win over the widget-level default.

`serviceNotAvailColor`/`serviceNotAvailColorSelected` apply when the service
can't currently be tuned; `fallbackColor`/`fallbackColorSelected` are a second
fallback tier. `recordColor`/`streamColor`/`pseudoColor` only apply when
`config.channelSelection.recordIndicatorMode == 2` ("Colored text") and the
row isn't marked/multi-selected.

Gradients (`foregroundGradient="start[,mid],end,horizontal|vertical[,alphablend]"`)
work on `<rectangle>` and `<progress>` widgets exactly like the generic
`backgroundGradient` skin attribute.

---

## 6. Minimal example

```xml
<templates>
    <template component="serviceList" name="Simple" screens="ChannelSelectionDefault" fonts="Regular;20,Regular;18">
        <mode name="services" itemHeight="28" foregroundColor="white" backgroundColor="#00000000"
              foregroundColorSelected="black" backgroundColorSelected="#00ffcc00">
            <pixmap index="Picon" position="4,2" size="40,24" alpha="blend" scale="centerScaled"/>
            <text index="Number" position="50,0" size="30,28" font="0" horizontalAlignment="right" verticalAlignment="center"/>
            <text index="ServiceName" position="90,0" size="200,28" autoFit="Title1" font="0" verticalAlignment="center" wrap="noWrap"/>
            <text index="Title1" position="290,0" size="e-90,28" font="1" verticalAlignment="center" wrap="ellipsis"/>
            <progress index="Progress" position="right,10" size="70,8" borderWidth="1" foregroundGradient="green,yellow,red,horizontal"/>
        </mode>
        <mode name="other" itemHeight="28" foregroundColor="white" backgroundColor="#00000000"
              foregroundColorSelected="black" backgroundColorSelected="#00ffcc00">
            <pixmap index="MarkerImage" position="4,2" size="24,24" alpha="blend" scale="centerScaled"/>
            <pixmap index="FolderImage" position="4,2" size="24,24" alpha="blend" scale="centerScaled"/>
            <text index="EntryName" position="34,0" size="e-40,28" font="0" verticalAlignment="center"/>
            <text index="MarkerName" position="34,0" size="e-40,28" foregroundColor="green" font="0" verticalAlignment="center"/>
        </mode>
        <mode name="bouquets" itemHeight="28" foregroundColor="white" backgroundColor="#00000000"
              foregroundColorSelected="black" backgroundColorSelected="#00ffcc00">
            <text index="Number" position="4,0" size="30,28" font="0" horizontalAlignment="right" verticalAlignment="center"/>
            <pixmap index="Picon" position="40,2" size="40,24" alpha="blend" scale="centerScaled"/>
            <pixmap index="MarkerImage" position="40,2" size="40,24" alpha="blend" scale="centerScaled"/>
            <pixmap index="FolderImage" position="40,2" size="40,24" alpha="blend" scale="centerScaled"/>
            <text index="ServiceName" position="86,0" size="200,28" autoFit="Title1" font="0" verticalAlignment="center" wrap="noWrap"/>
            <text index="MarkerName" position="86,0" size="e-90,28" foregroundColor="green" font="0" verticalAlignment="center"/>
            <text index="FolderName" position="86,0" size="e-90,28" font="0" verticalAlignment="center"/>
            <text index="Title1" position="286,0" size="e-90,28" font="1" verticalAlignment="center" wrap="ellipsis"/>
            <progress index="Progress" position="right,10" size="70,8" borderWidth="1" foregroundGradient="green,yellow,red,horizontal"/>
        </mode>
    </template>
</templates>
```
