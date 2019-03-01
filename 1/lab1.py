#########################
#  Лабораторная Onvif-1 #
#########################


# Подключение к камере
from ptzcamera import *
cam42 = Camera('192.168.15.42', 'maden98', 'QvDcgHBkMPGV')

# Проверки
cam42.checkAbsoluteMove()
cam42.checkPTZPosition()
cam42.checkFocusValue()
cam42.checkFocusMove()

# Движение в режиме Absolute Move
cam42.initAbsoluteMove()
cam42.absoluteMove(0.9, 0, 0.8)
cam42.absoluteMove(-0.3, -0.5, 0)

# Движение в режиме Continuous Move
cam42.initContinuousMove()
cam42.continuousMove(-0.8, 2, 0.5, 1.5, 0.2, 0.5)

# Управление фокусом
cam42.initContinuousFocusMove()
cam42.continuousFocusMove(-2)
cam42.continuousFocusMove(4)