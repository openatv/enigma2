#ifndef __esettings_h
#define __esettings_h
#include <string>

class eSubtitleSettings
{
public:
  eSubtitleSettings() = default;

  static void setTTXSubtitleOriginalPosition(bool value) { ttx_subtitle_original_position = value; }
  static void setTTXSubtitleColors(int value) { ttx_subtitle_colors = value; }
  static void setPangoSubtitleRemovehi(bool value) { pango_subtitle_removehi = value; }
  static void setPangoSubtitleFontWitch(bool value) { pango_subtitle_fontswitch = value; }
  static void setPangoSubtitleColors(int value) { pango_subtitle_colors = value; }
  static void setPangoSubtitleDelay(int value) { pango_subtitles_delay = value; }
  static void setPangoSubtitleFPS(int value) { pango_subtitles_fps = value; }
  static void setPangoSubtitleAutoRun(bool value) { pango_autoturnon = value; }
  static void setDVBSubtitleOriginalPosition(int value) { dvb_subtitles_original_position = value; }
  static void setDVBSubtitleBacktrans(int value) { dvb_subtitles_backtrans = value; }
  static void setDVBSubtitleColor(int value) { dvb_subtitles_color = value; }
  static void setDVBSubtitleCentered(bool value) { dvb_subtitles_centered = value; }
  static void setSubtitleReWrap(bool value) { subtitle_rewrap = value; }
  static void setSubtitlePosition(int value) { subtitle_position = value; }
  static void setSubtitleAligment(int value) { subtitle_alignment_flag = value; }
  static void setSubtitleBorderWith(int value) { subtitle_borderwidth = value; }
  static void setSubtitleFontSize(int value) { subtitle_fontsize = value; }
  static void setSubtitleBacktrans(int value) { subtitles_backtrans = value; }
  static void setSubtitleColoriseDialogs(bool value) { colorise_dialogs = value; }
  static void setSubtitleNoPTSDelay(int value) { subtitle_noPTSrecordingdelay = value; }
  static void setSubtitleBadTimingDelay(int value) { subtitle_bad_timing_delay = value; }
  static void setSubtitleUseCache(bool value) { subtitle_usecache = value; }
  static void setSubtitleLanguages(const std::string &autoselect1, const std::string &autoselect2, const std::string &autoselect3, const std::string &autoselect4)
  {
    subtitle_autoselect1 = autoselect1;
    subtitle_autoselect2 = autoselect2;
    subtitle_autoselect3 = autoselect3;
    subtitle_autoselect4 = autoselect4;
  }
  static void setSubtitleHearingImpaired(bool value) { subtitle_hearingimpaired = value; }
  static void setSubtitleDefaultImpaired(bool value) { subtitle_defaultimpaired = value; }
  static void setSubtitleDefaultDVB(bool value) { subtitle_defaultdvb = value; }
  static void setSubtitleEqualLanguages(int value) { equal_languages = value; }

  static bool ttx_subtitle_original_position;
  static bool subtitle_rewrap;
  static int ttx_subtitle_colors;
  static int subtitle_position;
  static int dvb_subtitles_original_position;
  static int dvb_subtitles_backtrans;
  static int dvb_subtitles_color;
  static bool dvb_subtitles_centered;
  static int subtitle_alignment_flag;
  static int subtitle_borderwidth;
  static int subtitle_fontsize;
  static int subtitles_backtrans;
  static bool pango_subtitle_removehi;
  static bool pango_subtitle_fontswitch;
  static int pango_subtitle_colors;
  static int pango_subtitles_delay;
  static int pango_subtitles_fps;
  static bool pango_autoturnon;
  static bool colorise_dialogs;
  static int subtitle_noPTSrecordingdelay;
  static int subtitle_bad_timing_delay;
  static bool subtitle_usecache;

  static bool subtitle_hearingimpaired;
  static bool subtitle_defaultimpaired;
  static bool subtitle_defaultdvb;
  static int equal_languages;

  static std::string subtitle_autoselect1;
  static std::string subtitle_autoselect2;
  static std::string subtitle_autoselect3;
  static std::string subtitle_autoselect4;

  //AI related parameters
  static void setAiEnabled(bool value) { ai_enabled = value; }
  static void setAiTranslateTo(std::string value) { ai_translate_to = value; }
  static void setAiSubscriptionCode(std::string value) { ai_subscription_code = value; }
  static void setAiSubtitleColors(int value) { ai_subtitle_colors = value; }
  static void setAiConnectionSpeed(int value) { ai_connection_speed = value; }
  static void setAiMode(int value) { ai_mode = value; }
  static bool ai_enabled;
  static std::string ai_translate_to;
  static std::string ai_subscription_code;
  static int ai_subtitle_colors;
  static int ai_connection_speed;//1=Up to 50 Mbps, 2=50-200 Mbps, 3=Above 200 Mbps
  static int ai_mode;

};

class eSettings
{
public:
  eSettings() = default;

  static void setRemoteFallbackEnabled(bool value) { remote_fallback_enabled = value; }
  static void setUseCIAssignment(bool value) { use_ci_assignment = value; }
  static void setTimeshiftPath(const std::string &value) { timeshift_path = value; }
  static void setAudioLanguages(const std::string &autoselect1, const std::string &autoselect2, const std::string &autoselect3, const std::string &autoselect4)
  {
    audio_autoselect1 = autoselect1;
    audio_autoselect2 = autoselect2;
    audio_autoselect3 = autoselect3;
    audio_autoselect4 = autoselect4;
  }
  static void setAudioDefaultAC3(bool value) { audio_defaultac3 = value; }
  static void setAudioDefaultDDP(bool value) { audio_defaultddp = value; }
  static void setAudioUseCache(bool value) { audio_usecache = value; }
  static void setHttpStartDelay(int value) { http_startdelay = value; }

  static bool remote_fallback_enabled;
  static bool use_ci_assignment;
  static std::string timeshift_path;

  static bool audio_defaultac3;
  static bool audio_defaultddp;
  static bool audio_usecache;
  static int http_startdelay;

  static std::string audio_autoselect1;
  static std::string audio_autoselect2;
  static std::string audio_autoselect3;
  static std::string audio_autoselect4;
};

#endif
