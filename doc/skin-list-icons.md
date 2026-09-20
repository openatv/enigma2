# Native File and Movie List Icons

`Components.FileList` and `Components.MovieList` can draw status/type icons
with the shared icon font instead of loading PNGs. This is an explicit skin
opt-in; neither E2 nor FileCommander changes the default for existing skins.
No C++ change is required. `Components/SkinIcon.py` must be installed alongside
the updated components.

## XML Contract

```xml
<fonts>
    <font filename="/usr/share/fonts/enigma2icons.ttf" name="enigma2icons" scale="100" />
    <alias name="FileListIcons" font="enigma2icons" size="24" />
    <alias name="MovieListIcons" font="enigma2icons" size="20" />
</fonts>
<parameters>
    <parameter name="FileListNativeIcons" value="1" />
    <parameter name="FileListIcon_directory" value="59828,yellow,yellow" />
    <parameter name="FileListIcon_movie" value="59765,accent,accent" />
    <parameter name="FileListIcon_py" value="60032,yellow,yellow" />
    <parameter name="MovieListNativeIcons" value="1" />
    <parameter name="MovieListIcon_folder" value="59828,yellow,yellow" />
    <parameter name="MovieListIcon_record" value="60038,red,red" />
    <parameter name="MovieListIcon_play_record" value="60039,red,red" />
    <parameter name="MovieListIcon_part_2_4" value="60035,accent,accent" />
</parameters>
```

Colours must be defined by the skin. A mapping accepts a decimal Unicode
codepoint, optionally followed by the normal and selected colours. Omitted
colours inherit the list's foreground colours. The codepoint must exist in
the selected font. Missing/invalid mappings fall back individually to the
original PNG and path; no global replacement of arbitrary pixmaps occurs.

## FileList

All current `EXTENSIONS` categories are supported: `music`, `picture`, `movie`,
`iso`, `playlist`, `7z`, `tar`, `cfg`, `html`, `ipk`, `log`, `lst`, `py`, `pyc`,
`rar`, `sh`, `txt`, `xml`, `zip`.

Additional keys: `file` (unknown extension), `directory`, `storage`, `parent`,
`current`, `lock_on`, `lock_off`, `link_arrow`, `link_error`.

The existing `FileListIcon`, `FileListMultiIcon` and `FileListMultiLock`
geometry parameters remain authoritative. Font slots 1 and 2 are reserved
for icons and half-size link badges in opted-in lists; text retains slot 0.
Link state remains visible alongside the type, not instead of it. Multi-selection
retains its separate checkbox. Extension classification and row payloads,
file actions, sorting, filtering and navigation are unchanged.

FileCommander uses this shared component for both panes. It needs no duplicate
icon lookup or file-action changes. Other users of the modern FileList benefit
as well. The deprecated standalone `FileEntryComponent` remains PNG-based:
its external callers control their own fonts and cannot safely be opted in here.

## MovieList / MovieSelection

Keys: `folder`, `trash`, `unwatched`, `play`, `record`, `play_record`, and
`part_0_4` through `part_4_4`. The five part icons retain E2's existing
percentage bucket calculation. Recording and playing still take priority over
watched state. Neither resume files nor recording behaviour are changed.

Slot 2 holds the icon font. Its size is capped to the available row height,
including the two-line list mode. Existing icon/progress/no-icon preferences
are retained. Progress bars/squares are still drawn natively; picons and
e2MDB artwork remain actual images.

Custom components that reuse the returned `SkinIcon` objects must render them
with their `entry(pos, size, font)` method, not pass them to a pixmap renderer.
This opt-in is for the standard components, not a promise about every private
third-party list implementation.

## Font Delivery

Eight additive SVG glyphs live in `enigma2iconfont/icons/other`: `file_code`,
five `progress_*` states, `record`, and `play_record` (60032-60039). Existing
codepoints, outlines and metrics are retained. E2 delivers the built TTF via
`enigma2-fonts`; Umbra must not bundle another `enigma2icons.ttf`.

The separate Metrix weather font and its codepoint numbering are unchanged.
Ship the E2 Python changes and updated font before enabling these mappings in
a released skin. This source change has not assigned a new image version.
