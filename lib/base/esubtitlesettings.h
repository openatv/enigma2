#ifndef __esubtitlesettings_h
#define __esubtitlesettings_h

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
        static void setDVBSubtitleYellow(bool value) { dvb_subtitles_yellow = value; }
        static void setDVBSubtitleCentered(bool value) { dvb_subtitles_centered = value; }
        static void setSubtitleReWrap(bool value) { subtitle_rewrap = value; }
        static void setSubtitlePosition(int value) { subtitle_position = value;}
        static void setSubtitleAligment(int value) { subtitle_alignment_flag = value; }
        static void setSubtitleBorderWith(int value) { subtitle_borderwidth = value; }
        static void setSubtitleFontSize(int value) { subtitle_fontsize = value; }
        static void setSubtitleBacktrans(int value) { subtitles_backtrans = value; }
        static void setSubtitleColoriseDialogs(bool value) { colorise_dialogs = value; }
        static void setSubtitleNoPTSDelay(int value) { subtitle_noPTSrecordingdelay = value; }
        static void setSubtitleBadTimingDelay(int value) { subtitle_bad_timing_delay = value; }

        static bool ttx_subtitle_original_position;
        static bool subtitle_rewrap;
        static int ttx_subtitle_colors;
        static int subtitle_position;
        static int dvb_subtitles_original_position;
        static int dvb_subtitles_backtrans;
        static bool dvb_subtitles_yellow;
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

};

#endif
