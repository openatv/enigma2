#include <lib/base/esettings.h>
#include <lib/gdi/grc.h>

bool eSubtitleSettings::ttx_subtitle_original_position = false;
bool eSubtitleSettings::subtitle_rewrap = false;
int eSubtitleSettings::ttx_subtitle_colors = 1;
int eSubtitleSettings::subtitle_position = 50;
int eSubtitleSettings::dvb_subtitles_original_position = 0;
int eSubtitleSettings::dvb_subtitles_backtrans = 0;
int eSubtitleSettings::dvb_subtitles_color = 0;
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
bool eSubtitleSettings::subtitle_usecache = true;

bool eSubtitleSettings::subtitle_hearingimpaired = false;
bool eSubtitleSettings::subtitle_defaultimpaired = false;
bool eSubtitleSettings::subtitle_defaultdvb = false;
int eSubtitleSettings::equal_languages = 0;

std::string eSubtitleSettings::subtitle_autoselect1 = "";
std::string eSubtitleSettings::subtitle_autoselect2 = "";
std::string eSubtitleSettings::subtitle_autoselect3 = "";
std::string eSubtitleSettings::subtitle_autoselect4 = "";

bool eSettings::remote_fallback_enabled = false;
bool eSettings::use_ci_assignment = false;
std::string eSettings::timeshift_path = "";

bool eSettings::audio_defaultac3 = false;
bool eSettings::audio_defaultddp = false;
bool eSettings::audio_usecache = true;
int eSettings::http_startdelay = 0;


std::string eSettings::audio_autoselect1 = "";
std::string eSettings::audio_autoselect2 = "";
std::string eSettings::audio_autoselect3 = "";
std::string eSettings::audio_autoselect4 = "";

//AI related parameters
bool eSubtitleSettings::ai_enabled = false;
std::string eSubtitleSettings::ai_translate_to = "0";
std::string eSubtitleSettings::ai_subscription_code = "15";
int eSubtitleSettings::ai_subtitle_colors = 1;
int eSubtitleSettings::ai_connection_speed = 1;
