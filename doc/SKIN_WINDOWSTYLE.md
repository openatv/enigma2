# Enigma2 Skin — `<windowstyle>`

The `<windowstyle>` element is the central place where a skin defines its global visual defaults:
window chrome (title bar, borders), default colors for all widgets, scrollbar sizes, and font assignments.
It lives at the top level of the skin XML file, not inside a `<screen>`.

---

## Structure overview

```xml
<skin>
    <colors> ... </colors>
    <fonts>  ... </fonts>

    <windowstyle type="skinned" id="0">
        <title ... />
        <color ... />
        <borderset name="bsWindow"> ... </borderset>
        <borderset name="bsButton"> ... </borderset>
        <borderset name="bsListboxEntry"> ... </borderset>
        <label ... />
        <listbox ... />
        <scrolllabel ... />
        <slider ... />
        <stringList ... />
        <configList ... />
    </windowstyle>

    <!-- Optional: second style for LCD/display (id="1") -->
    <windowstyle type="skinned" id="1">
        ...
    </windowstyle>

    <!-- Optional: screen-edge margins -->
    <margin id="0" left="0" top="0" right="0" bottom="0" />

    <!-- Optional: subtitle fonts (usually in a separate skin_subtitles.xml) -->
    <subtitles>
        <sub name="Subtitle_Regular" ... />
    </subtitles>
</skin>
```

| Attribute on `<windowstyle>` | Description                                         |
| ----------------------------- | --------------------------------------------------- |
| `type="skinned"`              | Required; the only supported type                   |
| `id="0"`                      | Screen ID: `0` = main TV screen, `1` = LCD/display  |

---

## `<title>` — window title bar

Configures the font and position of the title text rendered in the top border of each window.

```xml
<title font="Regular;26" offset="15,5" />
```

| Attribute | Example        | Description                                      |
| --------- | -------------- | ------------------------------------------------ |
| `font`    | `Regular;26`   | Font used for the window title text              |
| `offset`  | `15,5`         | x,y offset of the title text within the title bar |

> The height of the title bar is determined by the `bpTop` pixmap in `bsWindow`.  
> If no border pixmaps are set, the title bar height is effectively zero.

---

## `<color>` — system colors

These colors set the default background and foreground for all widgets that do not have explicit colors set in the screen XML.

```xml
<color name="Background"                           color="#00111111" />
<color name="Foreground"                           color="#00FFFFFF" />
<color name="ListboxBackground"                    color="#00111111" />
<color name="ListboxForeground"                    color="#00DDDDDD" />
<color name="ListboxSelectedBackground"            color="#00224466" />
<color name="ListboxSelectedForeground"            color="#00FFFFFF" />
<color name="ListboxMarkedBackground"              color="#001F771F" />
<color name="ListboxMarkedForeground"              color="#00FFFFFF" />
<color name="ListboxMarkedAndSelectedBackground"   color="#0018188B" />
<color name="ListboxMarkedAndSelectedForeground"   color="#00FFFFFF" />
<color name="WindowTitleForeground"                color="#00FFFFFF" />
<color name="WindowTitleBackground"                color="#00000000" />
<color name="ScrollbarForeground"                  color="#004488FF" />
<color name="ScrollbarBackground"                  color="#00222222" />
<color name="ScrollbarBorder"                      color="#00444444" />
<color name="SliderForeground"                     color="#004488FF" />
<color name="SliderBackground"                     color="#00222222" />
<color name="SliderBorder"                         color="#00444444" />
```

| `name`                                   | Applies to                                               |
| ---------------------------------------- | -------------------------------------------------------- |
| `Background`                             | Default window / widget background                       |
| `Foreground` / `LabelForeground`         | Default text color (both are aliases)                    |
| `ListboxBackground`                      | Listbox normal row background                            |
| `ListboxForeground`                      | Listbox normal row text color                            |
| `ListboxSelectedBackground`              | Listbox selected row background                          |
| `ListboxSelectedForeground`              | Listbox selected row text color                          |
| `ListboxMarkedBackground`                | Listbox marked (bookmarked) row background               |
| `ListboxMarkedForeground`                | Listbox marked row text color                            |
| `ListboxMarkedAndSelectedBackground`     | Listbox row that is both marked and selected             |
| `ListboxMarkedAndSelectedForeground`     | Same, text color                                         |
| `WindowTitleForeground`                  | Title text color                                         |
| `WindowTitleBackground`                  | Title area background (if no border pixmap)              |
| `ScrollbarForeground`                    | Scrollbar slider fill color                              |
| `ScrollbarBackground`                    | Scrollbar track background                               |
| `ScrollbarBorder`                        | Scrollbar slider border color                            |
| `SliderForeground`                       | Progress slider fill color                               |
| `SliderBackground`                       | Progress slider track background                         |
| `SliderBorder`                           | Progress slider border color                             |

> The `color` attribute on `<color>` can be either a hex value (`#AARRGGBB`) or a named color defined in `<colors>`.

---

## `<borderset>` — border images

Borders are built from up to 9 tiled or stretched pixmaps that together form the window frame.  
Three border sets are available:

| `name`           | Used for                            |
| ---------------- | ----------------------------------- |
| `bsWindow`       | All dialog and screen windows       |
| `bsButton`       | Button widget borders               |
| `bsListboxEntry` | Individual listbox row borders      |

Each `<borderset>` contains `<pixmap>` entries with a `pos` and `filename`:

```xml
<borderset name="bsWindow">
    <pixmap pos="bpTopLeft"     filename="skin/border/corner_tl.png" />
    <pixmap pos="bpTop"         filename="skin/border/top_50px.png"  />
    <pixmap pos="bpTopRight"    filename="skin/border/corner_tr.png" />
    <pixmap pos="bpLeft"        filename="skin/border/left_5px.png"  />
    <pixmap pos="bpBackground"  filename="skin/border/bg.png"        />
    <pixmap pos="bpRight"       filename="skin/border/right_5px.png" />
    <pixmap pos="bpBottomLeft"  filename="skin/border/corner_bl.png" />
    <pixmap pos="bpBottom"      filename="skin/border/bottom_5px.png"/>
    <pixmap pos="bpBottomRight" filename="skin/border/corner_br.png" />
</borderset>
```

| `pos`            | Position in the frame                              |
| ---------------- | -------------------------------------------------- |
| `bpTopLeft`      | Top-left corner                                    |
| `bpTop`          | Top edge (stretched horizontally); height = title bar height |
| `bpTopRight`     | Top-right corner                                   |
| `bpLeft`         | Left edge (stretched vertically)                   |
| `bpBackground`   | Window background (tiled or stretched)             |
| `bpRight`        | Right edge (stretched vertically)                  |
| `bpBottomLeft`   | Bottom-left corner                                 |
| `bpBottom`       | Bottom edge (stretched horizontally)               |
| `bpBottomRight`  | Bottom-right corner                                |

> The height of `bpTop` determines the title bar height.  
> The widths/heights of the edge pixmaps determine the border insets (margin) for the window content.  
> Omitted positions are simply not drawn.

For a title-only border (top bar, thin sides):

```xml
<borderset name="bsWindow">
    <pixmap pos="bpTop"    filename="skin/border/titlebar_50px.png" />
    <pixmap pos="bpLeft"   filename="skin/border/side_5px.png"      />
    <pixmap pos="bpRight"  filename="skin/border/side_5px.png"      />
    <pixmap pos="bpBottom" filename="skin/border/bottom_5px.png"    />
</borderset>
```

For a borderless style (no frame at all — use with `flags="wfNoBorder"` on screens):

```xml
<borderset name="bsWindow">
    <!-- No pixmaps — window has no chrome -->
</borderset>
```

---

## `<label>` — default eLabel font

Sets the font used for all `eLabel` widgets that don't specify their own `font` attribute.

```xml
<label font="Regular;22" />
```

---

## `<listbox>` — default listbox scrollbar settings

Overrides the compiled-in defaults for all listbox scrollbars and alignment.

```xml
<listbox
    font="Regular;22"
    scrollbarWidth="8"
    scrollbarBorderWidth="1"
    scrollbarOffset="4"
    scrollbarMode="showOnDemand"
    scrollbarScroll="byPage"
    scrollbarRadius="4"
    enableWrapAround="1"
    horizontalAlignment="left"
    verticalAlignment="center"
/>
```

| Attribute            | Default        | Description                                             |
| -------------------- | -------------- | ------------------------------------------------------- |
| `font`               | `Regular;20`   | Default font for string-list items                      |
| `scrollbarWidth`     | `10`           | Scrollbar width in pixels                               |
| `scrollbarBorderWidth`| `0`           | Scrollbar slider border width                           |
| `scrollbarOffset`    | `0`            | Gap between list content and scrollbar                  |
| `scrollbarMode`      | `showOnDemand` | `showOnDemand`, `showAlways`, `showNever`, `showLeftOnDemand`, `showLeftAlways` |
| `scrollbarScroll`    | `byPage`       | `byPage` or `byLine`                                    |
| `scrollbarRadius`    | `0`            | Corner radius of the scrollbar slider                   |
| `enableWrapAround`   | `0`            | `1` = wrap from last to first item                      |
| `horizontalAlignment`| `left`         | Default item text alignment                             |
| `verticalAlignment`  | `center`       | Default item vertical text alignment                    |

---

## `<scrolllabel>` — default ScrollLabel / scroll text settings

Controls the scrollbar behavior of multi-line scrollable labels (e.g. EPG description).  
Same scrollbar attributes as `<listbox>`, but affects `ScrollLabel` widgets.

```xml
<scrolllabel
    scrollbarWidth="8"
    scrollbarBorderWidth="1"
    scrollbarOffset="4"
    scrollbarMode="showOnDemand"
    scrollbarScroll="byLine"
    scrollbarRadius="4"
/>
```

---

## `<slider>` — default slider border

Sets the default border width for all `eSlider` (progress bar) widgets.

```xml
<slider borderWidth="1" />
```

---

## `<stringList>` — default string list padding

Sets the default inner text padding for all string list items.

```xml
<stringList textPadding="6,0,6,0" />
```

`textPadding` format: `left,top,right,bottom` in pixels.

---

## `<configList>` — config list defaults

Controls the font and indentation for config list screens (setup screens).

```xml
<configList
    entryFont="Regular;22"
    valueFont="Regular;20"
    headerFont="Regular;22"
    entryLeftOffset="15"
    headerLeftOffset="5"
    indentSize="20"
/>
```

| Attribute          | Default      | Description                                              |
| ------------------ | ------------ | -------------------------------------------------------- |
| `entryFont`        | `Regular;20` | Font for config entry labels                             |
| `valueFont`        | `Regular;18` | Font for config entry values (right side)                |
| `headerFont`       | `Regular;20` | Font for section header separators                       |
| `entryLeftOffset`  | `15`         | Left indent for entry rows in pixels                     |
| `headerLeftOffset` | `15`         | Left indent for header rows in pixels                    |
| `indentSize`       | `20`         | Additional indent per nesting level in pixels            |

---

## `<margin>` — screen edge margins (top-level, not inside `<windowstyle>`)

Reserves pixels at the screen edges, e.g. for overscan compensation.  
This element is at the root level of `<skin>`, not inside `<windowstyle>`.

```xml
<margin id="0" left="0" top="0" right="0" bottom="0" />
```

| Attribute | Description                                          |
| --------- | ---------------------------------------------------- |
| `id`      | Screen ID (`0` = main screen, `1` = LCD)             |
| `left`    | Reserved pixels on the left edge                     |
| `top`     | Reserved pixels at the top edge                      |
| `right`   | Reserved pixels on the right edge                    |
| `bottom`  | Reserved pixels at the bottom edge                   |

---

## `<subtitles>` — subtitle font styles (top-level)

Defines fonts and colors for each subtitle rendering style.  
Usually placed in a separate `skin_subtitles.xml` file, but can also appear in the main skin.

```xml
<subtitles>
    <sub name="Subtitle_TTX"     font="Subs;34"  borderColor="#000000" borderWidth="3" />
    <sub name="Subtitle_Regular" font="Subs;34"  foregroundColor="#ffffff" borderColor="#000000" borderWidth="3" />
    <sub name="Subtitle_Bold"    font="Subsb;34" foregroundColor="#ffffff" borderColor="#000000" borderWidth="3" />
    <sub name="Subtitle_Italic"  font="Subsi;34" foregroundColor="#ffffff" borderColor="#000000" borderWidth="3" />
    <sub name="Subtitle_MAX"     font="Subsz;34" foregroundColor="#ffffff" borderColor="#000000" borderWidth="3" />
</subtitles>
```

| `name`              | Style                                       |
| ------------------- | ------------------------------------------- |
| `Subtitle_TTX`      | Teletext subtitles (color from broadcast)   |
| `Subtitle_Regular`  | DVB normal subtitles                        |
| `Subtitle_Bold`     | DVB bold subtitles                          |
| `Subtitle_Italic`   | DVB italic subtitles                        |
| `Subtitle_MAX`      | DVB bold+italic subtitles                   |

| Attribute         | Description                                          |
| ----------------- | ---------------------------------------------------- |
| `font`            | Font face and size                                   |
| `foregroundColor` | Text color (omit for TTX to use broadcast colors)    |
| `borderColor`     | Shadow/outline color                                 |
| `borderWidth`     | Shadow/outline width in pixels (default: `3`)        |

---

## Complete minimal example

```xml
<skin>
    <colors>
        <color name="background"        value="#00111111" />
        <color name="foreground"        value="#00DDDDDD" />
        <color name="selectionBG"       value="#00224466" />
        <color name="selectionFG"       value="#00FFFFFF" />
        <color name="scrollbarColor"    value="#004488FF" />
        <color name="scrollbarBorder"   value="#00333333" />
        <color name="titleFG"           value="#00FFFFFF" />
        <color name="titleBG"           value="#00000000" />
    </colors>

    <fonts>
        <font filename="fonts/OpenSans-Regular.ttf" name="Regular"  scale="100" />
        <font filename="fonts/OpenSans-Bold.ttf"    name="Bold"     scale="100" />
    </fonts>

    <windowstyle type="skinned" id="0">
        <!-- Title bar -->
        <title font="Regular;24" offset="15,5" />

        <!-- System colors -->
        <color name="Background"                         color="background"     />
        <color name="Foreground"                         color="foreground"     />
        <color name="ListboxBackground"                  color="background"     />
        <color name="ListboxForeground"                  color="foreground"     />
        <color name="ListboxSelectedBackground"          color="selectionBG"    />
        <color name="ListboxSelectedForeground"          color="selectionFG"    />
        <color name="ListboxMarkedBackground"            color="#001F771F"      />
        <color name="ListboxMarkedForeground"            color="foreground"     />
        <color name="ListboxMarkedAndSelectedBackground" color="#0018188B"      />
        <color name="ListboxMarkedAndSelectedForeground" color="foreground"     />
        <color name="WindowTitleForeground"              color="titleFG"        />
        <color name="WindowTitleBackground"              color="titleBG"        />
        <color name="ScrollbarForeground"                color="scrollbarColor" />
        <color name="ScrollbarBorder"                    color="scrollbarBorder"/>
        <color name="SliderForeground"                   color="scrollbarColor" />
        <color name="SliderBorder"                       color="scrollbarBorder"/>

        <!-- Window border: top bar + thin sides -->
        <borderset name="bsWindow">
            <pixmap pos="bpTop"    filename="skin/border/titlebar_48px.png" />
            <pixmap pos="bpLeft"   filename="skin/border/side_4px.png"      />
            <pixmap pos="bpRight"  filename="skin/border/side_4px.png"      />
            <pixmap pos="bpBottom" filename="skin/border/bottom_4px.png"    />
        </borderset>

        <!-- Listbox entry borders (optional separator lines) -->
        <borderset name="bsListboxEntry">
            <pixmap pos="bpBottom" filename="skin/border/separator_1px.png" />
        </borderset>

        <!-- Default fonts -->
        <label font="Regular;22" />

        <!-- Listbox scrollbar defaults -->
        <listbox
            font="Regular;22"
            scrollbarWidth="8"
            scrollbarBorderWidth="1"
            scrollbarOffset="4"
            scrollbarMode="showOnDemand"
            scrollbarRadius="4"
            enableWrapAround="1"
        />

        <!-- ScrollLabel defaults -->
        <scrolllabel
            scrollbarWidth="8"
            scrollbarBorderWidth="1"
            scrollbarOffset="4"
            scrollbarMode="showOnDemand"
            scrollbarScroll="byLine"
        />

        <!-- Config list fonts and indentation -->
        <configList
            entryFont="Regular;22"
            valueFont="Regular;20"
            headerFont="Bold;22"
            entryLeftOffset="15"
            headerLeftOffset="5"
        />
    </windowstyle>

    <!-- Screen edge reservation for overscan (optional) -->
    <margin id="0" left="0" top="0" right="0" bottom="0" />
</skin>
```

---

## Tips

- **Border pixmap sizing**: the pixel dimensions of the border images determine the window insets. A `bpTop` image 48 px tall creates a 48 px title bar; `bpLeft` 5 px wide creates 5 px left padding for the window content.
- **Named colors**: the `color` attribute on `<color>` elements accepts both `#AARRGGBB` literals and names defined in `<colors>`. Using named colors makes the whole style easy to recolor from one place.
- **`id="1"`**: define a second `<windowstyle id="1">` for the LCD/display screen with smaller fonts and simpler borders.
- **`bsListboxEntry`**: often left empty (no pixmaps) for a clean look, or given a single `bpBottom` separator line to divide rows.
- **`bsButton`**: used by the built-in button rendering; less relevant if all buttons are drawn as plain `eLabel` widgets in the screen skin.
