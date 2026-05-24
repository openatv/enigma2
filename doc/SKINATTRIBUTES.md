# Enigma2 Skin Attributes Documentation

## Overview

A complete documentation of all attributes from the AttributeParser class in Enigma2 GUI system.
Each attribute is documented with:
- Its exact name (case-sensitive)
- All possible values and formats
- Description of functionality
- If deprecated, what to use instead
- Related attributes where applicable

## Attributes

### A

### alphaBlend=
Controls alpha blending for the widget
- Values: boolean-like — `yes`/`no`, `true`/`false`, `1`/`0`, `on`/`off`.
- Behaviour: when enabled the GUI uses alpha blending for pixmaps and backgrounds that contain per-pixel alpha; when disabled alpha blending is off.
- Example: `alphaBlend=yes`

#### alphaTest=
Controls alpha channel handling for images
- Values:
  - `on`: Use alpha test
  - `off`: No alpha
  - `blend`: Alpha blending

#### alphatest=
**(Deprecated - use alphaTest)**
- Values: Same as alphaTest

#### align=
Sets stack alignment for child widgets when used inside a stack (or when the widget is added to a stack)
- Values: `left`, `right`, `center` for horizontal stacks; `top`, `bottom`, `center` for vertical stacks. Numeric/internal enum values may also be accepted.
- Notes: used with `stack` layout or `eStack` widgets; the value is converted to internal stack-alignment flags by the skin engine.
- Example: `align=center`

#### animationMode=
Controls widget animation behavior
- Values:
  - `disable`/`off`: No animation (0x00)
  - `offshow`: Animation on hide only (0x10)
  - `offhide`: Animation on show only (0x01)
  - `onshow`: Animation when shown (0x01)
  - `onhide`: Animation when hidden (0x10)

#### animationPaused=
Controls if animation is paused
- Values: `yes`/`no`, `true`/`false`, `0`/`1`

### B

#### backgroundColor=
Sets widget background color
- Single color: `#AARRGGBB` or named color
- Gradient: `startColor[,centerColor],endColor,direction[,alphaBlend]`
  - Direction: `horizontal`, `vertical`
  - AlphaBlend: `1` (on) or `0` (off)
- Examples:
  - `#00000000`: Black with 0% alpha
  - `black,white,horizontal`: Horizontal gradient
  - `#00FF0000,#0000FF00,vertical,1`: Vertical gradient with alpha blend

#### backgroundColorEven=
Color for even rows in lists
- Values: `#AARRGGBB` or named color

#### backgroundColorMarked=
Color for marked items
- Values: `#AARRGGBB` or named color

#### backgroundColorMarkedAndSelected=
Color when item is both marked and selected
- Values: `#AARRGGBB` or named color

#### backgroundColorOdd=
Color for odd rows in lists
- Values: `#AARRGGBB` or named color

#### backgroundColorRows=
**(Deprecated - use backgroundColorEven)**
- Values: Same as backgroundColorEven

#### backgroundColorSelected=
Color when widget is selected
- Values: Same format as backgroundColor

#### backgroundGradient=
**(Deprecated - use backgroundColor with gradient)**
- Values: Same as backgroundColor gradient format

#### backgroundPixmap=
Background image
- Values: Path to image file

#### base=
Base reference value
- Values: Various

#### borderColor=
Color of widget border
- Values: `#AARRGGBB` or named color

#### borderWidth=
Width of widget border
- Values: Integer pixels

### C

#### condition=
Condition for widget visibility
- Values: config or BoxInfo

#### conditional=
Condition for widget visibility
- Values: Comma-separated conditions

#### cornerRadius=
Radius for rounded corners
- Values: 
  - Single number for all corners: `10`
  - Specific corners: `10;topLeft,bottomRight`
  - Available corners: `topLeft`, `topRight`, `bottomLeft`, `bottomRight`

### E

#### enableWrapAround=
Enable wrapping in lists
- Values: `yes`/`no`, `true`/`false`, `0`/`1`

#### entryFont=
Font for entries
- Values: `fontname;size`
- Example: `Regular;20`

#### excludes=
Elements to exclude
- Values: Comma-separated list

### F

#### flags=
Window flags
- Values: Comma-separated list of window flags

#### font=
Main font settings
- Values: `fontname;size`
- Example: `Regular;20`

#### foregroundColor=
Text/content color
- Single color: `#AARRGGBB` or named color
- Gradient: `startColor[,centerColor],endColor,direction[,alphaBlend]`

#### foregroundColorSelected=
Color for selected text
- Values: `#AARRGGBB` or named color

#### foregroundGradient=
**(Deprecated - use foregroundColor with gradient)**
- Values: Same as foregroundColor gradient

### H

#### hAlign=
**(Deprecated - use horizontalAlignment)**
- Values: Same as horizontalAlignment

#### halign=
**(Deprecated - use horizontalAlignment)**
- Values: Same as horizontalAlignment

#### headerFont=
Font for headers
- Values: `fontname;size`
- Example: `Regular;20`

#### headerForegroundColor=
Color for header text
- Values: `#AARRGGBB` or named color

#### horizontalAlignment=
Text horizontal alignment
- Values:
  - `left`: Left aligned
  - `center`: Centered
  - `right`: Right aligned
  - `block`: Block aligned

### I

#### ignoreWidgets=
List of widgets to ignore
- Values: Comma-separated list

#### includes=
Elements to include
- Values: Comma-separated list

#### itemAlignment=
Alignment of items in lists
- Values:
  - `default`: Default alignment
  - `center`: Centered
  - `justify`: Justified
  - `leftTop`, `leftMiddle`, `leftBottom`
  - `rightTop`, `rightMiddle`, `rightBottom`
  - `centerTop`, `centerMiddle`, `centerBottom`
  - `justifyTop`, `justifyMiddle`, `justifyBottom`
  - `justifyLeft`, `justifyRight`

#### itemCornerRadius=
Corner radius for list items
- Values: Same as cornerRadius

#### itemCornerRadiusMarked=
Corner radius for marked list items
- Values: Same as cornerRadius

#### itemCornerRadiusMarkedAndSelected=
Corner radius for marked and selected list items
- Values: Same as cornerRadius

#### itemCornerRadiusSelected=
Corner radius for selected list items
- Values: Same as cornerRadius

#### itemGradient=
Gradient for list items
- Values: Same as backgroundGradient

#### itemGradientMarked=
Gradient for marked list items
- Values: Same as backgroundGradient

#### itemGradientMarkedAndSelected=
Gradient for marked and selected list items
- Values: Same as backgroundGradient

#### itemGradientSelected=
Gradient for selected list items
- Values: Same as backgroundGradient

#### itemHeight=
Height of items in lists
- Values: Integer pixels

#### itemSpacing=
Space between items
- Values: `x,y` in pixels

#### itemWidth=
Width of items in lists
- Values: Integer pixels

### L

#### label=
Text label content
- Values: Text string

#### layout=
Controls how a panel arranges its child widgets.
- Values: `stack`, `vertical`, `horizontal`.
  - `stack`: children are layered/stacked (overlapping). Per-child `align` controls placement inside the layer.
  - `vertical`: children are laid out top-to-bottom.
  - `horizontal`: children are laid out left-to-right.
- Related: `spacing` (distance between items), per-child `position` and `size` attributes.
- Example: `<panel layout="horizontal">…</panel>`

#### listOrientation=
List display orientation
- Values:
  - `vertical`
  - `horizontal`
  - `grid`

### N

#### noWrap=
**(Deprecated - use wrap)**
- Values: `yes`/`no`, `true`/`false`, `0`/`1`

### O

#### objectTypes=
Object type specifications
- Values: Various

#### orientation=
Widget orientation
- Values:
  - `orHorizontal`/`orLeftToRight`
  - `orVertical`/`orTopToBottom`
  - `orRightToLeft`
  - `orBottomToTop`

#### overScan=
Screen overscan settings
- Values: Various

### P

#### padding=
Inner spacing
- Values:
  - Single number: All sides
  - Two numbers: `vertical,horizontal`
  - Four numbers: `left,top,right,bottom`

#### pixmap=
Image to display
- Values: Path to image file

#### pointer=
Mouse pointer settings
- Values: `name:pos`

#### position=
Widget position
- Values:
  - Coordinates: `x,y`
  - Keywords: `left`, `right`, `top`, `bottom`, `center`
  - Mixed: `left,100`, `20,center`
  - Special: `fill` (fills parent)

### R

#### resolution=
Screen resolution settings
- Values: `width,height`

### S

#### scale=
Image scaling mode
- Values:
  - `none`: No scaling
  - `scale`: Scale to size
  - `keepAspect`: Keep ratio
  - `width`: Scale width
  - `height`: Scale height
  - `stretch`: Stretch to fit
  - `center`: Center without scaling
  - Advanced combinations:
    - `leftTop`, `leftCenter`, `leftBottom`
    - `centerTop`, `centerScaled`, `centerBottom`
    - `rightTop`, `rightCenter`, `rightBottom`

#### scrollbarMode=
Scrollbar behavior
- Values:
  - `showOnDemand`: Show when needed
  - `showAlways`: Always visible
  - `showNever`: Never show
  - `showLeft`: Show on left
  - `showLeftOnDemand`: Show on left when needed

#### scrollbarWidth=
Width of scrollbar
- Values: Integer pixels

#### scrollbarBorderWidth=
Border width of scrollbar
- Values: Integer pixels

#### scrollbarBorderColor=
Border color of scrollbar
- Values: `#AARRGGBB` or named color

#### scrollbarForegroundColor=
Color of scrollbar
- Values: `#AARRGGBB` or named color

#### scrollbarBackgroundColor=
Background color of scrollbar
- Values: `#AARRGGBB` or named color

#### scrollbarBackgroundGradient=
Background gradient of scrollbar
- Values: Same as backgroundGradient

#### scrollbarBackgroundPixmap=
Background image of scrollbar
- Values: Path to image file

#### scrollbarForegroundGradient=
Foreground gradient of scrollbar
- Values: Same as backgroundGradient

#### scrollbarForegroundPixmap=
Foreground image of scrollbar
- Values: Path to image file

#### scrollbarLength=
Length of scrollbar
- Values: Integer or `auto`

#### scrollbarOffset=
Offset of scrollbar
- Values: Integer pixels

#### scrollbarRadius=
Radius of scrollbar corners
- Values: Same as cornerRadius

#### scrollbarScroll=
Scrollbar scroll behavior
- Values: `byPage`, `byLine`

#### scrollText=
Defines scrolling behaviour for text widgets (for long label text that needs to scroll).
- Format: comma-separated key=value pairs.
- Supported keys and defaults:
  - `direction`: `left`, `right`, `top`, `bottom` (default: no direction / scrollNone)
  - `stepDelay`: integer milliseconds between movement steps (default: `100`)
  - `startDelay`: initial delay in ms before the first scroll (default: `0`)
  - `endDelay`: delay at the end in ms (default: `0`)
  - `repeat`: number of times to repeat (default: `0`)
  - `stepSize`: pixels per movement step (default: `2`)
  - `mode`: scrolling mode — `cached`, `bounce`, `bounceCached`, `roll` (maps to internal scroll modes)
- Behaviour: parsed to an internal scroll-config tuple (direction, stepDelay, startDelay, endDelay, repeat, stepSize, mode) used by the widget to control how the text moves.
- Example: `scrollText=direction=left,stepDelay=120,startDelay=300,repeat=0,stepSize=3,mode=cached`

#### secondFont=
**(Deprecated - use valueFont)**
- Values: Same as valueFont

#### secondfont=
**(Deprecated - use valueFont)**
- Values: Same as valueFont

#### seek_pointer=
**(Deprecated - use seekPointer)**
- Values: Same as seekPointer

#### seekPointer=
Seek pointer settings
- Values: `name:pos`

#### selection=
Enable/disable selection
- Values: `0`/`1`

#### selectionDisabled=
**(Deprecated - use selection="0")**
- Values: `0`/`1`

#### selectionPixmap=
Image for selection
- Values: Path to image file

#### selectionZoom=
Zoom settings for selection
- Values: Integer percentage, zoom mode

#### selectionZoomSize=
Size settings for selection zoom
- Values: `width,height,mode`

#### separatorColor=
Color of separator
- Values: `#AARRGGBB` or named color

#### separatorSize=
Size of separator
- Values: Integer pixels

#### shadowColor=
Color of shadows
- Values: `#AARRGGBB` or named color

#### shadowOffset=
Shadow offset position
- Values: `x,y` offset

#### size=
Widget dimensions
- Values: `width,height`

#### spacing=
Pixel spacing used between children in a `vertical` or `horizontal` layout (or within a stack context where spacing applies).
- Values: integer number of pixels.
- Example: `spacing=6`

#### spacingColor=
Color of spacing
- Values: `#AARRGGBB` or named color

#### stack=
Describes stack usage / the stack widget concept.
- Usage: either set `layout="stack"` on a panel or use an `eStack` widget. Children are drawn in layers; the `align` attribute controls how each child is positioned within its layer.
- Example (layout): `layout="stack"`  — Example (widget): `<eStack ...>...</eStack>`

### T

#### tabWidth=
Width of tabs
- Values: Integer or `auto`

#### tag=
Arbitrary integer tag value attached to the widget for application/plugins to use.
- Values: any integer (parsed with the usual integer rules).
- Example: `tag=5`
- Use-case: application code can read widget tags to identify widgets or pass small metadata values.

#### text=
Text content
- Values: Text string

#### textBorderColor=
Color of text border
- Values: `#AARRGGBB` or named color

#### textBorderWidth=
Width of text border
- Values: Integer pixels

#### textOffset=
**(Deprecated - use padding)**
- Values: Same as padding

#### textPadding=
**(Deprecated - use padding)**
- Values: Same as padding

#### title=
Window title text
- Values: Text string

#### transparent=
Make widget background transparent
- Values: `yes`/`no`, `true`/`false`, `0`/`1`

### U

#### underline=
Enable/disable text underlining
- Values: `yes`/`no`, `true`/`false`, `0`/`1`

### V

#### vAlign=
**(Deprecated - use verticalAlignment)**
- Values: Same as verticalAlignment

#### valign=
**(Deprecated - use verticalAlignment)**
- Values: Same as verticalAlignment

#### valueFont=
Font for values
- Values: `fontname;size`
- Example: `Regular;20`

#### verticalAlignment=
Text vertical alignment
- Values:
  - `top`: Top aligned
  - `center`/`middle`: Center aligned
  - `bottom`: Bottom aligned

### W

#### widgetBorderColor=
Color of widget border
- Values: `#AARRGGBB` or named color

#### widgetBorderWidth=
Width of widget border
- Values: Integer pixels

#### wrap=
Text wrapping behavior
- Values:
  - `noWrap`/`off`/`0`: No wrapping
  - `wrap`/`on`/`1`: Break text
  - `ellipsis`: Add ...

### Z

#### zPosition=
Layer/stacking order
- Values: Integer (higher = more front)