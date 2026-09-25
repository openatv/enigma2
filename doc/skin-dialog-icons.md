# Opt-in font icons for choice lists and message boxes

These extensions use native MultiContent text and eLabel rendering. They do not
change the default PNG path and do not require a C++ change or bitmap conversion.
Register the icon font in the skin before enabling the corresponding option.

## ChoiceList

As with `VirtualKeyboardNative`, the skin explicitly enables the native path:

```xml
<fonts>
    <alias name="ChoiceListIcons" font="enigma2icons" size="24" />
</fonts>
<parameters>
    <parameter name="ChoiceListNative" value="1" />
    <parameter name="ChoiceListIcon_red" value="0xEA12,red,red" />
    <parameter name="ChoiceListIcon_menu" value="0xE911" />
</parameters>
```

`ChoiceListIcon_<key>` specifies a Unicode codepoint followed by optional normal
and selected foreground colors. Without colors the widget's colors are used;
with only one color that color also applies to the selected entry. Codepoints
are skin-configurable and must exist in the selected font. The sample red key
uses the existing `stop` glyph in enigma2icons.

- `ChoiceListNative` absent or zero: unchanged PNG lookup and drawing.
- Enabled: single ASCII digits use the normal list font; configured keys use
  `ChoiceListIcons` (fallback alias: enigma2icons at the ordinary list font size).
- Unknown or invalid glyph definitions retain the existing PNG fallback.
- Empty keys, `dummy`, `none` and separator entries retain their behavior.
- `ChoicelistIcon`, `ChoicelistIconExpanded` and `ChoicelistIconVerticalline`
  continue to define icon geometry. Font size and geometry must fit the row.
- Key actions, return values, callbacks, ordering and summary data are unchanged.

This affects the shared ChoiceList component, including ChoiceBox, channel
context menus and other screens that already use that component. It does not
replace arbitrary plugin-owned pixmaps or custom lists.

## MultiPixmap / MessageBox

The opt-in is widget-local, so an embedded plugin screen can continue using its
PNGs even when the active skin supports font icons elsewhere:

```xml
<widget name="icon" position="20,84" size="53,53"
    pixmaps="icons/input_question.png,icons/input_info.png,icons/input_warning.png,icons/input_error.png,icons/input_message.png"
    iconFont="enigma2icons;48"
    iconGlyphs="0xE94F,0xE90A,0xE90B,0xE909,0xE9E4"
    iconColors="accent,accent,yellow,red,foreground"
    foregroundColor="foreground" halign="center" valign="center"
    alphatest="blend" transparent="1" conditional="icon" scale="1" />
```

Both `iconFont` and a valid `iconGlyphs` list are required. The component creates
an eLabel instead of an ePixmap only for this explicit opt-in. In that mode it
does not load the declared PNGs and ignores their `scale` attribute. Glyphs are
rasterized at the requested font size; standard label alignment and blending
attributes apply. The existing `setPixmapNum(index)` selects the glyph instead
of the PNG. Direct pixmap operations are not part of the font-icon path.

`iconGlyphs` is a comma-separated list of decimal or `0x` Unicode codepoints.
For MessageBox the order is question, information, warning, error, message.
`iconColors` is optional; if supplied, provide exactly one color per glyph.
Otherwise the widget foreground color applies. Empty/invalid codepoints or an
incomplete opt-in preserve the PNG path. Missing glyphs inside an otherwise valid
font cannot be detected by this Python component; the skinner must validate them.

The `pixmaps` declaration can remain as a compatibility fallback. Older E2
versions without this extension may report the unknown icon attributes and will
still use their normal MultiPixmap PNG path. Existing skins without the new
attributes are unchanged. Separate MessageBox aliases must opt in as well.

Reused modal message boxes in font-icon mode hide the existing icon for
TYPE_NOICON and show it again when the next message requests an icon. This
avoids a stale glyph without changing response or timeout handling. Existing
PNG skins retain their previous visibility handling, including custom applets.

## Verification

Run the receiver-independent regressions with:

```sh
python3 -m unittest discover -s tests -p test_dialog_icons.py -v
```

Also check a receiver at the supported resolutions: colored/digit choice keys,
unmapped custom PNGs, tree entries, all five message types, TYPE_NOICON, repeated
modal messages and a skin without the opt-ins. Measure performance separately
before making any broader rendering defaults mandatory.
