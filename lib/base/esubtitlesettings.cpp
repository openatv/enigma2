#include <lib/base/esubtitlesettings.h>
#include <lib/gdi/grc.h>

bool eSubtitleSettings::ttx_subtitle_original_position = false;
bool eSubtitleSettings::subtitle_rewrap = false;
int eSubtitleSettings::ttx_subtitle_colors = 1;
int eSubtitleSettings::subtitle_position = 50;
int eSubtitleSettings::dvb_subtitles_original_position = 0;
int eSubtitleSettings::dvb_subtitles_backtrans = 0;
bool eSubtitleSettings::dvb_subtitles_yellow = false;
bool eSubtitleSettings::dvb_subtitles_centered = false;
int eSubtitleSettings::subtitle_alignment_flag = gPainter::RT_HALIGN_CENTER;
bool eSubtitleSettings::colorise_dialogs = false;
int eSubtitleSettings::subtitle_borderwidth = 2;
int eSubtitleSettings::subtitle_fontsize = 40;
int eSubtitleSettings::subtitles_backtrans = 255;
bool eSubtitleSettings::pango_subtitle_removehi = false;
bool eSubtitleSettings::pango_subtitle_fontswitch = false;
int eSubtitleSettings::pango_subtitle_colors = 1;
int eSubtitleSettings::pango_subtitles_delay = 0;
int eSubtitleSettings::pango_subtitles_fps = 1;
bool eSubtitleSettings::pango_autoturnon = true;
int eSubtitleSettings::subtitle_noPTSrecordingdelay = 315000;
int eSubtitleSettings::subtitle_bad_timing_delay = 0;
