# Enigma2 Skin Attribute Dokumentation

## Übersicht

Eine vollständige Dokumentation aller Attribute der AttributeParser-Klasse im Enigma2 GUI-System.
Jedes Attribut wird dokumentiert mit:
- Seinem exakten Namen (Groß-/Kleinschreibung beachten)
- Allen möglichen Werten und Formaten
- Beschreibung der Funktionalität
- Falls veraltet, welches Attribut stattdessen zu verwenden ist
- Verwandte Attribute wo zutreffend

## Attribute

### A

### alphaBlend=
Steuert Alpha-Blending für das Widget
- Werte: Boolean — `yes`/`no`, `true`/`false`, `1`/`0`, `on`/`off`.
- Verhalten: Wenn aktiviert, verwendet die GUI Alpha-Blending für Pixmaps und Hintergründe mit Per-Pixel-Alpha; wenn deaktiviert, ist Alpha-Blending ausgeschaltet.
- Beispiel: `alphaBlend=yes`

#### alphaTest=
Steuert die Alpha-Kanal-Behandlung für Bilder
- Werte:
  - `on`: Alpha-Test verwenden
  - `off`: Kein Alpha
  - `blend`: Alpha-Blending

#### alphatest=
**(Veraltet - nutze alphaTest)**
- Werte: Wie bei alphaTest

#### align=
Legt die Stack-Ausrichtung für Kind-Widgets fest, wenn sie innerhalb eines Stack verwendet werden
- Werte: `left`, `right`, `center` für horizontale Stacks; `top`, `bottom`, `center` für vertikale Stacks. Numerische/interne Enum-Werte werden ebenfalls akzeptiert.
- Hinweis: Wird mit `stack`-Layout oder `eStack`-Widgets verwendet; der Wert wird durch die Skin-Engine in interne Stack-Ausrichtungs-Flags umgewandelt.
- Beispiel: `align=center`

#### animationMode=
Steuert das Animationsverhalten des Widgets
- Werte:
  - `disable`/`off`: Keine Animation (0x00)
  - `offshow`: Animation nur beim Ausblenden (0x10)
  - `offhide`: Animation nur beim Einblenden (0x01)
  - `onshow`: Animation beim Einblenden (0x01)
  - `onhide`: Animation beim Ausblenden (0x10)

#### animationPaused=
Steuert ob die Animation pausiert ist
- Werte: `yes`/`no`, `true`/`false`, `0`/`1`

### B

#### backgroundColor=
Legt die Hintergrundfarbe des Widgets fest
- Einzelfarbe: `#AARRGGBB` oder Farbname
- Farbverlauf: `Startfarbe[,Mittelfarbe],Endfarbe,Richtung[,alphaBlend]`
  - Richtung: `horizontal`, `vertical`
  - AlphaBlend: `1` (an) oder `0` (aus)
- Beispiele:
  - `#00000000`: Schwarz mit 0% Alpha
  - `black,white,horizontal`: Horizontaler Verlauf
  - `#00FF0000,#0000FF00,vertical,1`: Vertikaler Verlauf mit Alpha-Blend

#### backgroundColorEven=
Hintergrundfarbe für gerade Zeilen in Listen
- Werte: `#AARRGGBB` oder Farbname

#### backgroundColorMarked=
Farbe für markierte Elemente
- Werte: `#AARRGGBB` oder Farbname

#### backgroundColorMarkedAndSelected=
Farbe für Elemente die markiert und ausgewählt sind
- Werte: `#AARRGGBB` oder Farbname

#### backgroundColorOdd=
Hintergrundfarbe für ungerade Zeilen in Listen
- Werte: `#AARRGGBB` oder Farbname

#### backgroundColorRows=
**(Veraltet - nutze backgroundColorEven)**
- Werte: Wie bei backgroundColorEven

#### backgroundColorSelected=
Farbe für ausgewählte Elemente
- Werte: Wie bei backgroundColor

#### backgroundGradient=
**(Veraltet - nutze backgroundColor mit Farbverlauf)**
- Werte: Wie backgroundColor Farbverlauf

#### backgroundGradientSelected=
**(Veraltet - nutze backgroundColorSelected mit Farbverlauf)**
- Werte: Wie backgroundColorSelected Farbverlauf

#### backgroundPixmap=
Hintergrundbild
- Werte: Pfad zur Bilddatei

#### base=
Basis-Referenzwert
- Werte: Verschiedene

#### borderColor=
Rahmenfarbe des Widgets
- Werte: `#AARRGGBB` oder Farbname

#### borderWidth=
Rahmenbreite des Widgets
- Werte: Ganzzahl in Pixeln

### C

#### condition=
Bedingung für Widget-Sichtbarkeit
- Werte: config oder BoxInfo

#### conditional=
Bedingung für Widget-Sichtbarkeit
- Werte: Komma-getrennte Bedingungen

#### connection=
Dummy-Attribut, das nur von Addons verwendet wird; wird von der Skin-Engine ignoriert.
- Werte: Beliebiger String

#### cornerRadius=
Radius für abgerundete Ecken
- Werte:
  - Einzelne Zahl für alle Ecken: `10`
  - Spezifische Ecken: `10;topLeft,bottomRight`
  - Verfügbare Ecken: `topLeft`, `topRight`, `bottomLeft`, `bottomRight`, `top`, `bottom`, `left`, `right`
- Beispiel: `cornerRadius=8;top` — rundet nur die beiden oberen Ecken ab

### E

#### enableWrapAround=
Aktiviert Umbruch in Listen
- Werte: `yes`/`no`, `true`/`false`, `0`/`1`

#### entryFont=
Schriftart für Einträge
- Werte: `Schriftname;Größe`
- Beispiel: `Regular;20`

#### excludes=
Auszuschließende Elemente
- Werte: Komma-getrennte Liste

### F

#### flags=
Fenster-Flags
- Werte: Komma-getrennte Liste von Fenster-Flags

#### font=
Hauptschriftart-Einstellungen
- Werte: `Schriftname;Größe`
- Beispiel: `Regular;20`

#### fontScale=
Verkleinert die Schriftart (ausgehend von der `font`-Größe) nur so weit wie nötig, damit der Text in den Widget-Bereich passt, bis maximal zu einer unteren Grenze.
- Format: `Skalierungstyp;Größe`
  - `Skalierungstyp`: `size` (nach Punktgröße skalieren) oder `width` (nach Zeichenbreite skalieren)
  - `Größe`: untere Grenze in Pixeln, bis zu der verkleinert wird (wird mit dem Skin-Auflösungsfaktor skaliert). Positiv = absolute Untergrenze; negativ = relativ zur `font`-Größe (Untergrenze = Font-Größe − |Größe|); weggelassen = Standardwert `-4`
- Beispiel: `fontScale=size;20` (absolute Untergrenze von 20)
- Beispiel: `fontScale=size;-4` (verkleinert um maximal 4 unter die `font`-Größe)

#### foregroundColor=
Text-/Inhaltsfarbe
- Einzelfarbe: `#AARRGGBB` oder Farbname
- Farbverlauf: `Startfarbe[,Mittelfarbe],Endfarbe,Richtung[,alphaBlend]`

#### foregroundColorSelected=
Farbe für ausgewählten Text
- Werte: `#AARRGGBB` oder Farbname

#### foregroundGradient=
**(Veraltet - nutze foregroundColor mit Farbverlauf)**
- Werte: Wie foregroundColor Farbverlauf

### H

#### hAlign=
**(Veraltet - nutze horizontalAlignment)**
- Werte: Wie horizontalAlignment

#### halign=
**(Veraltet - nutze horizontalAlignment)**
- Werte: Wie horizontalAlignment

#### headerFont=
Schriftart für Überschriften
- Werte: `Schriftname;Größe`
- Beispiel: `Regular;20`

#### headerForegroundColor=
Textfarbe für Überschriften
- Werte: `#AARRGGBB` oder Farbname

#### horizontalAlignment=
Horizontale Textausrichtung
- Werte:
  - `left`: Linksbündig
  - `center`: Zentriert
  - `right`: Rechtsbündig
  - `block`: Blocksatz

### I

#### ignoreWidgets=
Liste von Widgets die ignoriert werden sollen
- Werte: Komma-getrennte Liste

#### includes=
Einzuschließende Elemente (Gegenstück zu excludes)
- Werte: Komma-getrennte Liste

#### itemAlignment=
Ausrichtung von Elementen in Listen
- Werte:
  - `default`: Standard-Ausrichtung
  - `center`: Zentriert
  - `justify`: Blocksatz
  - `leftTop`, `leftMiddle`, `leftBottom`
  - `rightTop`, `rightMiddle`, `rightBottom`
  - `centerTop`, `centerMiddle`, `centerBottom`
  - `justifyTop`, `justifyMiddle`, `justifyBottom`
  - `justifyLeft`, `justifyRight`

#### itemCornerRadius=
Eckenradius für normale (nicht ausgewählte) Listeneinträge
- Werte: Wie bei cornerRadius

#### itemCornerRadiusMarked=
Eckenradius für markierte Listeneinträge
- Werte: Wie bei cornerRadius

#### itemCornerRadiusMarkedAndSelected=
Eckenradius für markierte und ausgewählte Listeneinträge
- Werte: Wie bei cornerRadius

#### itemCornerRadiusSelected=
Eckenradius für ausgewählte Listeneinträge
- Werte: Wie bei cornerRadius

#### itemGradient=
Farbverlauf für Listeneinträge
- Werte: Wie bei backgroundGradient

#### itemGradientMarked=
Farbverlauf für markierte Listeneinträge
- Werte: Wie bei backgroundGradient

#### itemGradientMarkedAndSelected=
Farbverlauf für markierte und ausgewählte Listeneinträge
- Werte: Wie bei backgroundGradient

#### itemGradientSelected=
Farbverlauf für ausgewählte Listeneinträge
- Werte: Wie bei backgroundGradient

#### itemHeight=
Höhe der Listeneinträge
- Werte: Ganzzahl in Pixeln

#### itemSpacing=
Abstand zwischen Listenelementen
- Werte: `x,y` in Pixeln

#### itemWidth=
Breite der Listeneinträge
- Werte: Ganzzahl in Pixeln

### L

#### label=
Textbeschriftung
- Werte: Textstring

#### layout=
Steuert wie ein Panel seine Kind-Widgets anordnet.
- Werte: `stack`, `vertical`, `horizontal`.
  - `stack`: Kinder werden übereinandergelegt (überlappend). Das Kind-Attribut `align` steuert die Platzierung innerhalb der Ebene.
  - `vertical`: Kinder werden von oben nach unten angeordnet.
  - `horizontal`: Kinder werden von links nach rechts angeordnet.
- Verwandt: `spacing` (Abstand zwischen Elementen), Kind-Attribute `position` und `size`.
- Beispiel: `<panel layout="horizontal">…</panel>`

#### listOrientation=
Ausrichtung der Liste
- Werte:
  - `vertical`: Vertikal
  - `horizontal`: Horizontal
  - `grid`: Gitter

### N

#### noWrap=
**(Veraltet - nutze wrap)**
- Werte: `yes`/`no`, `true`/`false`, `0`/`1`

### O

#### objectTypes=
Objekttyp-Spezifikationen
- Werte: Verschiedene

#### orientation=
Widget-Ausrichtung (für eSlider)
- Werte:
  - `orHorizontal`/`orLeftToRight`: Horizontal / Links nach Rechts
  - `orVertical`/`orTopToBottom`: Vertikal / Oben nach Unten
  - `orRightToLeft`: Rechts nach Links
  - `orBottomToTop`: Unten nach Oben

#### OverScan=
**(Veraltet - nutze overScan)**
- Werte: Wie bei overScan

#### overScan=
Bildschirm-Overscan Einstellungen
- Werte: Verschiedene

### P

#### padding=
Innerer Abstand
- Werte:
  - Eine Zahl: Alle Seiten
  - Zwei Zahlen: `vertikal,horizontal`
  - Vier Zahlen: `links,oben,rechts,unten`

#### pixmap=
Anzuzeigendes Bild
- Werte: Pfad zur Bilddatei

#### pointer=
Mauszeiger-Einstellungen
- Werte: `name:pos`

#### position=
Widget-Position
- Werte:
  - Koordinaten: `x,y`
  - Schlüsselwörter: `left`, `right`, `top`, `bottom`, `center`
  - Gemischt: `left,100`, `20,center`
  - Spezial: `fill` (füllt den übergeordneten Bereich)

### R

#### resolution=
Bildschirmauflösung
- Werte: `Breite,Höhe`

### S

#### scale=
Bildskaliermodus
- Werte:
  - `none` / `off` / `0`: Keine Skalierung
  - `scale` / `stretch` / `1`: Auf Größe skalieren (Seitenverhältnis kann brechen)
  - `keepAspect` / `on` / `aspect`: Skalieren unter Beibehaltung des Seitenverhältnisses
  - `width`: Auf Widget-Breite skalieren, Höhe kann über-/unterschreiten
  - `height`: Auf Widget-Höhe skalieren, Breite kann über-/unterschreiten
  - `fill`: So skalieren, dass das Widget vollständig gefüllt wird (eine Seite kann abgeschnitten werden)
  - `center`: Zentriert ohne Skalierung
  - Skalieren + Position (Seitenverhältnis beibehalten, innerhalb Widget ausrichten):
    - `leftTop`, `leftCenter` / `leftMiddle`, `leftBottom`
    - `centerTop` / `middleTop`, `centerScaled` / `middleScaled`, `centerBottom` / `middleBottom`
    - `rightTop`, `rightCenter` / `rightMiddle`, `rightBottom`
  - Nur verschieben (keine Skalierung, nur innerhalb Widget ausrichten):
    - `moveLeftTop`, `moveLeftCenter` / `moveLeftMiddle`, `moveLeftBottom`
    - `moveCenterTop` / `moveMiddleTop`, `moveCenter` / `moveMiddle`, `moveCenterBottom` / `moveMiddleBottom`
    - `moveRightTop`, `moveRightCenter` / `moveRightMiddle`, `moveRightBottom`
  - Veraltete scale-Aliasse (bitte nicht-präfixierte Form verwenden):
    - `scaleKeepAspect`, `scaleLeftTop`, `scaleLeftCenter`, `scaleLeftMiddle`, `scaleLeftBottom`
    - `scaleCenterTop`, `scaleMiddleTop`, `scaleCenter`, `scaleMiddle`, `scaleCenterBottom`, `scaleMiddleBottom`
    - `scaleRightTop`, `scaleRightCenter`, `scaleRightMiddle`, `scaleRightBottom`

#### scaleFlags=
**(Veraltet - nutze scale)**
- Werte: Wie bei scale
- Hinweis: Temporärer Kompatibilitäts-Alias; in neuen Skins `scale` verwenden.

#### scrollbarMode=
Scrollleisten-Verhalten
- Werte:
  - `showOnDemand`: Rechts anzeigen wenn nötig
  - `showAlways`: Immer rechts anzeigen
  - `showNever`: Nie anzeigen
  - `showLeft` **(Veraltet - nutze showLeftOnDemand)**: Links anzeigen wenn nötig
  - `showLeftOnDemand`: Links anzeigen wenn nötig
  - `showLeftAlways`: Immer links anzeigen
  - `showTopOnDemand`: Oben anzeigen wenn nötig
  - `showTopAlways`: Immer oben anzeigen

#### scrollbarSliderBorderColor=
**(Veraltet - nutze scrollbarBorderColor)**
- Werte: Wie bei scrollbarBorderColor

#### scrollbarSliderBorderWidth=
**(Veraltet - nutze scrollbarBorderWidth)**
- Werte: Wie bei scrollbarBorderWidth

#### scrollbarSliderForegroundColor=
**(Veraltet - nutze scrollbarForegroundColor)**
- Werte: Wie bei scrollbarForegroundColor

#### scrollbarSliderPicture=
**(Veraltet - nutze scrollbarForegroundPixmap)**
- Werte: Pfad zur Bilddatei

#### scrollbarSliderPixmap=
**(Veraltet - nutze scrollbarForegroundPixmap)**
- Werte: Pfad zur Bilddatei

#### scrollbarWidth=
Breite der Scrollleiste
- Werte: Ganzzahl in Pixeln

#### scrollbarBorderWidth=
Rahmenbreite der Scrollleiste
- Werte: Ganzzahl in Pixeln

#### scrollbarBorderColor=
Rahmenfarbe der Scrollleiste
- Werte: `#AARRGGBB` oder Farbname

#### scrollbarForegroundColor=
Vordergrundfarbe der Scrollleiste
- Werte: `#AARRGGBB` oder Farbname

#### scrollbarBackgroundColor=
Hintergrundfarbe der Scrollleiste
- Werte: `#AARRGGBB` oder Farbname

#### scrollbarBackgroundGradient=
Hintergrund-Farbverlauf der Scrollleiste
- Werte: Wie bei backgroundGradient

#### scrollbarBackgroundPicture=
**(Veraltet - nutze scrollbarBackgroundPixmap)**
- Werte: Pfad zur Bilddatei

#### scrollbarBackgroundPixmap=
Hintergrundbild der Scrollleiste
- Werte: Pfad zur Bilddatei

#### scrollbarbackgroundPixmap=
**(Veraltet - nutze scrollbarBackgroundPixmap)**
- Werte: Pfad zur Bilddatei

#### scrollbarForegroundGradient=
Vordergrund-Farbverlauf der Scrollleiste
- Werte: Wie bei backgroundGradient

#### scrollbarForegroundPixmap=
Vordergrundbild der Scrollleiste
- Werte: Pfad zur Bilddatei

#### scrollbarLength=
Länge der Scrollleiste
- Werte: Ganzzahl oder `auto`

#### scrollbarOffset=
Versatz der Scrollleiste
- Werte: Ganzzahl in Pixeln

#### scrollbarRadius=
Eckenradius der Scrollleiste
- Werte: Wie bei cornerRadius

#### scrollbarScroll=
Scroll-Verhalten der Scrollleiste
- Werte: `byPage`, `byLine`, `byCenter`
- `byPage`: Die Liste scrollt seitenweise.
- `byLine`: Die Liste scrollt zeilenweise.
- `byCenter`: Die Markierung bleibt auf dem mittleren Slot, die Einträge scrollen daran vorbei. Slots vor dem ersten und nach dem letzten Eintrag bleiben leer. Funktioniert bei horizontalen und vertikalen Listen; Grid-Listen und vertikale Listen mit `lockFirstRow` fallen auf `byPage` zurück. Für eine exakte Mitte eine ungerade Anzahl sichtbarer Einträge verwenden; bei gerader Anzahl wird der untere/rechte der beiden mittleren Slots verwendet. Jede Änderung der Auswahl zeichnet die ganze Liste neu.

#### scrollText=
Legt das Scroll-Verhalten für Text-Widgets fest (für langen Text der gescrollt werden muss).
- Format: Komma-getrennte Schlüssel=Wert-Paare.
- Unterstützte Schlüssel und Standardwerte:
  - `direction`: `left`, `right`, `top`, `bottom` (Standard: keine Richtung / scrollNone)
  - `stepDelay`: Ganzzahl Millisekunden zwischen Bewegungsschritten (Standard: `100`)
  - `startDelay`: Anfangsverzögerung in ms vor dem ersten Scrollen (Standard: `0`)
  - `endDelay`: Verzögerung am Ende in ms (Standard: `0`)
  - `repeat`: Anzahl der Wiederholungen (Standard: `0`)
  - `stepSize`: Pixel pro Bewegungsschritt (Standard: `2`)
  - `mode`: Scroll-Modus — `cached`, `bounce`, `bounceCached`, `roll`
- Beispiel: `scrollText=direction=left,stepDelay=120,startDelay=300,repeat=0,stepSize=3,mode=cached`

#### secondFont=
**(Veraltet - nutze valueFont)**
- Werte: Wie bei valueFont

#### secondfont=
**(Veraltet - nutze valueFont)**
- Werte: Wie bei valueFont

#### seek_pointer=
**(Veraltet - nutze seekPointer)**
- Werte: Wie bei seekPointer

#### seekPointer=
Sprung-Zeiger-Einstellungen
- Werte: `name:pos`

#### selection=
Auswahl aktivieren/deaktivieren
- Werte: `0`/`1`

#### selectionDisabled=
**(Veraltet - nutze selection="0")**
- Werte: `0`/`1`

#### selectionPixmap=
Bild für die Auswahl-Markierung
- Werte: Pfad zur Bilddatei

#### selectionZoom=
Zoom-Einstellungen für die Auswahl
- Werte: Ganzzahl Prozent, Zoom-Modus

#### selectionZoomSize=
Größen-Einstellungen für den Auswahl-Zoom
- Werte: `Breite,Höhe,Modus`

#### separatorLineColor=
Farbe der Trennlinie innerhalb von Listenelementen
- Werte: `#AARRGGBB` oder Farbname

#### separatorLineSize=
Position und Größe der Trennlinie innerhalb von Listenelementen
- Format: `Höhe` | `oben,Höhe` | `links,oben,Breite,Höhe`
  - `Höhe`: Linienhöhe; `links`/`oben`/`Breite` sind standardmäßig `-1` (auto/volle Breite)
  - `Breite=-1`: Volle Element-Breite minus Rand
  - `oben=-1`: Vertikal zentriert (Standard)
- Beispiel: `separatorLineSize=1` — 1 Pixel breite, vollbreite, zentrierte Linie

#### shadowColor=
Farbe des Schattens
- Werte: `#AARRGGBB` oder Farbname

#### shadowOffset=
Versatz des Schattens
- Werte: `x,y` Versatz

#### size=
Widget-Abmessungen
- Werte: `Breite,Höhe`

#### spacing=
Pixel-Abstand zwischen Kinder-Widgets in einem `vertical`- oder `horizontal`-Layout.
- Werte: Ganzzahl in Pixeln.
- Beispiel: `spacing=6`

#### spacingColor=
Farbe des Abstands
- Werte: `#AARRGGBB` oder Farbname

#### sliderPixmap=
**(Veraltet - nutze scrollbarForegroundPixmap)**
- Werte: Pfad zur Bilddatei

#### stack=
Beschreibt Stack-Verwendung / das Stack-Widget-Konzept.
- Verwendung: Entweder `layout="stack"` auf einem Panel setzen oder ein `eStack`-Widget verwenden. Kinder werden in Ebenen gezeichnet; das Attribut `align` steuert die Positionierung jedes Kindes innerhalb seiner Ebene.
- Beispiel (Layout): `layout="stack"` — Beispiel (Widget): `<eStack ...>...</eStack>`

### T

#### tabWidth=
Breite der Tabs
- Werte: Ganzzahl oder `auto`

#### tag=
Beliebiger ganzzahliger Tag-Wert der dem Widget zugewiesen wird, zur Verwendung durch Anwendungen/Plugins.
- Werte: Beliebige Ganzzahl.
- Beispiel: `tag=5`
- Verwendungszweck: Anwendungscode kann Widget-Tags lesen, um Widgets zu identifizieren oder kleine Metadaten-Werte zu übergeben.

#### text=
Textinhalt
- Werte: Textstring

#### textBorderColor=
Farbe des Textrandrahmens
- Werte: `#AARRGGBB` oder Farbname

#### textBorderWidth=
Breite des Textrandrahmens
- Werte: Ganzzahl in Pixeln

#### textOffset=
**(Veraltet - nutze padding)**
- Werte: Wie bei padding

#### textPadding=
**(Veraltet - nutze padding)**
- Werte: Wie bei padding

#### title=
Fenstertitel-Text
- Werte: Textstring

#### transparent=
Widget-Hintergrund transparent machen
- Werte: `yes`/`no`, `true`/`false`, `0`/`1`

### U

#### underline=
Text-Unterstreichung aktivieren/deaktivieren
- Werte: `yes`/`no`, `true`/`false`, `0`/`1`

### V

#### vAlign=
**(Veraltet - nutze verticalAlignment)**
- Werte: Wie bei verticalAlignment

#### valign=
**(Veraltet - nutze verticalAlignment)**
- Werte: Wie bei verticalAlignment

#### valueFont=
Schriftart für Werte
- Werte: `Schriftname;Größe`
- Beispiel: `Regular;20`

#### verticalAlignment=
Vertikale Textausrichtung
- Werte:
  - `top`: Oben ausgerichtet
  - `center`/`middle`: Mittig ausgerichtet
  - `bottom`: Unten ausgerichtet

### W

#### widgetBorderColor=
Rahmenfarbe des Widgets
- Werte: `#AARRGGBB` oder Farbname

#### widgetBorderWidth=
Rahmenbreite des Widgets
- Werte: Ganzzahl in Pixeln

#### wrap=
Textumbruch-Verhalten
- Werte:
  - `noWrap`/`off`/`0`: Kein Umbruch
  - `wrap`/`on`/`1`: Text umbrechen
  - `ellipsis`: Mit ... abschneiden

### Z

#### zPosition=
Ebenen-/Schichtordnung
- Werte: Ganzzahl (höher = weiter vorne)
