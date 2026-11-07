# Enigma2 Skin Samples

Practical examples for commonly used skin elements.  
Each example shows typical attribute combinations with a short explanation.

---

## eLabel

An `eLabel` is a display element for static text. There are two variants:

- **Named widget** — binds the label to a Python component in the screen code
- **Inline (eLabel tag)** — purely decorative, no Python counterpart needed

---

### Named widget

The label is defined in Python as `self["myLabel"] = Label("Hello")`.  
In the skin it is bound via `name="myLabel"`.

```xml
<widget name="myLabel"
    position="50,100"
    size="400,40"
    font="Regular;28"
    foregroundColor="#00FFFFFF"
    horizontalAlignment="center"
    verticalAlignment="center"
    transparent="1"
/>
```

| Attribute             | Value           | Description                                         |
| --------------------- | --------------- | --------------------------------------------------- |
| `name`                | `myLabel`       | Binds widget to Python component                    |
| `position`            | `50,100`        | Position in pixels: x,y                             |
| `size`                | `400,40`        | Width,height in pixels                              |
| `font`                | `Regular;28`    | Font face and size                                  |
| `foregroundColor`     | `#00FFFFFF`     | Text color (AARRGGBB)                               |
| `horizontalAlignment` | `center`        | Horizontal alignment (`left`, `center`, `right`, `block`) |
| `verticalAlignment`   | `center`        | Vertical alignment (`top`, `center`, `bottom`)      |
| `transparent`         | `1`             | Transparent background                              |

---

### Inline (eLabel tag)

No Python counterpart. Defined directly in the skin, e.g. for captions, dividers or decorative text.

```xml
<eLabel
    text="Settings"
    position="50,20"
    size="300,36"
    font="Regular;24"
    foregroundColor="#00AAAAAA"
    horizontalAlignment="left"
    verticalAlignment="center"
    transparent="1"
/>
```

#### With background color and rounded corners

```xml
<eLabel
    text="NEW"
    position="10,10"
    size="80,30"
    font="Regular;18"
    foregroundColor="#00FFFFFF"
    backgroundColor="#00CC0000"
    cornerRadius="8"
    horizontalAlignment="center"
    verticalAlignment="center"
/>
```

#### With gradient background (used as a divider line)

```xml
<eLabel
    position="0,460"
    size="1280,4"
    backgroundColor="#00444444,#00FFFFFF,#00444444,horizontal"
/>
```

> No `text` needed — the label acts as a divider line with a gradient fill.

#### With text shadow

```xml
<eLabel
    text="Title"
    position="50,50"
    size="400,50"
    font="Bold;32"
    foregroundColor="#00FFFFFF"
    shadowColor="#00000000"
    shadowOffset="2,2"
    transparent="1"
/>
```

#### With text wrap and padding

```xml
<eLabel
    text="This text is longer and will be wrapped automatically."
    position="20,100"
    size="300,120"
    font="Regular;22"
    foregroundColor="#00CCCCCC"
    wrap="wrap"
    padding="8,6,8,6"
    transparent="1"
/>
```

| Attribute      | Value            | Description                                                    |
| -------------- | ---------------- | -------------------------------------------------------------- |
| `text`         | Any text         | Text to display (translated via `_()` if active)              |
| `wrap`         | `wrap`           | Line wrap for long text (`noWrap`, `wrap`, `ellipsis`)        |
| `padding`      | `8,6,8,6`        | Inner spacing: left,top,right,bottom                           |
| `shadowColor`  | `#00000000`      | Color of the text shadow                                       |
| `shadowOffset` | `2,2`            | Shadow offset: x,y                                             |
| `cornerRadius` | `8`              | Round all four corners                                         |

#### With widget border

Draws a border around the entire widget box.

```xml
<eLabel
    text="Bordered Box"
    position="20,150"
    size="300,50"
    font="Regular;24"
    foregroundColor="#00FFFFFF"
    backgroundColor="#00222222"
    borderColor="#00888888"
    borderWidth="2"
    cornerRadius="6"
    horizontalAlignment="center"
    verticalAlignment="center"
/>
```

| Attribute       | Value       | Description                                      |
| --------------- | ----------- | ------------------------------------------------ |
| `borderColor`   | `#00888888` | Color of the widget border                       |
| `borderWidth`   | `2`         | Width of the widget border in pixels             |
| `cornerRadius`  | `6`         | Round all corners by 6 pixels                    |

**Rounding specific corners only:**

```xml
<eLabel
    position="20,210"
    size="300,50"
    backgroundColor="#00333333"
    borderColor="#00AAAAAA"
    borderWidth="1"
    cornerRadius="12;topLeft,topRight"
/>
```

Available corner names: `topLeft`, `topRight`, `bottomLeft`, `bottomRight`, `top` (both top), `bottom` (both bottom), `left` (both left), `right` (both right).

#### With widget border (widgetBorderColor / widgetBorderWidth)

`widgetBorderColor` and `widgetBorderWidth` draw a border *inside* the widget boundary, independent of `borderColor`.

```xml
<eLabel
    text="Inner border"
    position="20,270"
    size="300,50"
    font="Regular;22"
    foregroundColor="#00FFFFFF"
    backgroundColor="#00111111"
    widgetBorderColor="#004488FF"
    widgetBorderWidth="2"
    cornerRadius="8"
    horizontalAlignment="center"
    verticalAlignment="center"
/>
```

#### With text border (outline effect)

`textBorderColor` and `textBorderWidth` draw an outline directly around each character.

```xml
<eLabel
    text="Outlined Text"
    position="20,330"
    size="400,50"
    font="Bold;32"
    foregroundColor="#00FFFFFF"
    textBorderColor="#00000000"
    textBorderWidth="2"
    transparent="1"
/>
```

| Attribute         | Value       | Description                                      |
| ----------------- | ----------- | ------------------------------------------------ |
| `textBorderColor` | `#00000000` | Color of the per-character text outline          |
| `textBorderWidth` | `2`         | Width of the text outline in pixels              |

#### With scrolling text

Scrolls long text that doesn't fit in the widget horizontally.

```xml
<eLabel
    text="This is a very long scrolling ticker text that moves from right to left."
    position="20,200"
    size="400,36"
    font="Regular;24"
    foregroundColor="#00FFFFFF"
    scrollText="direction=left,stepDelay=80,startDelay=1000,endDelay=2000,stepSize=2,mode=cached"
    transparent="1"
/>
```

| Key          | Value    | Description                                                      |
| ------------ | -------- | ---------------------------------------------------------------- |
| `direction`  | `left`   | Scroll direction: `left`, `right`, `top`, `bottom`              |
| `stepDelay`  | `80`     | Milliseconds between each step (lower = faster)                  |
| `startDelay` | `1000`   | Delay in ms before scrolling starts                              |
| `endDelay`   | `2000`   | Pause in ms when the end is reached before restarting           |
| `stepSize`   | `2`      | Pixels moved per step                                            |
| `mode`       | `cached` | Scroll mode: `cached`, `bounce`, `bounceCached`, `roll`         |

**Bounce mode** — scrolls back and forth instead of looping:

```xml
<eLabel
    text="Channel name that is too long"
    position="20,200"
    size="300,36"
    font="Regular;24"
    foregroundColor="#00FFFFFF"
    scrollText="direction=left,stepDelay=60,startDelay=500,endDelay=1500,stepSize=2,mode=bounce"
    transparent="1"
/>
```

#### With font scale

`fontScale` shrinks the font — starting from the size given in `font` — only as far as needed so the text fits inside the widget, and never below a floor size `N`. If the text already fits, the original `font` size is used unchanged.

`N` can be given as:

- a **positive** number — an absolute minimum point size (or point width) to shrink down to
- a **negative** number — a floor *relative to* the `font` size, i.e. the font may shrink by at most `|N|` points (floor = original size − |N|)
- omitted (just `fontScale="size"`) — defaults to `-4`, i.e. shrink by at most 4 points

**Scale by height** — font shrinks (down to a floor of 16pt) so the text fits the label's width/height:

```xml
<eLabel
    text="Scaled Text"
    position="20,250"
    size="400,50"
    font="Regular;24"
    fontScale="size;16"
    foregroundColor="#00FFFFFF"
    transparent="1"
/>
```

**Scale by height, relative floor** — font shrinks by at most 4pt below the `font` size (won't go below 20pt here):

```xml
<eLabel
    text="Scaled Text"
    position="20,250"
    size="400,50"
    font="Regular;24"
    fontScale="size;-4"
    foregroundColor="#00FFFFFF"
    transparent="1"
/>
```

**Scale by character width** — font's `pointWidth` shrinks (down to a floor of 14) so a line that is too wide (but whose height still fits) is condensed instead of wrapped/clipped:

```xml
<eLabel
    text="00:00"
    position="20,310"
    size="200,50"
    font="Regular;24"
    fontScale="width;14"
    foregroundColor="#00FFFFFF"
    transparent="1"
/>
```

**Force a fixed rendered size regardless of container** — using a tiny base `font` size (e.g. `;1`) makes the natural fit calculation always undershoot the floor, so the floor `N` effectively becomes the actual rendered size:

```xml
<eLabel
    text="Scaled Text"
    position="20,370"
    size="400,50"
    font="Regular;1"
    fontScale="size;48"
    foregroundColor="#00FFFFFF"
    transparent="1"
/>
```

| Attribute   | Format        | Description                                                                          |
| ----------- | ------------- | ------------------------------------------------------------------------------------- |
| `fontScale` | `size;N`      | Shrink font size as needed to fit, floor at `N` (or `font size − \|N\|` if negative)   |
| `fontScale` | `width;N`     | Shrink font's character width as needed to fit, same floor rules as above             |

> `font` must still be set — its point size is both the starting size and the reference for a negative (relative) `N`.

---

## eRectangle

An `eRectangle` is a purely geometric element — no text, no image.  
It is always inline (no Python counterpart). Use it for backgrounds, dividers, highlights, badges or decorative shapes.

---

### Solid color

```xml
<eRectangle
    position="20,100"
    size="400,4"
    backgroundColor="#00FFFFFF"
/>
```

A 4 px high horizontal divider line.

---

### With border

```xml
<eRectangle
    position="20,120"
    size="300,60"
    backgroundColor="#00222222"
    borderColor="#00888888"
    borderWidth="2"
/>
```

| Attribute       | Value       | Description                           |
| --------------- | ----------- | ------------------------------------- |
| `backgroundColor` | `#00222222` | Fill color (AARRGGBB)               |
| `borderColor`   | `#00888888` | Border color                          |
| `borderWidth`   | `2`         | Border width in pixels                |

---

### With rounded corners

```xml
<eRectangle
    position="20,200"
    size="300,60"
    backgroundColor="#00333399"
    borderColor="#006666FF"
    borderWidth="2"
    cornerRadius="12"
/>
```

**Specific corners only:**

```xml
<!-- Top corners rounded — e.g. a tab header -->
<eRectangle
    position="20,260"
    size="200,40"
    backgroundColor="#00444444"
    cornerRadius="10;topLeft,topRight"
/>

<!-- Bottom corners rounded — e.g. a panel footer -->
<eRectangle
    position="20,300"
    size="200,40"
    backgroundColor="#00444444"
    cornerRadius="10;bottomLeft,bottomRight"
/>
```

Available corner names: `topLeft`, `topRight`, `bottomLeft`, `bottomRight`, `top`, `bottom`, `left`, `right`.

---

### Circle / pill shape

Set `cornerRadius` to half the height (or larger) to get a circle or pill.

```xml
<!-- Circle (size must be square) -->
<eRectangle
    position="20,350"
    size="60,60"
    backgroundColor="#00CC2222"
    cornerRadius="30"
/>

<!-- Pill shape -->
<eRectangle
    position="100,355"
    size="120,50"
    backgroundColor="#002266CC"
    cornerRadius="25"
/>
```

---

### Gradient fill

Two-color gradient (horizontal or vertical):

```xml
<eRectangle
    position="0,440"
    size="1280,80"
    backgroundColor="#FF000000,#00000000,vertical"
/>
```

> Alpha fades from fully opaque (`FF`) to fully transparent (`00`) — useful for a shadow overlay at the bottom of an image.

Three-color gradient with center stop:

```xml
<eRectangle
    position="0,530"
    size="1280,4"
    backgroundColor="#00444444,#00FFFFFF,#00444444,horizontal"
/>
```

| Format                                        | Description                                    |
| --------------------------------------------- | ---------------------------------------------- |
| `start,end,direction`                         | Two-color gradient                             |
| `start,center,end,direction`                  | Three-color gradient with explicit center stop |
| `start,end,direction,1`                       | Gradient with alpha blending enabled           |
| direction: `horizontal` / `vertical`          |                                                |

---

### Transparent overlay (alpha blend)

Use `alphaBlend` to let the rectangle blend correctly with underlying layers that have per-pixel alpha.

```xml
<eRectangle
    position="0,0"
    size="1280,720"
    backgroundColor="#80000000"
    alphaBlend="yes"
/>
```

> A semi-transparent black overlay (`80` = 50% opacity in the AA byte) over the whole screen.

---

### As a layered badge (with zPosition)

```xml
<!-- Background card -->
<eRectangle
    position="20,100"
    size="200,100"
    backgroundColor="#00222222"
    cornerRadius="10"
    zPosition="1"
/>

<!-- Accent bar on the left edge -->
<eRectangle
    position="20,100"
    size="6,100"
    backgroundColor="#004488FF"
    cornerRadius="10;left"
    zPosition="2"
/>
```

| Attribute    | Value | Description                                       |
| ------------ | ----- | ------------------------------------------------- |
| `zPosition`  | `2`   | Layer order — higher value = drawn on top         |
| `alphaBlend` | `yes` | Enable alpha blending for semi-transparent fills  |

---

## ePixmap

An `ePixmap` displays an image file. Two variants:

- **Inline (ePixmap tag)** — image path defined directly in the skin, no Python counterpart needed
- **Named widget** — image is set at runtime from Python code

---

### Inline (ePixmap tag)

#### Basic image with alpha channel

```xml
<ePixmap
    pixmap="icons/plugin.png"
    position="20,100"
    size="40,40"
    alphatest="on"
/>
```

| Attribute   | Value          | Description                                                                 |
| ----------- | -------------- | --------------------------------------------------------------------------- |
| `pixmap`    | path to file   | Image path, relative to the skin directory                                  |
| `alphatest` | `on`           | Use the image's alpha channel for transparency (`on`, `off`, `blend`)      |

**`alphatest` values:**

| Value   | Description                                                                 |
| ------- | --------------------------------------------------------------------------- |
| `off`   | No transparency — image is drawn opaque                                    |
| `on`    | Hard alpha test — pixels are either fully visible or fully transparent     |
| `blend` | Per-pixel alpha blending — smooth transparency edges                       |

---

#### Decorative background image

```xml
<ePixmap
    pixmap="background.png"
    position="0,0"
    size="1280,720"
    alphatest="off"
    zPosition="0"
/>
```

> `alphatest="off"` is appropriate for opaque full-screen backgrounds.

---

#### Scaled image

```xml
<!-- Scale keeping aspect ratio, centered in the widget area -->
<ePixmap
    pixmap="poster.png"
    position="20,100"
    size="185,278"
    alphatest="blend"
    scale="keepAspect"
/>

<!-- Fill the full widget area (may clip the image) -->
<ePixmap
    pixmap="backdrop.jpg"
    position="0,0"
    size="1280,720"
    alphatest="off"
    scale="fill"
/>

<!-- Align top-left, keep aspect ratio -->
<ePixmap
    pixmap="icon.png"
    position="20,20"
    size="100,100"
    alphatest="on"
    scale="leftTop"
/>
```

| `scale` value  | Description                                                               |
| -------------- | ------------------------------------------------------------------------- |
| `none`         | No scaling — image displayed at original size                            |
| `keepAspect`   | Scale to fit inside the widget, keep aspect ratio, centered              |
| `fill`         | Scale to fill the widget completely — one side may be clipped            |
| `stretch`      | Scale to exact widget size — aspect ratio may break                      |
| `center`       | No scaling, centered in the widget                                        |
| `leftTop`      | No scaling or: keep aspect + align top-left                              |
| `width`        | Scale to widget width, height may overflow                               |
| `height`       | Scale to widget height, width may overflow                               |

See `SKINATTRIBUTES.md` → `scale=` for the full list of positioning variants.

---

#### With rounded corners

`cornerRadius` clips the image to a rounded shape.

```xml
<!-- Rounded poster thumbnail -->
<ePixmap
    pixmap="poster.png"
    position="20,100"
    size="120,160"
    alphatest="blend"
    scale="keepAspect"
    cornerRadius="8"
/>

<!-- Round avatar / channel logo -->
<ePixmap
    pixmap="logo.png"
    position="20,20"
    size="60,60"
    alphatest="blend"
    scale="keepAspect"
    cornerRadius="30"
/>
```

---

#### With border

```xml
<ePixmap
    pixmap="poster.png"
    position="20,100"
    size="120,160"
    alphatest="blend"
    scale="keepAspect"
    cornerRadius="8"
    borderColor="#00888888"
    borderWidth="2"
/>
```

---

### Named widget

The image is set at runtime from Python.  
Python: `self["cover"] = Pixmap()`  
In Python code: `self["cover"].instance.setPixmap(myPixmap)`

```xml
<widget name="cover"
    position="20,100"
    size="185,278"
    alphatest="blend"
    scale="keepAspect"
    cornerRadius="8"
/>
```

The skin defines layout and appearance; the actual image is loaded in Python at runtime.

---

#### Named widget filling its parent (using `e` coordinate)

```xml
<widget name="backdrop"
    position="0,0"
    size="e,e"
    alphatest="off"
    scale="fill"
    transparent="0"
    zPosition="1"
/>
```

> `e` means "take the full size of the parent" — width and height are resolved at layout time.

---

## panel

A `panel` is a layout container that arranges its children automatically.  
It has no visual representation of its own — it only controls the positioning of its children.

Three layout modes are available via the `layout` attribute:

| `layout`     | Position keywords for children       | Description                              |
| ------------ | ------------------------------------ | ---------------------------------------- |
| `horizontal` | `left`, `right`, `center`            | Children placed side by side             |
| `vertical`   | `top`, `bottom`, `center`            | Children stacked top to bottom           |
| *(none)*     | absolute `x,y` or `fill`            | Children placed at explicit coordinates  |

---

### Horizontal layout

Children flow from left to right. `left` appends to the left edge, `right` to the right edge, `center` uses the remaining space.

```xml
<panel position="20,120" size="1240,50" layout="horizontal" spacing="10">
    <eLabel position="left"   size="140,40" text="Red"    backgroundColor="#009F1313" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="left"   size="140,40" text="Green"  backgroundColor="#001F771F" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="right"  size="140,40" text="Blue"   backgroundColor="#0018188B" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="center" size="300,40" text="Center" backgroundColor="#00333333" horizontalAlignment="center" verticalAlignment="center" />
</panel>
```

| Attribute  | Value        | Description                                      |
| ---------- | ------------ | ------------------------------------------------ |
| `layout`   | `horizontal` | Children placed left to right                    |
| `spacing`  | `10`         | Gap in pixels between children                   |
| `position` | child        | `left` / `right` anchors to edge; `center` fills remaining space |

---

### Vertical layout

Children flow from top to bottom. `top` appends at the top, `bottom` anchors to the bottom, `center` uses remaining space.

```xml
<panel position="20,180" size="420,120" layout="vertical" spacing="6">
    <eLabel position="top"    size="420,30" text="Header"  backgroundColor="#00335577" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="center" size="420,30" text="Content" backgroundColor="#00446688" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="bottom" size="420,30" text="Footer"  backgroundColor="#00557799" horizontalAlignment="center" verticalAlignment="center" />
</panel>
```

---

### Including a named panel (screen include)

A panel can include another named screen/panel from `domScreens`. The included content is rendered into the given position and size.

```xml
<!-- Define once, reuse anywhere -->
<screen name="_ButtonBar">
    <panel position="0,0" size="e,e" layout="horizontal" spacing="10">
        <eLabel position="left"  size="130,40" text="Red"   backgroundColor="key_red"    foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" />
        <eLabel position="left"  size="130,40" text="Green" backgroundColor="key_green"  foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" />
        <eLabel position="right" size="130,40" text="Blue"  backgroundColor="key_blue"   foregroundColor="key_text" horizontalAlignment="center" verticalAlignment="center" />
    </panel>
</screen>

<!-- Include in another screen -->
<panel position="0,e-40" size="e,40" name="_ButtonBar" />
```

> When `name` is set and no child elements are present, the panel acts as a pure include.  
> If `name` is set **and** child elements exist, the named screen is included first, then children are processed on top.

---

### Absolute layout (no layout mode)

Without `layout`, children use explicit `x,y` coordinates relative to the panel's own origin.

```xml
<panel position="20,200" size="600,300">
    <eRectangle position="0,0"     size="600,300" backgroundColor="#00111111" cornerRadius="10" />
    <eLabel     position="20,20"   size="300,30"  text="Title" font="Regular;22" foregroundColor="#00FFFFFF" transparent="1" />
    <ePixmap    position="20,60"   size="120,160" pixmap="poster.png" alphatest="blend" scale="keepAspect" />
    <eLabel     position="160,60"  size="420,160" text="Description text" font="Regular;20" foregroundColor="#00CCCCCC" wrap="wrap" transparent="1" />
</panel>
```

---

## eStack

`eStack` is similar to `panel` but renders as an actual C++ widget that participates in the widget hierarchy.  
Key difference from `panel`: named widgets inside an `eStack` reflow automatically when sibling widgets are hidden or shown.

Same layout keywords apply: `left`/`right`/`center` for horizontal, `top`/`bottom`/`center` for vertical.

---

### Horizontal eStack

```xml
<eStack position="20,80" size="1240,60" layout="horizontal" spacing="10">
    <eLabel position="left"   size="180,50" text="Left 1"  backgroundColor="#00336699" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="left"   size="220,50" text="Left 2"  backgroundColor="#004466AA" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="center" size="220,50" text="Center"  backgroundColor="#005577BB" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="right"  size="180,50" text="Right"   backgroundColor="#006688CC" horizontalAlignment="center" verticalAlignment="center" />
</eStack>
```

---

### Vertical eStack

```xml
<eStack position="20,160" size="420,200" layout="vertical" spacing="8">
    <eLabel position="top"    size="400,50" text="Top"    backgroundColor="#00337755" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="top"    size="400,50" text="Top 2"  backgroundColor="#00448866" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="center" size="400,50" text="Center" backgroundColor="#00559977" horizontalAlignment="center" verticalAlignment="center" />
    <eLabel position="bottom" size="400,50" text="Bottom" backgroundColor="#0066AA88" horizontalAlignment="center" verticalAlignment="center" />
</eStack>
```

---

### Nested eStacks

A vertical outer stack contains two horizontal inner rows.

```xml
<eStack position="20,380" size="800,220" layout="vertical" spacing="10">
    <eLabel position="top" size="e-20,36" text="Section Header" backgroundColor="#00333333" horizontalAlignment="center" verticalAlignment="center" />

    <!-- Row 1: colored blocks -->
    <eStack position="top" size="e-20,80" layout="horizontal" spacing="12">
        <eRectangle position="left"  size="120,70" backgroundColor="#00993333" cornerRadius="8" />
        <eRectangle position="left"  size="120,70" backgroundColor="#00339933" cornerRadius="8" />
        <eRectangle position="left"  size="120,70" backgroundColor="#00333399" cornerRadius="8" />
        <eRectangle position="right" size="120,70" backgroundColor="#00999933" cornerRadius="8" />
    </eStack>

    <!-- Row 2: label columns -->
    <eStack position="top" size="e-20,80" layout="horizontal" spacing="12">
        <eLabel position="left"   size="220,70" text="Left"   backgroundColor="#004444AA" horizontalAlignment="center" verticalAlignment="center" />
        <eLabel position="center" size="220,70" text="Center" backgroundColor="#005555BB" horizontalAlignment="center" verticalAlignment="center" />
        <eLabel position="right"  size="220,70" text="Right"  backgroundColor="#006666CC" horizontalAlignment="center" verticalAlignment="center" />
    </eStack>
</eStack>
```

---

### eStack with named widgets (dynamic reflow)

Named widgets inside an `eStack` reflow automatically when hidden/shown from Python.

```xml
<eStack position="20,620" size="1240,40" layout="horizontal" spacing="10">
    <widget name="btn_red"    position="left"  size="220,40" backgroundColor="key_red"    foregroundColor="key_text" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" />
    <widget name="btn_green"  position="left"  size="220,40" backgroundColor="key_green"  foregroundColor="key_text" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" />
    <widget name="btn_yellow" position="left"  size="220,40" backgroundColor="key_yellow" foregroundColor="key_text" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" />
    <widget name="btn_blue"   position="right" size="220,40" backgroundColor="key_blue"   foregroundColor="key_text" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" />
</eStack>
```

> When `self["btn_yellow"].hide()` is called from Python, the remaining buttons reflow to fill the gap automatically.

---

## Listbox

A `Listbox` is always a **named widget** bound to a Python list component.  
Two common Python types:
- `self["list"] = List(entries)` — simple string list
- `self["list"] = MenuList(entries)` — menu-style list

In the skin it is bound via `name="list"` (string list / config list) or `render="Listbox"` (source-based renderer).

---

### Basic string list

```xml
<widget name="list"
    position="20,80"
    size="600,500"
    font="Regular;24"
    itemHeight="40"
    backgroundColor="#00111111"
    backgroundColorSelected="#00223366"
    foregroundColor="#00DDDDDD"
    foregroundColorSelected="#00FFFFFF"
    scrollbarMode="showOnDemand"
    scrollbarWidth="6"
    enableWrapAround="1"
    transparent="0"
/>
```

| Attribute                  | Value       | Description                                              |
| -------------------------- | ----------- | -------------------------------------------------------- |
| `font`                     | `Regular;24`| Font for list entries                                    |
| `itemHeight`               | `40`        | Height of each row in pixels                             |
| `backgroundColor`          | `#00111111` | Normal row background                                    |
| `backgroundColorSelected`  | `#00223366` | Selected row background                                  |
| `foregroundColor`          | `#00DDDDDD` | Normal text color                                        |
| `foregroundColorSelected`  | `#00FFFFFF` | Selected text color                                      |
| `scrollbarMode`            | `showOnDemand` | Show scrollbar only when list overflows              |
| `scrollbarWidth`           | `6`         | Scrollbar width in pixels                                |
| `enableWrapAround`         | `1`         | Wrap from last item back to first                        |

---

### With scrollbar styling

```xml
<widget name="list"
    position="20,80"
    size="600,500"
    font="Regular;24"
    itemHeight="40"
    backgroundColor="#00111111"
    backgroundColorSelected="#00223366"
    foregroundColor="#00DDDDDD"
    foregroundColorSelected="#00FFFFFF"
    scrollbarMode="showAlways"
    scrollbarWidth="8"
    scrollbarOffset="4"
    scrollbarBorderWidth="1"
    scrollbarBorderColor="#00444444"
    scrollbarForegroundColor="#004488FF"
    scrollbarBackgroundColor="#00222222"
    scrollbarRadius="4"
/>
```

---

### With item gradients and corner radius

```xml
<widget name="list"
    position="20,80"
    size="600,500"
    font="Regular;24"
    itemHeight="44"
    backgroundColor="#00000000"
    itemGradient="#00222222,#00333333,vertical"
    itemGradientSelected="#00224466,#00336699,vertical"
    itemCornerRadius="8"
    itemCornerRadiusSelected="8"
    foregroundColor="#00CCCCCC"
    foregroundColorSelected="#00FFFFFF"
    scrollbarMode="showOnDemand"
    scrollbarWidth="6"
    transparent="1"
/>
```

| Attribute                  | Description                                              |
| -------------------------- | -------------------------------------------------------- |
| `itemGradient`             | Gradient fill for normal rows                            |
| `itemGradientSelected`     | Gradient fill for the selected row                       |
| `itemCornerRadius`         | Round corners on normal rows                             |
| `itemCornerRadiusSelected` | Round corners on the selected row                        |

---

### Grid layout (e.g. plugin browser)

```xml
<widget source="pluginlist"
    render="Listbox"
    position="20,80"
    size="1240,560"
    listOrientation="grid"
    itemHeight="120"
    itemWidth="190"
    itemSpacing="8,8"
    itemCornerRadius="10"
    itemGradient="#00222233,#00333344,vertical"
    itemGradientSelected="#00224466,#00336699,vertical"
    spacingColor="#00111111"
    scrollbarMode="showOnDemand"
    scrollbarWidth="6"
    transparent="0"
/>
```

| Attribute         | Value      | Description                                              |
| ----------------- | ---------- | -------------------------------------------------------- |
| `listOrientation` | `grid`     | Grid layout (`vertical`, `horizontal`, `grid`)           |
| `itemWidth`       | `190`      | Width of each grid cell                                  |
| `itemSpacing`     | `8,8`      | Gap between cells: x,y in pixels                         |
| `spacingColor`    | `#00111111`| Fill color for the gap between cells                     |

---

### With selection zoom

The selected item is enlarged relative to its neighbors.

```xml
<widget source="mylist"
    render="Listbox"
    position="20,80"
    size="300,500"
    listOrientation="vertical"
    itemHeight="120"
    itemWidth="260"
    selectionZoomSize="280,140,zoomContent"
    itemCornerRadius="10"
    scrollbarMode="showNever"
    transparent="1"
/>
```

| Attribute          | Format                      | Description                                              |
| ------------------ | --------------------------- | -------------------------------------------------------- |
| `selectionZoom`    | `percent[,mode]`            | Zoom factor in percent (e.g. `110`) + optional mode     |
| `selectionZoomSize`| `width,height[,mode]`       | Explicit size for the selected item + optional mode      |
| mode               | `zoomContent` / `moveContent` / `ignoreContent` | How item content scales with the zoom |

---

### scrollText — scroll long item text

`scrollText` applies to the entire widget and affects how overflowing item text is displayed.  
The syntax is identical to `eLabel`'s `scrollText` attribute.

```xml
<widget name="list"
    position="20,80"
    size="600,500"
    font="Regular;24"
    itemHeight="40"
    backgroundColor="#00111111"
    backgroundColorSelected="#00223366"
    scrollbarMode="showOnDemand"
    scrollbarWidth="6"
    scrollText="direction=left,stepDelay=80,startDelay=1000,endDelay=2000,stepSize=2,mode=roll"
/>
```

| `scrollText` option | Example value | Description                                        |
| ------------------- | ------------- | -------------------------------------------------- |
| `direction`         | `left`        | Scroll direction: `left`, `right`, `top`, `bottom` |
| `stepDelay`         | `80`          | Milliseconds between each scroll step              |
| `startDelay`        | `1000`        | Delay in ms before scrolling starts                |
| `endDelay`          | `2000`        | Pause at end before wrapping / reversing           |
| `stepSize`          | `2`           | Pixels per step                                    |
| `mode`              | `roll`        | `roll` (wrap) / `bounce` / `bounceCached`          |
| `repeat`            | `-1`          | Times to repeat; `-1` = loop forever               |

> `scrollText` only scrolls the primary text field of a list item, not individual MultiContent text entries.

---

### fontScale — scale font to fit items

`fontScale` shrinks the font — starting from the size given in `font` — only as far as needed so each item's text fits within the row, and never below a floor `N`. Two modes:

- `size;N` — scale by point size: shrinks the font size, floor at `N`
- `width;N` — scale by character width: shrinks the font's character width (used when a line is too wide but its height still fits), floor at `N`

As with `eLabel`, `N` may be negative to mean "shrink by at most `|N|` points relative to the `font` size" instead of an absolute floor; omitting `N` (`fontScale="size"`) defaults to `-4`.

```xml
<!-- Shrink font size as needed, but never below 22pt -->
<widget name="list"
    position="20,80"
    size="600,500"
    font="Regular;24"
    itemHeight="40"
    backgroundColor="#00111111"
    backgroundColorSelected="#00223366"
    scrollbarMode="showOnDemand"
    scrollbarWidth="6"
    fontScale="size;22"
/>
```

```xml
<!-- Condense character width as needed, but never below 14 -->
<widget name="list"
    position="20,80"
    size="600,500"
    font="Regular;24"
    itemHeight="40"
    backgroundColor="#00111111"
    backgroundColorSelected="#00223366"
    fontScale="width;14"
/>
```

---

### XML-based MultiContent templates

Instead of the old Python-based `MultiContentEntry*` tuples with `TemplatedMultiContent`, you can define item layout directly in the skin XML using `<template>` / `<mode>` / `<text>` / `<pixmap>` / `<rectangle>` / `<progress>`.

The Python side creates a `List` source with `indexNames`:

```python
from Components.Sources.List import List

indexNames = {
    "Name": 0,
    "Description": 1,
    "Icon": 2,
    "Progress": 3,
}
self["mylist"] = List(entries, indexNames=indexNames)
# entries is a list of tuples: (name, description, iconPixmap, progressValue)
```

The skin defines the template inline inside the `<widget>`:

#### Simple text list

```xml
<widget source="mylist" render="Listbox"
    position="20,80" size="750,500"
    scrollbarMode="showOnDemand" scrollbarWidth="6">
    <template name="Default" fonts="Regular;22" itemHeight="40">
        <mode name="default">
            <text index="Name" position="10,0" size="730,40" font="0"
                horizontalAlignment="left" verticalAlignment="center" />
        </mode>
    </template>
</widget>
```

| Attribute on `<template>` | Description                                          |
| ------------------------- | ---------------------------------------------------- |
| `name`                    | Template name; `"Default"` is used unless changed    |
| `fonts`                   | Comma-separated font definitions; `font="0"` = first |
| `itemHeight`              | Row height in pixels                                 |
| `itemWidth`               | Cell width for grid layouts                          |

#### Two-line list with icon

```xml
<widget source="mylist" render="Listbox"
    position="20,80" size="750,500"
    scrollbarMode="showOnDemand" scrollbarWidth="6">
    <template name="Default" fonts="Regular;22,Regular;16" itemHeight="60">
        <mode name="default">
            <!-- Icon on the left -->
            <pixmap index="Icon" position="6,6"  size="48,48"
                alpha="blend" scale="centerScaled" />
            <!-- Title and subtitle on the right -->
            <text index="Name"        position="62,2"  size="674,28" font="0"
                horizontalAlignment="left" verticalAlignment="center" />
            <text index="Description" position="62,32" size="674,22" font="1"
                horizontalAlignment="left" verticalAlignment="center"
                foregroundColor="#00AAAAAA" foregroundColorSelected="#00FFFFFF" />
        </mode>
    </template>
</widget>
```

| Element      | Key attributes                                    |
| ------------ | ------------------------------------------------- |
| `<text>`     | `index`, `position`, `size`, `font`, `horizontalAlignment`, `verticalAlignment`, `wrap`, `foregroundColor`, `foregroundColorSelected`, `backgroundColor`, `cornerRadius`, `padding`, `textBorderColor`, `textBorderWidth` |
| `<pixmap>`   | `index`, `position`, `size`, `alpha` (`blend`/`test`), `scale`, `cornerRadius`, `backgroundColor` |
| `<rectangle>`| `position`, `size`, `backgroundColor`, `backgroundColorSelected`, `borderWidth`, `borderColor`, `cornerRadius`, `foregroundGradient`, `foregroundGradientSelected` |
| `<progress>` | `index`, `position`, `size`, `borderWidth`, `foregroundColor`, `foregroundColorSelected`, `borderColor`, `foregroundGradient` |

#### With background, rectangle, and progress bar

```xml
<widget source="mylist" render="Listbox"
    position="20,80" size="750,500"
    scrollbarMode="showOnDemand" scrollbarWidth="6">
    <template name="Default" fonts="Regular;22,Regular;16" itemHeight="70">
        <mode name="default">
            <!-- Row background -->
            <rectangle position="0,2"   size="750,66"
                backgroundColor="#00222233" backgroundColorSelected="#00224466"
                cornerRadius="8" />
            <!-- Icon -->
            <pixmap index="Icon" position="10,10" size="50,50"
                alpha="blend" scale="centerScaled" cornerRadius="6" />
            <!-- Title -->
            <text index="Name" position="70,4" size="590,28" font="0"
                horizontalAlignment="left" verticalAlignment="center"
                foregroundColor="#00DDDDDD" foregroundColorSelected="#00FFFFFF" />
            <!-- Subtitle -->
            <text index="Description" position="70,34" size="440,22" font="1"
                horizontalAlignment="left" verticalAlignment="center"
                foregroundColor="#00888888" foregroundColorSelected="#00CCCCCC" />
            <!-- Progress bar -->
            <progress index="Progress" position="70,58" size="440,6"
                foregroundColor="#004488FF" foregroundColorSelected="#0066AAFF"
                borderWidth="1" borderColor="#00333333" />
        </mode>
    </template>
</widget>
```

#### Multiple display modes

A template can contain multiple `<mode>` blocks. The active mode is set from Python via `self["mylist"].style = "compact"`.

```xml
<widget source="mylist" render="Listbox"
    position="20,80" size="750,500"
    scrollbarMode="showOnDemand" scrollbarWidth="6">
    <template name="Default" fonts="Regular;22,Regular;16" itemHeight="40">
        <mode name="default">
            <text index="Name" position="10,0" size="730,40" font="0"
                horizontalAlignment="left" verticalAlignment="center" />
        </mode>
        <mode name="compact" itemHeight="28">
            <text index="Name" position="10,0" size="580,28" font="1"
                horizontalAlignment="left" verticalAlignment="center" />
            <text index="Description" position="600,0" size="140,28" font="1"
                horizontalAlignment="right" verticalAlignment="center"
                foregroundColor="#00888888" foregroundColorSelected="#00CCCCCC" />
        </mode>
    </template>
</widget>
```

> `itemHeight` on a `<mode>` overrides the template-level value for that mode.

#### Using `<panel>` inside a mode for layout groups

`<panel>` with `layout` can be used inside a `<mode>` to group elements, exactly like in screen XML:

```xml
<mode name="default">
    <panel position="0,0" size="750,60" layout="horizontal" spacing="8">
        <pixmap index="Icon"        position="left"   size="50,50" alpha="blend" scale="centerScaled" />
        <text   index="Name"        position="left"   size="500,60" font="0" horizontalAlignment="left" verticalAlignment="center" />
        <text   index="Description" position="right"  size="180,60" font="1" horizontalAlignment="right" verticalAlignment="center" />
    </panel>
</mode>
```

---
