# Enigma2 Date And Time

Documentation for OpenATV developers. It describes the current code (`Components/DateTimes.py`, `Screens/DateTime.py`, `Components/Converter/ClockToText.py`) and is based on the original date and time proposal by IanSav (2016).

## Summary

Enigma2 used to have date and time formats hard coded across the code base and the skins. Different coders used different formats, there was no coordination and users had no way to present dates and times in the format they are most comfortable with.

The date and time infrastructure provides a set of pre built date and time formats that are used by the core code, plugins, converters and skins. Users select their preferred style once, in the "Date and Time Settings" screen, and every screen that uses the infrastructure follows that choice.

Typical examples of why this matters: is "11/12" "11 Dec" or "12 Nov"? With the user selectable layout (day-month-year, month-day-year or year-month-day) the same skin shows dates the way each user expects, and coders do not need to know who the user is or where they come from.

## Advisory note

Care should be taken before enabling the time options in a skin, particularly the am/pm and AM/PM formats. The 12 hour formats are wider than the 24 hour formats. Skin and code developers should make sure that their layouts can display all the formats before the options are enabled and exposed to users. A widget that is too narrow trims the end of the text, so the am/pm indicator is the first thing to be lost.

## How it works

| Part | File | Purpose |
|---|---|---|
| Formats and config | `Components/DateTimes.py` | The `DateTimes` class and its singleton `dateTimes`. Creates `config.usage.date` and `config.usage.time`, builds all format strings and provides the `get...()` methods. |
| Initialisation | `Components/UsageConfig.py` | `InitUsageConfig()` calls `dateTimes.initConfig()`. |
| Settings screen | `Screens/DateTime.py`, `data/setup.xml` (key `DateTime`), `data/menu.xml` (key `time_setup`) | The "Date and Time Settings" screen in the System menu. It is also used by the start wizard. |
| Converter | `Components/Converter/ClockToText.py` | Gives skins access to the formats. |
| Skin switch | `skin.py` | `onReload` list. `dateTimes.updateDatesAndTimes()` is registered there so the formats follow a skin change without a restart. |

`dateTimes.updateDatesAndTimes()` rebuilds every format. It runs at start up, after a skin reload, on a locale change and whenever a format option changes. The option notifiers remain active outside the settings screen, including for OpenWebif changes. The screen adds its own preview notifiers and removes only those when it closes.

## Skin parameter

The infrastructure is controlled by the active skin. To enable it a skin author adds a `<parameter>` tag to the `<parameters>` section of the skin:

```xml
<skin>
	<parameters>
		<parameter name="AllowUserDatesAndTimes" value="1,0" />
	</parameters>
</skin>
```

The first number controls the date formats and the second number controls the time formats. A value of `0` disables the feature and a value of `1` enables it. The default, if the parameter is missing, is `0,0`.

| Value | Meaning |
|---|---|
| `0,0` | Default. Fixed legacy formats, no user selection (see "Behavior when disabled"). |
| `1,0` | User selectable dates, fixed 24 hour times. Useful while a skin does not yet have room for the wide 12 hour times. |
| `1,1` | User selectable dates and times. |

`config.usage.date.enabled` and `config.usage.time.enabled` reflect the two values. They are not saved.

The settings screen only shows the date items when the date feature is enabled and the time items when the time feature is enabled. The feature follows the loaded skin: after a skin change the formats and the settings screen adapt without a restart.

### Behavior when disabled

When a part is disabled the formats are fixed and depend only on the language. The user cannot change them.

| Locale | Date | Date without year | Time | Time without seconds |
|---|---|---|---|---|
| `de_DE` | `%d.%m.%Y` | `%d.%m` | `%H:%M:%S` | `%H:%M` |
| `en_AU`, `en_GB` | `%d/%m/%Y` | `%d/%m` | `%H:%M:%S` | `%H:%M` |
| all others | `%m/%d/%Y` | `%m/%d` | `%H:%M:%S` | `%H:%M` |

In this mode there are no day or month names. The date options use the numeric date variants above. `Full` still includes the date without year and the time. `DateShortDayNoMonthNoYear` gives `%a %d`. The date and the time are separated by two spaces in the combined formats. Locale-dependent fallback formats are refreshed when the language changes.

## User settings

The settings are in "Date and Time Settings" (below the time zone and time synchronisation items). The screen shows a preview of the date and time in the footnote while one of the date or time items is selected. Save and Cancel also process options that became hidden, such as the day separator after selecting no day name or the meridiem after selecting a 24 hour clock.

Date items (shown when the skin enables dates):

| Setting | Config | Choices |
|---|---|---|
| Date style | `config.usage.date.layout` | Day Date Month Year, Day Month Date Year, Day Year Month Date |
| Day display style | `config.usage.date.dayFormat` | No day name, abbreviated, full |
| Date display style | `config.usage.date.dateFormat` | `%-d` one digit, `%e` one digit space padded, `%d` two digits |
| Month display style | `config.usage.date.monthFormat` | `%-m`, `%m`, `%b` abbreviated name, `%B` full name |
| Day separator | `config.usage.date.daySeparator` | Shown only if a day name is displayed |
| First separator | `config.usage.date.firstSeparator` | Between the first two date elements |
| Second separator | `config.usage.date.secondSeparator` | Between the second two date elements |
| Suffix character | `config.usage.date.suffix` | None, period or comma appended to the date |
| Time separator | `config.usage.date.timeSeparator` | Between date and time in the combined formats: one space, two spaces or space hyphen space |

Time items (shown when the skin enables times):

| Setting | Config | Choices |
|---|---|---|
| Hour display style | `config.usage.time.hourFormat` | 24 hour (`%-H`, `%k`, `%H`) or 12 hour (`%-I`, `%l`, `%I`) |
| Meridiem (AM/PM) display | `config.usage.time.meridiemFormat` | Only shown for the 12 hour styles. No display, `am/pm` or `AM/PM`. (The am/pm choices are only offered if the locale defines them.) |
| Display seconds | `config.usage.time.secondsFormat` | No or yes |
| Time separator | `config.usage.time.separator` | Between hours, minutes and seconds |

### Layout strings

The formats are built from two layout strings. The placeholders are replaced with the user's choices:

| Placeholder | Replaced with |
|---|---|
| `%A` | Day name format (`dayFormat`) |
| `%d` | Date format (`dateFormat`) |
| `%m` | Month format (`monthFormat`) |
| `+` | Day separator |
| `=` | First separator (date) or time separator (time) |
| `#` | Second separator |
| `%Y` | Year |
| `%H` | Hour format (`hourFormat`) |
| `%S` | Seconds (`secondsFormat`) |
| `%P` | Meridiem (`meridiemFormat`, only for 12 hour styles) |

Date layouts: `%A+%d=%m#%Y`, `%A+%m=%d#%Y` and `%A+%Y=%m#%d`. Time layout: `%H=%M=%S%P`. The variants without day name or year are built from the same strings by removing the `%A+` and year parts.

The date separator options store stable IDs (`space`, `hyphen`, `period`, `periodSpace`, `comma`, `commaSpace`, `colon`, `semicolon`, `slash`). The date/time separator stores `space`, `twoSpaces` or `spacedHyphen`. `DateTimes.SEPARATORS` maps these IDs to display text. This preserves spaces across a settings save/reload, since the settings parser strips whitespace from stored values. Old format preferences are not migrated.

### Defaults

| Locale | Layout | Day sep. | Date | Month | First / second sep. |
|---|---|---|---|---|---|
| `de_DE` | Day Date Month Year | `, ` | `%d` | `%m` | `.` / `.` |
| `en_AU`, `en_GB` | Day Date Month Year | `, ` | `%d` | `%B` | `-` / `-` |
| all others (US style) | Day Month Date Year | ` ` | `%-d` | `%m` | `/` / `/` |

The defaults are read when the configuration is created at start up. The other defaults are: day name full (`%A`), hours `%H`, no meridiem, no seconds, time separator `:`, date and time separated by two spaces.

## ClockToText converter

Skin authors use the existing converter and name the format they want. No special code is needed, the converter adapts the output to the user's choices.

```xml
<convert type="ClockToText">LongFullDate</convert>
```

The examples below are for the skin parameter `1,1`, the default settings of the locale, a 24 hour clock, and the time 16:28:42 on Wednesday 28 October 2026. Day and month names follow the language of the receiver.

| Option | Meaning | `de_DE` | `en_GB` | `en_US` |
|---|---|---|---|---|
| (empty), `Default`, `Display`, `DisplayTime`, `TimeShort` | Hours and minutes with meridiem for 12 hour clocks | `16:28` | `16:28` | `16:28` |
| `TimeShortNoMeridiem` | Hours and minutes, never a meridiem | `16:28` | `16:28` | `16:28` |
| `Time`, `TimeLong` | Hours, minutes, seconds (if enabled) and meridiem | `16:28` | `16:28` | `16:28` |
| `WithSeconds` | Hours, minutes, seconds and meridiem, regardless of the optional seconds setting | `16:28:42` | `16:28:42` | `16:28:42` |
| `TimeNoMeridiem` | As `Time` without meridiem | `16:28` | `16:28` | `16:28` |
| `Mixed`, `TimeMixed` | Time with seconds (if enabled) for 24 hour clocks, hours and minutes with meridiem for 12 hour clocks | `16:28` | `16:28` | `16:28` |
| `Date` | Day name, date, month, year | `Wednesday, 28.10.2026` | `Wednesday, 28-October-2026` | `Wednesday 10/28/2026` |
| `DateNoDay` | No day name | `28.10.2026` | `28-October-2026` | `10/28/2026` |
| `DateNoDayNoYear` | No day name, no year | `28.10` | `28-October` | `10/28` |
| `DateNoDayShortMonth` | No day name, abbreviated month | `28.Oct.2026` | `28-Oct-2026` | `Oct/28/2026` |
| `DateNoDayShortMonthNoYear`, `DisplayDate` | No day name, abbreviated month, no year | `28.Oct` | `28-Oct` | `Oct/28` |
| `DateNoYear`, `LongDate` | Day name, date, month, no year | `Wednesday, 28.10` | `Wednesday, 28-October` | `Wednesday 10/28` |
| `DateShortDay`, `FullDate` | Abbreviated day name | `Wed, 28.10.2026` | `Wed, 28-October-2026` | `Wed 10/28/2026` |
| `DateShortDayNoMonthNoYear` | Abbreviated day name and date only | `Wed, 28` | `Wed, 28` | `Wed 28` |
| `DateShortDayShortMonth`, `ShortFullDate` | Abbreviated day name and month | `Wed, 28.Oct.2026` | `Wed, 28-Oct-2026` | `Wed Oct/28/2026` |
| `Full` | Abbreviated day and month, no year, followed by time without seconds | `Wed, 28.Oct  16:28` | `Wed, 28-Oct  16:28` | `Wed Oct/28  16:28` |
| `DateShortDayShortMonthNoYear`, `DisplayDayDate`, `ShortDate` | Abbreviated day name and month, no year | `Wed, 28.Oct` | `Wed, 28-Oct` | `Wed Oct/28` |
| `DateTime` | `Date`, the date and time separator, then `Time` | `Wednesday, 28.10.2026  16:28` | `Wednesday, 28-October-2026  16:28` | `Wednesday 10/28/2026  16:28` |
| `LongFullDate` | Abbreviated day and month, year and the time without seconds | `Wed, 28.Oct.2026  16:28` | `Wed, 28-Oct-2026  16:28` | `Wed Oct/28/2026  16:28` |

When the "Display seconds" setting is "Yes" the options marked "(if enabled)" show `16:28:42`. With a 12 hour clock and the "am/pm" meridiem they show `4:28pm` (hour format `%-I`) or `04:28pm` (`%I`).

Front panel display options:

| Option | Meaning | `de_DE` | `en_GB` | `en_US` |
|---|---|---|---|---|
| `VFD08` | Time, trimmed to 8 characters | `16:28` | `16:28` | `16:28` |
| `VFD12`, `VFD` | Date and time, trimmed to 12 characters | `28.10 16:28` | `28-10 16:28` | `10/28 16:28` |
| `VFD14` | Date and time, trimmed to 14 characters | `28.10 16:28` | `28-10 16:28` | `10/28 16:28` |
| `VFD18` | Abbreviated day name, date and time, trimmed to 18 characters | `Wed, 28.10 16:28` | `Wed, 28-10 16:28` | `Wed 10/28 16:28` |

The front panel options always show the month as a number, to save space. The date comes before the time. If the text exceeds the character limit, the whole meridiem is dropped first. If necessary, spaces in the date are removed and then only the date is shortened. Hours and minutes remain complete; partial AM/PM suffixes are not shown.

Other options (unchanged by the date and time infrastructure):

| Option | Meaning |
|---|---|
| `AsLength` | A duration in seconds as minutes and seconds (`M:SS`). |
| `AsLengthHours` | A duration in seconds as hours and minutes (`H:MM`). |
| `AsLengthSeconds` | A duration in seconds as hours, minutes and seconds (`H:MM:SS`). |
| `InMinutes` | A duration in seconds as "N Min" or "N Mins". |
| `Timestamp` | The raw timestamp. |
| `Format:<strftime>` | An explicit strftime format, for example `Format:%a %e-%b-%Y  %H:%M`. This bypasses the user's choices. |

An unknown option shows `???`. The OpenViX options `NoSpace` and `Proportional` are accepted and ignored. The former option `VFD11` and the option `DateCompact` no longer exist.

### Parsing and tuples

If the source delivers a tuple of times the converter formats every time of the tuple with its own option and joins the results with a separator (default ` - `). If there are fewer options than times the last option is reused for the remaining times.

| Token | Purpose |
|---|---|
| `Separator<c><string>` | The string put between the formatted times. The character `<c>` directly after `Separator` is skipped and the rest is the separator, for example `Separator: ~ ` gives ` ~ `. |
| `Parse<char>` | Must be first. The character after `Parse` becomes the token separator, for example `Parse|LongFullDate|Default`. |

The default token separators are `;` and `,`. A token list that starts with `Format` is never split at `,`, so a strftime format can contain commas.

Examples:

```xml
<convert type="ClockToText"></convert>                 <!-- "16:28", same as Default -->
<convert type="ClockToText">Default</convert>          <!-- "16:28" -->
<convert type="ClockToText">LongFullDate</convert>     <!-- "Wed, 28-Oct-2026  16:28" (en_GB) -->
<convert type="ClockToText">Default,Default</convert>  <!-- for a tuple: "16:30 - 17:30" -->
<convert type="ClockToText">Separator: ~ ,Default</convert>  <!-- for a tuple: "16:30 ~ 17:30" -->
```

When designing or modifying skins, allow about 50% to 60% more width for each time field than before. If a widget is too narrow the 12 hour times are cut and the AM/PM or am/pm is lost.

## Config variables for Python code

`config.usage.date` and `config.usage.time` contain the user settings (see above). Only five generated format values remain for existing plugins. They are `NoSave` values rebuilt from the new options; old saved format preferences are not migrated.

| Plugin format | Format on `dateTimes` | Content |
|---|---|---|
| `config.usage.date.dayshort` | `dateShortDayShortMonthNoYear` | Abbreviated day and month, no year |
| `config.usage.date.full` | `dateNoDay` | Date, month, year |
| `config.usage.date.short` | `dateNoDayShortMonthNoYear` | Date, abbreviated month |
| `config.usage.time.long` | `time` | Hours, minutes, optional seconds and meridiem |
| `config.usage.time.short` | `timeShort` | Hours, minutes and meridiem |

`config.usage.time.wide` remains a Boolean status flag for `ConfigClock` and plugin layouts that need more room for AM/PM. It is not a format string. Other status values are `config.usage.date.enabled`, `config.usage.time.enabled` and `config.usage.time.meridiemActive`.

Generated formats are stored on `dateTimes` and updated whenever settings, skin or locale change. Internal code uses its formatting methods directly. Controls such as `ConfigDateTime`, which require an unformatted strftime string, use the corresponding `dateTimes` attribute.

Removed config formats:

| Removed | Use instead |
|---|---|
| `config.usage.date.dayfull`, `daylong`, `long`, `dayshortfull`, `shortdayfull`, `daysmall`; `config.usage.time.mixed` | The corresponding `dateTimes.get...()` method. `ClockToText` already uses these methods. |
| `config.usage.date.compact`, `compressed`, `displayday`, `display_template`, `display`; `config.usage.time.display`, `wide_display`, `disabled`; `enabled_display` (date and time) | The front panel is formatted by the `VFD...` options of `ClockToText` or by `dateTimes.getVfdDisplay..()`. |
| Generated config copies such as `config.usage.date.noDay` or `config.usage.time.noMeridiem` | Use `dateTimes.getDateNoDay()` or `dateTimes.getTimeNoMeridiem()` directly. |

A value that a user saved earlier for `config.usage.date.dayfull`, `config.usage.date.display` or `config.usage.time.display` is no longer used. The formats now follow the settings of "Date and Time Settings".

The settings screen is `Screens.DateTime.DateTime`. The unused `Screens/Time.py` forwarding module has been removed. The screen still accepts the `Time`, `setup_Time` and `SetupTime` skin names for existing layouts; this does not migrate saved preferences.

## The `dateTimes` object

Code can ask for a formatted date or time directly:

```python
from time import localtime
from Components.DateTimes import dateTimes

dateTimes.getDateShortDayShortMonthNoYear(localtime(timestamp))  # "Wed, 28-Oct"
dateTimes.getTimeShort()                                         # The current time.
```

All methods take a `time.struct_time` (the default is the current time) and return a string.

| Method | Format on `dateTimes` / purpose |
|---|---|
| `getDate()` | `date` |
| `getDateNoDay()`, `getDateNoDayNoYear()`, `getDateNoDayShortMonth()`, `getDateNoDayShortMonthNoYear()`, `getDateNoYear()` | `dateNoDay`, `dateNoDayNoYear`, `dateNoDayShortMonth`, `dateNoDayShortMonthNoYear`, `dateNoYear` |
| `getDateShortDay()`, `getDateShortDayNoMonthNoYear()`, `getDateShortDayShortMonth()`, `getDateShortDayShortMonthNoYear()` | `dateShortDay`, `dateShortDayNoMonthNoYear`, `dateShortDayShortMonth`, `dateShortDayShortMonthNoYear` |
| `getDateTime()`, `getDateTimeShortDayShortMonthNoSeconds()`, `getDateTimeShortDayShortMonthNoYear()` | Date and time together |
| `getTime()`, `getTimeMixed()`, `getTimeNoMeridiem()`, `getTimeShort()`, `getTimeShortNoMeridiem()` | `time`, `timeMixed`, `timeNoMeridiem`, `timeShort`, `timeShortNoMeridiem` |
| `getTimeWithSeconds()` | Time with explicit seconds, independent of the optional seconds setting |
| `getVfdDisplay08()`, `getVfdDisplay12()`, `getVfdDisplay14()`, `getVfdDisplay18()` | The front panel formats used by `ClockToText` |

The date methods (except `getDateShortDayNoMonthNoYear()`) accept `forceNumeric=True`. This replaces the month name by the month number, so the date can be shown in a narrow space. `dataFormat` replaces the default format with any strftime format. The front panel methods have `forceNumeric=True` by default.

## Code examples for plugins

A plugin cannot know if the hosting build has the new formats. A plugin should therefore test for them and fall back to its former hard coded value:

```python
from time import localtime, strftime
from Components.config import config

t = localtime(beginTime)
if hasattr(config.usage.date, "dayshort"):
	dateText = strftime(config.usage.date.dayshort.value, t)
	timeText = strftime(config.usage.time.short.value, t)
else:
	dateText = strftime("%a %d %b", t)
	timeText = strftime("%H:%M", t)
```

Code that only uses the legacy names (`config.usage.date.dayshort`, `config.usage.time.short`, ...) keeps working on builds that have these names.

The EPG time line shows the idea. Before:

```python
timetext = strftime("%H:%M", ttime)
```

After:

```python
timetext = strftime(config.usage.time.short.value, ttime)
```

Where a column holds times, `config.usage.time.wide` tells the code that more space is needed:

```python
timesWidth = int(fontSize * 5.6)
if config.usage.time.wide.value:
	timesWidth = int(timesWidth * 1.5)
```

Use fixed padding between columns and size the time column from the content, instead of adding extra room to the time column.

## Conclusion

For all Enigma2 builds there is a significant legacy of code and skins that needs to be preserved and protected. The infrastructure is conservative: nothing changes for a skin until its author adds the `AllowUserDatesAndTimes` parameter, the five plugin format names remain available, and plugins can adopt the formats in a way that still supports builds without them.
