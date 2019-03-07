from time import sleep
from onvif import ONVIFCamera

# Исправление ошибки "NotImplementedError: AnySimpleType.pytonvalue() not implemented"
import zeep
from onvif import ONVIFCamera, ONVIFService

def zeep_pythonvalue(self, xmlvalue):
    return xmlvalue

zeep.xsd.simple.AnySimpleType.pythonvalue = zeep_pythonvalue

# Класс для работы с камерой
class Camera(object):

    # Конструктор для инициализации
    def __init__(self, ip, login, password, port = 80):
        # Подключение
        self.mycam = ONVIFCamera(ip, port, login, password)

        # Получение профиля, в котором содержатся необходимые токены
        # (Понадобятся в запросах)
        self.media = self.mycam.create_media_service()
        self.media_profile = self.media.GetProfiles()[0]  
        self.video_source_token = self.media.GetVideoSourceConfigurationOptions().VideoSourceTokensAvailable[0]

        # Создание сервиса для управления движением
        self.ptz = self.mycam.create_ptz_service()
        # Создание сервиса для управления настройками изображения
        self.img = self.mycam.create_imaging_service()

        # Для получения пределов движения по осям понадобятся параметры конфигурации сервиса PTZ
        opt_request = self.ptz.create_type('GetConfigurationOptions')
        opt_request.ConfigurationToken = self.media_profile.PTZConfiguration.token
        self.ptz_configuration_options = self.ptz.GetConfigurationOptions(opt_request)

        # Запрос конфигурации для изображения
        opt_request = self.img.create_type('GetMoveOptions')
        opt_request.VideoSourceToken = self.video_source_token   
        self.img_move_options = self.img.GetMoveOptions(opt_request)

############
# ПРОВЕРКИ #
############

    # Проверка: поддерживает ли Absolute Move
    def checkAbsoluteMove(self):
        # Получение параметров конфигурации Absolute Move
        absPanTiltSpace = self.ptz_configuration_options.Spaces.AbsolutePanTiltPositionSpace
        absZoomSpace = self.ptz_configuration_options.Spaces.AbsoluteZoomPositionSpace
        # Если space имеет значение None, данная функция не поддерживается
        if absPanTiltSpace and absZoomSpace:
            print("Camera supports Absolute Move")
        elif absPanTiltSpace:
            print("Camera supports Absolute Move: PanTilt only")
        elif absZoomSpace:
            print("Camera supports Absolute Move: Zoom only")
        else:   
            print("Absolute Move is not supported")


    # Проверка: отдаёт ли свои текущие координаты PTZ
    def checkPTZPosition(self):
        # Получение текущей позиции PTZ
        pos = self.ptz.GetStatus({'ProfileToken': self.media_profile.token}).Position
        # Если space имеет значение None, данная координата не отдается

        if (not pos.PanTilt or not pos.PanTilt.space) and (not pos.Zoom or not pos.Zoom.space):
            print("PTZ Position unknown")
        elif not pos.Zoom or not pos.Zoom.space:
            print("PTZ Position: x = ", pos.PanTilt.x, ", y = ", pos.PanTilt.y, ", zoom unknown")
        elif not pos.PanTilt or not pos.PanTilt.space:
            print("PTZ Position: x and y unknown, zoom = ", pos.Zoom.x)
        else:
            print("PTZ Position: x = ", pos.PanTilt.x, ", y = ", pos.PanTilt.y, ", zoom = ", pos.Zoom.x)


    # Проверка: показывает ли камера значение фокуса
    def checkFocusValue(self):
        pos = self.img.GetStatus({'VideoSourceToken' : self.video_source_token}).FocusStatus20.Position
        if pos:
            print("Focus position: ", pos)
        else:
            print("Unknown focus position")

    # Проверка доступных режимов изменения фокуса
    def checkFocusMove(self):
        if self.img_move_options.Absolute == None:
            print("Absolute Focus Move is not supported")
        else:
            print("Camera suports Absolute Focus Move")
        if self.img_move_options.Relative == None:
            print("Relative Focus Move is not supported")
        else:
            print("Camera suports Relative Focus Move")
        if self.img_move_options.Continuous == None:
            print("Continuous Focus Move is not supported")
        else:
            print("Camera suports Continuous Focus Move")     

 
#################
# ABSOLUTE MOVE #
#################

    # Получение данных для Absolute Move
    def initAbsoluteMove(self):
        # Пределы движения
        XMAX = self.ptz_configuration_options.Spaces.AbsolutePanTiltPositionSpace[0].XRange.Max
        XMIN = self.ptz_configuration_options.Spaces.AbsolutePanTiltPositionSpace[0].XRange.Min
        YMAX = self.ptz_configuration_options.Spaces.AbsolutePanTiltPositionSpace[0].YRange.Max
        YMIN = self.ptz_configuration_options.Spaces.AbsolutePanTiltPositionSpace[0].YRange.Min
        ZMAX = self.ptz_configuration_options.Spaces.AbsoluteZoomPositionSpace[0].XRange.Max
        ZMIN = self.ptz_configuration_options.Spaces.AbsoluteZoomPositionSpace[0].XRange.Min

        # Вывод пределов на экран
        print("Absolute Move limits:")
        print("\tXmin: ", XMIN, "; Xmax: ", XMAX)
        print("\tYmin: ", YMIN, "; Ymax: ", YMAX)
        print("\tZmin: ", ZMIN, "; Zmax: ", ZMAX)

        # Создание запроса отправки координат
        self.abs_request = self.ptz.create_type('AbsoluteMove')
        self.abs_request.ProfileToken = self.media_profile.token

        # Так как в созданном запросе атрибут Position = None,
        # присваиваем ему объект с аналогичной структурой 
        self.abs_request.Position = self.ptz.GetStatus({'ProfileToken': self.media_profile.token}).Position
        self.abs_request.Position.PanTilt.space = None
        self.abs_request.Position.Zoom.space = None


    def absoluteMove(self, x, y, z):
        # На случай, если камера уже двигается, выполняется остановка
        self.ptz.Stop({'ProfileToken': self.media_profile.token})

        # Передача координат в запрос
        self.abs_request.Position.PanTilt.x = x
        self.abs_request.Position.PanTilt.y = y
        self.abs_request.Position.Zoom.x = z

        #  Отправка запроса
        self.ptz.AbsoluteMove(self.abs_request)


###################
# CONTINUOUS MOVE #
###################

   # Получение данных для Continuous Move
    def initContinuousMove(self):
        # Пределы движения
        XMAX = self.ptz_configuration_options.Spaces.ContinuousPanTiltVelocitySpace[0].XRange.Max
        XMIN = self.ptz_configuration_options.Spaces.ContinuousPanTiltVelocitySpace[0].XRange.Min
        YMAX = self.ptz_configuration_options.Spaces.ContinuousPanTiltVelocitySpace[0].YRange.Max
        YMIN = self.ptz_configuration_options.Spaces.ContinuousPanTiltVelocitySpace[0].YRange.Min
        ZMAX = self.ptz_configuration_options.Spaces.ContinuousZoomVelocitySpace[0].XRange.Max
        ZMIN = self.ptz_configuration_options.Spaces.ContinuousZoomVelocitySpace[0].XRange.Min

        # Вывод пределов на экран
        print("Continuous Move limits:")
        print("\tXmin: ", XMIN, "; Xmax: ", XMAX)
        print("\tYmin: ", YMIN, "; Ymax: ", YMAX)
        print("\tZmin: ", ZMIN, "; Zmax: ", ZMAX)

        # Для управления камерой необходимо создать запрос типа ContinuousMove
        self.cont_request = self.ptz.create_type('ContinuousMove')
        self.cont_request.ProfileToken = self.media_profile.token
        # Так как в созданном запросе атрибут Velosity = None, 
        # замещаем его объектом с аналогичной структурой
        self.cont_request.Velocity = self.ptz.GetStatus({'ProfileToken': self.media_profile.token}).Position
        self.cont_request.Velocity.PanTilt.space = ''
        self.cont_request.Velocity.Zoom.space = ''

        

    # Функция для задания движения в режиме Continuous Move 
    # Принимает скорость и продолжительность движения по каждой оси
    # Требует предварительного вызова initContinuousMove()   
    def continuousMove(self, x = 0.0, xtime = 0, y = 0.0, ytime = 0, z = 0.0, ztime = 0):
        # На случай, если камера уже двигается, выполняется остановка
        self.ptz.Stop({'ProfileToken': self.media_profile.token})
        # Обработка отдельно каждой оси
        self.continuousMoveAxis('x', x, xtime)
        self.continuousMoveAxis('y', y, ytime)
        self.continuousMoveAxis('z', z, ztime)

    # Обработка заданной оси (название оси, скорость, продолжительность)
    def continuousMoveAxis(self, axis, value, timeout):
        # Сброс значений по осям 
        self.cont_request.Velocity.PanTilt.x = 0.0
        self.cont_request.Velocity.PanTilt.y = 0.0
        self.cont_request.Velocity.Zoom.x = 0.0

        # Значение задается для указанной оси
        if axis == 'x':
            self.cont_request.Velocity.PanTilt.x = value
        elif axis == 'y':
            self.cont_request.Velocity.PanTilt.y = value
        elif axis == 'z':
            self.cont_request.Velocity.Zoom.x = value

        # Начинается движение
        self.ptz.ContinuousMove(self.cont_request)
        # Ожидание 
        sleep(timeout)
        # Остановка движения
        self.ptz.Stop({'ProfileToken': self.cont_request.ProfileToken})


#########
# FOCUS #
#########

    # Подготовка к командам изменения фокуса
    def initContinuousFocusMove(self):
        # Переключение режима фокусировки на ручной
        self.activateManualFocus()

        # Определение пределов для изменения фокуса в режиме Continuous Move
        FMIN = self.img_move_options.Continuous.Speed.Min
        FMAX = self.img_move_options.Continuous.Speed.Max
        print("Continuous Focus Move speed limits: min = ", FMIN, "; max = ", FMAX)

        # Создание запроса для изменения фокуса
        self.f_request = self.img.create_type('Move')
        self.f_request.VideoSourceToken = self.video_source_token
        # Элемент с похожей структурой: MoveOptions
        self.f_request.Focus = self.img_move_options
        self.f_request.Focus.Continuous.Speed = 0
        # Неиспользуемые типЫ движения
        self.f_request.Focus.Absolute = None
        self.f_request.Focus.Relative = None

    def activateManualFocus(self):
        # Получение текущих настроек
        settings = self.img.GetImagingSettings({'VideoSourceToken': self.video_source_token})
        # Изменение параметра
        settings.Focus.AutoFocusMode = 'MANUAL'
        # Отправка измененных настроек
        request = self.img.create_type('SetImagingSettings')
        request.VideoSourceToken = self.video_source_token
        request.ImagingSettings = settings
        self.img.SetImagingSettings(request)
        print ("Changed Focus Mode to MANUAL")

    # Команда на изменение фокуса, 
    # требует предварительного вызова initContinuousFocusMove
    def continuousFocusMove(self, speed):
        # Добавление в запрос требуемой скорости
        self.f_request.Focus.Continuous.Speed = speed
        # Отправка запроса
        self.img.Move(self.f_request)
