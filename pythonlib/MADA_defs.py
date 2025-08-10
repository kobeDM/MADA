'''
Definition of MADA constants.
'''



'''
MADA Control words for UDP data transfer
'''
MADA_CTRL_SYS_MIRACLUE = 0b00000001.to_bytes( 1, "little" )

MADA_CTRL_ROLE_MASTER  = 0b00000001.to_bytes( 1, "little" )
MADA_CTRL_ROLE_SERVER  = 0b00000010.to_bytes( 1, "little" )
MADA_CTRL_ROLE_CTRL    = 0b00000100.to_bytes( 1, "little" )

MADA_CTRL_CMD_CHKHB    = 0b00000001.to_bytes( 1, "little" )
MADA_CTRL_CMD_DAQSTART = 0b00000010.to_bytes( 1, "little" )
MADA_CTRL_CMD_DAQSTOP  = 0b00000011.to_bytes( 1, "little" )

MADA_CTRL_VAL_TRUE     = 0b00000001.to_bytes( 1, "little" )
MADA_CTRL_VAL_FALSE    = 0b00000010.to_bytes( 1, "little" )

'''
MADA Control packet
'''

MADA_PACKET_DAQSTART = MADA_CTRL_SYS_MIRACLUE + MADA_CTRL_ROLE_MASTER + MADA_CTRL_CMD_DAQSTART + MADA_CTRL_VAL_TRUE
MADA_PACKET_DAQSTART = MADA_CTRL_SYS_MIRACLUE + MADA_CTRL_ROLE_MASTER + MADA_CTRL_CMD_DAQSTOP  + MADA_CTRL_VAL_TRUE



