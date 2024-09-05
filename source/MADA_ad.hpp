#ifndef MADA_H
#define MADA_H

#include <libm2k/m2k.hpp>

int ad_message();
int ad_showIDs(libm2k::context::M2k *ctx);
int ad_d_setClock(libm2k::digital::M2kDigital *dio, int dfreq);
int ad_d_init(libm2k::digital::M2kDigital *dio);
int ad_d_cyclic(libm2k::digital::M2kDigital *dio, bool b);
int ad_d_enable(libm2k::digital::M2kDigital *dio);
int ad_d_latch_up(libm2k::digital::M2kDigital *dio);
int ad_d_latch_down(libm2k::digital::M2kDigital *dio);
int ad_d_pulse(libm2k::digital::M2kDigital *dio, unsigned short data);

#endif
