#ifndef __MHW_H__
#define __MHW_H__

#include <sys/types.h>

/* Structures for MHW-EPG tables parsing */

typedef struct {
   u_char	network_id_hi;
   u_char	network_id_lo;
   u_char	transport_stream_id_hi;
   u_char	transport_stream_id_lo;
   u_char	channel_id_hi;
   u_char	channel_id_lo;
   u_char	name[16];

   int getNetworkId() const         { return network_id_hi << 8 | network_id_lo; };
   int getTransportStreamId() const { return transport_stream_id_hi << 8 | transport_stream_id_lo; };
   int getChannelId() const         { return channel_id_hi << 8 | channel_id_lo; };
} mhw_channel_name_t;

typedef struct {
   u_char	name[15];
} mhw_theme_name_t;

struct summary_min {
#if BYTE_ORDER == BIG_ENDIAN
   u_char minutes                                :6;
   u_char                                        :1;
   u_char summary_available                      :1;
#else
   u_char summary_available                      :1;
   u_char                                        :1;
   u_char minutes                                :6;
#endif
};

struct day_hours {
#if BYTE_ORDER == BIG_ENDIAN
   u_char day                                    :3;
   u_char hours                                  :5;
#else
   u_char hours                                  :5;
   u_char day                                    :3;
#endif
};

typedef struct {
   u_char table_id                               :8;
#if BYTE_ORDER == BIG_ENDIAN
   u_char section_syntax_indicator               :1;
   u_char dummy                                  :1;
   u_char                                        :2;
   u_char section_length_hi                      :4;
#else
   u_char section_length_hi                      :4;
   u_char                                        :2;
   u_char dummy                                  :1;
   u_char section_syntax_indicator               :1;
#endif
   union {
   u_char section_length_lo                      :8;
   u_char mhw2_theme                             :8;
   };
   u_char channel_id                             :8;
   union {
     u_char theme_id                             :8;
     u_char mhw2_hours                           :8;
   };
   union {
     struct day_hours dh;
     u_char mhw2_minutes                         :8;
   };
   union {
     struct summary_min ms;
     u_char mhw2_seconds                         :8;
   };
   u_char                                        :8; // mhw2_title begin
   u_char                                        :8;
   u_char duration_hi                            :8;
   u_char duration_lo                            :8;
   u_char title                                [23];
   u_char ppv_id_hi                              :8;
   u_char ppv_id_mh                              :8;
   u_char ppv_id_ml                              :8;
   u_char ppv_id_lo                              :8;
   u_char program_id_hi                          :8;
   u_char program_id_mh                          :8;
   u_char program_id_ml                          :8;
   u_char program_id_lo                          :8; // mhw2_title end (35chars max)
   u_char mhw2_mjd_hi                            :8;
   u_char mhw2_mjd_lo                            :8;
   u_char mhw2_duration_hi                       :8;
   u_char mhw2_duration_lo                       :8;

   int getDuration() const     { return duration_hi << 8 | duration_lo; };
   int getMhw2Duration() const { return mhw2_duration_hi << 8 | mhw2_duration_lo; };
} mhw_title_t;

typedef struct mhw_summary {
   u_char table_id                               :8;
#if BYTE_ORDER == BIG_ENDIAN
   u_char section_syntax_indicator               :1;
   u_char dummy                                  :1;
   u_char                                        :2;
   u_char section_length_hi                      :4;
#else
   u_char section_length_hi                      :4;
   u_char                                        :2;
   u_char dummy                                  :1;
   u_char section_syntax_indicator               :1;
#endif
   u_char section_length_lo                      :8;
   u_char program_id_hi                          :8;
   u_char program_id_mh                          :8;
   u_char program_id_ml                          :8;
   u_char program_id_lo                          :8;
   u_char                                        :8;
   u_char                                        :8;
   u_char                                        :8;
   u_char nb_replays                             :8;
} mhw_summary_t;

#endif

