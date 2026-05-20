#ifndef ADALMUTIL_H
#define ADALMUTIL_H

#include <iostream>
#include <string>
#include <vector>

#include <libm2k/analog/m2kanalogin.hpp>
#include <libm2k/analog/m2kanalogout.hpp>
#include <libm2k/analog/m2kpowersupply.hpp>
#include <libm2k/contextbuilder.hpp>
#include <libm2k/digital/m2kdigital.hpp>  //for dio
#include <libm2k/m2k.hpp>

using namespace libm2k;
using namespace libm2k::analog;
using namespace libm2k::digital;  // for dio
using namespace libm2k::context;

// Connection
M2k *ConnectToAdalmWithSerial( const std::string &serialNumber );

// I/O control
void AnalogDcOut( M2kAnalogOut *aout, int channel, double voltage );
void DigitalLatchUp( M2kDigital *dout, const int channel[16] );
void DigitalLatchDown( M2kDigital *dout, const int channel[16] );
void OutputWaveformSquare( M2kAnalogOut *aout, int channel, double voltage, double frequency );

// Disconnection
void DisconnectAdalm( M2k *m2k );

#endif  // ADALMUTIL_H