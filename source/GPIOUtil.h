#ifndef GPIO_UTIL_h
#define GPIO_UTIL_h

const unsigned int WIDTH_CNT_STORE       = 32;
const unsigned int WIDTH_TRG_CNT         = 32;
const unsigned int WIDTH_TRG_CNT_STORE   = 32;
const unsigned int WIDTH_CNT             = 32;
const unsigned int WIDTH_REAL_CNT        = 32;
const unsigned int WIDTH_REAL_CNT_STORE  = 32;
const unsigned int WIDTH_SW_BUSY         = 1;
const unsigned int WIDTH_SW_READ_ENABLE  = 1;
const unsigned int WIDTH_DAQ_ENABLE      = 1;
const unsigned int WIDTH_DAQ_DISABLE     = 1;
const unsigned int WIDTH_DAQ_STATUS      = 32;
const unsigned int WIDTH_DAQ_KILL        = 1;
const unsigned int WIDTH_DAQ_COUNT_RESET = 1;

const std::string GPIO_DEV_PATH       = "/dev";
const std::string GPIO_DEV_CHIP_STR   = "gpiochip";
const std::string GPIO_DEV_CHIP_PATH  = "/dev/gpiochip";

const unsigned int CHIP_ID_CNT_STORE       = 1;  // 0x4120_0000
const unsigned int CHIP_ID_TRG_CNT         = 19; // 0x4121_0000
const unsigned int CHIP_ID_TRG_CNT_STORE   = 20; // 0x4122_0000
const unsigned int CHIP_ID_CNT             = 0;  // 0x4123_0000
const unsigned int CHIP_ID_REAL_CNT        = 15; // 0x4124_0000
const unsigned int CHIP_ID_REAL_CNT_STORE  = 16; // 0x4125_0000
const unsigned int CHIP_ID_SW_BUSY         = 17; // 0x4126_0000
const unsigned int CHIP_ID_SW_READ_ENABLE  = 18; // 0x4127_0000
const unsigned int CHIP_ID_DAQ_ENABLE      = 4;  // 0x4128_0000
const unsigned int CHIP_ID_DAQ_DISABLE     = 3;  // 0x4129_0000
const unsigned int CHIP_ID_DAQ_STATUS      = 6;  // 0x412a_0000
const unsigned int CHIP_ID_DAQ_KILL        = 5;  // 0x412b_0000
const unsigned int CHIP_ID_DAQ_COUNT_RESET = 2;  // 0x412c_0000


class GPIOUtil
{
public:

    static unsigned int getFullValue( const unsigned int& chipID,
                                      const unsigned int& width );

    static bool         setFullValue( const unsigned int& chipID,
                                      const unsigned int& width,
                                      const unsigned int& value );
    
};


#endif // GPIO_UTIL_h
