import os

'''
Environmental  variables
'''

MADA_ENV_PATH    = os.environ["MADAPATH"]
NETUTIL_ENV_PATH = os.environ["NETWORKUTILPATH"]
PYLIB_ENV_PATH   = os.environ["PYTHONPATH"]
HOME_ENV_PATH    = os.environ["HOME"]

'''
C++ binary
'''

CPP_MADA_IWAKI = "MADA_iwaki"


'''
Definition of MADA constants.
'''

DEF_FILESIZE         = 1000  # data size in Mbyte
DEF_CONFIGFILE       = "MADA_config.json"
DEF_CONFIG_SKEL_FILE = "MADA_config_SKEL.json"
DEF_RATEPATH         = f"{HOME_ENV_PATH}/rate/"

MAX_BOARDS = 10
ALL_BOARDS = [
    "GBKB-00",
    "GBKB-01",
    "GBKB-03",
    "GBKB-04",
    "GBKB-05",
    "GBKB-11",
    "GBKB-13",
    "GBKB-14",
    "GBKB-15",
    "GBKB-16",
]

'''
MADA Control words for UDP data transfer
'''
CTRL_SYS_MIRACLUE = 0b00000001.to_bytes( 1, "little" )

CTRL_ROLE_MASTER  = 0b00000001.to_bytes( 1, "little" )
CTRL_ROLE_SERVER  = 0b00000010.to_bytes( 1, "little" )
CTRL_ROLE_CTRL    = 0b00000100.to_bytes( 1, "little" )

CTRL_CMD_CHKHB    = 0b00000001.to_bytes( 1, "little" )
CTRL_CMD_DAQSTART = 0b00000010.to_bytes( 1, "little" )
CTRL_CMD_DAQSTOP  = 0b00000011.to_bytes( 1, "little" )
CTRL_CMD_CHECKDAQ = 0b00000100.to_bytes( 1, "little" )

CTRL_VAL_TRUE     = 0b00000001.to_bytes( 1, "little" )
CTRL_VAL_FALSE    = 0b00000010.to_bytes( 1, "little" )

'''
MADA Control packet
'''

PACKET_DAQSTART = CTRL_SYS_MIRACLUE + CTRL_ROLE_MASTER + CTRL_CMD_DAQSTART + CTRL_VAL_TRUE
PACKET_DAQSTOP  = CTRL_SYS_MIRACLUE + CTRL_ROLE_MASTER + CTRL_CMD_DAQSTOP  + CTRL_VAL_TRUE
PACKET_CHECKDAQ = CTRL_SYS_MIRACLUE + CTRL_ROLE_MASTER + CTRL_CMD_CHECKDAQ + CTRL_VAL_TRUE
