"""

input 是 robotengine 中用于处理输入的模块。

在引擎初始化时，会根据 input_devices 参数创建 Input 实例，并将其传递给所有节点。

注意：在传递 input_devices 非空时，必须提前连接好相应的设备，否则程序会自动终止。

在节点的构造中，可以使用 _input(event: InputEvent) 来以回调的方式处理输入事件，也可以使用 self.input 来显式的访问 Input 实例。

"""


from enum import Enum
import inputs
from robotengine.tools import error, warning, info

# 定义 JoyButton 和 JoyAxis 枚举
class JoyButton(Enum):
    """ 手柄按钮枚举，以下以 Xbox 手柄为例 """
    JOY_BUTTON_INVALID = -1
    """ 无效按钮 """
    JOY_BUTTON_A = 0
    """ A 按钮 """
    JOY_BUTTON_B = 1
    """ B 按钮 """
    JOY_BUTTON_X = 2
    """ X 按钮 """
    JOY_BUTTON_Y = 3
    """ Y 按钮 """
    JOY_BUTTON_BACK = 4
    """ BACK 按钮 """
    JOY_BUTTON_START = 5
    """ START 按钮 """
    JOY_BUTTON_LEFT_STICK = 6
    """ 左摇杆按钮 """
    JOY_BUTTON_RIGHT_STICK = 7
    """ 右摇杆按钮 """
    JOY_BUTTON_LEFT_SHOULDER = 8
    """ 左扳机按钮 """
    JOY_BUTTON_RIGHT_SHOULDER = 9
    """ 右扳机按钮 """

class JoyAxis(Enum):
    """ 手柄轴枚举，以下以 Xbox 手柄为例 """
    JOY_AXIS_INVALID = -1
    """ 无效轴 """
    JOY_AXIS_LEFT_X = 0
    """ 左摇杆 X 轴 """
    JOY_AXIS_LEFT_Y = 1
    """ 左摇杆 Y 轴 """
    JOY_AXIS_RIGHT_X = 2
    """ 右摇杆 X 轴 """
    JOY_AXIS_RIGHT_Y = 3
    """ 右摇杆 Y 轴 """
    JOY_AXIS_TRIGGER_LEFT = 4
    """ 左扳机轴 """
    JOY_AXIS_TRIGGER_RIGHT = 5
    """ 右扳机轴 """
    JOY_AXIS_DPAD_X = 6
    """ D-Pad X 轴 """
    JOY_AXIS_DPAD_Y = 7
    """ D-Pad Y 轴 """

JOY_MAPPING = {
    "A": JoyButton.JOY_BUTTON_A,
    "B": JoyButton.JOY_BUTTON_B,
    "X": JoyButton.JOY_BUTTON_X,
    "Y": JoyButton.JOY_BUTTON_Y,
    "BACK": JoyButton.JOY_BUTTON_BACK,
    "START": JoyButton.JOY_BUTTON_START,
    "LEFT_STICK": JoyButton.JOY_BUTTON_LEFT_STICK,
    "RIGHT_STICK": JoyButton.JOY_BUTTON_RIGHT_STICK,
    "LEFT_SHOULDER": JoyButton.JOY_BUTTON_LEFT_SHOULDER,
    "RIGHT_SHOULDER": JoyButton.JOY_BUTTON_RIGHT_SHOULDER,

    "LEFT_X": JoyAxis.JOY_AXIS_LEFT_X,
    "LEFT_Y": JoyAxis.JOY_AXIS_LEFT_Y,
    "RIGHT_X": JoyAxis.JOY_AXIS_RIGHT_X,
    "RIGHT_Y": JoyAxis.JOY_AXIS_RIGHT_Y,
    "TRIGGER_LEFT": JoyAxis.JOY_AXIS_TRIGGER_LEFT,
    "TRIGGER_RIGHT": JoyAxis.JOY_AXIS_TRIGGER_RIGHT,
    "DPAD_X": JoyAxis.JOY_AXIS_DPAD_X,
    "DPAD_Y": JoyAxis.JOY_AXIS_DPAD_Y
}


INPUTS_BUTTON_MAPPING = {
    "BTN_SOUTH": JoyButton.JOY_BUTTON_A,
    "BTN_EAST": JoyButton.JOY_BUTTON_B,
    "BTN_WEST": JoyButton.JOY_BUTTON_X,
    "BTN_NORTH": JoyButton.JOY_BUTTON_Y,
    "BTN_START": JoyButton.JOY_BUTTON_BACK,
    "BTN_SELECT": JoyButton.JOY_BUTTON_START,
    
    "BTN_THUMBL": JoyButton.JOY_BUTTON_LEFT_STICK,
    "BTN_THUMBR": JoyButton.JOY_BUTTON_RIGHT_STICK,
    "BTN_TL": JoyButton.JOY_BUTTON_LEFT_SHOULDER,
    "BTN_TR": JoyButton.JOY_BUTTON_RIGHT_SHOULDER,
}

INPUTS_AXIS_MAPPING = {
    "ABS_X": JoyAxis.JOY_AXIS_LEFT_X,
    "ABS_Y": JoyAxis.JOY_AXIS_LEFT_Y,
    "ABS_RX": JoyAxis.JOY_AXIS_RIGHT_X,
    "ABS_RY": JoyAxis.JOY_AXIS_RIGHT_Y,

    "ABS_Z": JoyAxis.JOY_AXIS_TRIGGER_LEFT,
    "ABS_RZ": JoyAxis.JOY_AXIS_TRIGGER_RIGHT,

    "ABS_HAT0X": JoyAxis.JOY_AXIS_DPAD_X,
    "ABS_HAT0Y": JoyAxis.JOY_AXIS_DPAD_Y
}

INPUTS_AXIS_VALUE_MAPPING = {
    "ABS_X": 32767.0,
    "ABS_Y": 32767.0,
    "ABS_RX": 32767.0,
    "ABS_RY": 32767.0,

    "ABS_Z": 255.0,
    "ABS_RZ": 255.0,

    "ABS_HAT0X": 1.0,
    "ABS_HAT0Y": 1.0
}

# 定义 InputEvent 类以及子类
class InputEvent:
    """ 输入事件基类 """
    def __init__(self):
        pass

    def get_action_strength(self, action: str) -> float:
        """ 返回某个动作的强度 """
        pass

    def is_action_pressed(self, action: str) -> bool:
        """ 检查某个动作是否被按下 """
        pass

    def is_action_released(self, action: str) -> bool:
        """ 检查某个动作是否被释放 """
        pass

class InputEventJoypadButton(InputEvent):
    """手柄按钮事件"""
    def __init__(self, button_index: JoyButton, pressed: bool):
        """ 初始化手柄按键事件 """
        self.button_index: JoyButton = button_index
        """ 当前按键索引 """
        self.pressed: bool = pressed
        """ 当前按键是否被按下 """

    def is_action_pressed(self, action: str) -> bool:
        """ 检查当前事件是否是某个手柄按键被按下 """
        if JOY_MAPPING.get(action) == self.button_index and self.pressed:
            return True
        return False

    def is_action_released(self, action: str) -> bool:
        """ 检查当前事件是否是某个手柄按键被释放 """
        if JOY_MAPPING.get(action) == self.button_index and not self.pressed:
            return True
        return False
    
    def __repr__(self):
        return f"JoypadButton({self.button_index}, {self.pressed})"

class InputEventJoypadAxis(InputEvent):
    """手柄轴事件"""
    def __init__(self, axis: JoyAxis, axis_value: float):
        """ 初始化手柄轴事件 """
        self.axis: JoyAxis = axis
        """ 当前轴索引 """
        self.axis_value: float = axis_value
        """ 当前轴值 """

    def get_action_strength(self, action: str) -> float:
        """ 检查当前事件的某个轴值 """
        if JOY_MAPPING.get(action) == self.axis:
            return self.axis_value
        return 0.0
    
    def __repr__(self):
        return f"JoypadAxis({self.axis}, {self.axis_value})"

class GamepadListener():
    def __init__(self):
        self.devices = inputs.devices.gamepads
        if not self.devices:
            error("您开启了 Gamepad 输入检测，但是未检测到 Gamepad 设备，请连接 Gamepad 设备后重试")
        else:
            info(f"您开启了 Gamepad 输入检测，检测到 {len(self.devices)} 个 Gamepad 设备, 将使用第一个设备 {self.devices[0].name} 进行输入检测")

    def listen(self) -> InputEvent: # type: ignore
        """监听手柄输入并生成事件"""
        _events = inputs.get_gamepad()
        for _event in _events:
            if _event.ev_type == 'Key':
                # 假设是按键事件
                button_index = JoyButton(INPUTS_BUTTON_MAPPING.get(_event.code))  # 获取按键代码
                pressed = _event.state == 1
                input_event = InputEventJoypadButton(button_index, pressed)
                yield input_event
            elif _event.ev_type == 'Absolute':
                # 假设是轴向事件
                axis = JoyAxis(INPUTS_AXIS_MAPPING.get(_event.code))  # 获取轴向代码
                axis_value = _event.state / INPUTS_AXIS_VALUE_MAPPING.get(_event.code)
                input_event = InputEventJoypadAxis(axis, axis_value)
                yield input_event

class Input:
    def __init__(self):
        self._button_states = {
            'A': False,
            'B': False,
            'X': False,
            'Y': False,
            'BACK': False,
            'START': False,
            'LEFT_STICK': False,
            'RIGHT_STICK': False,
            'LEFT_SHOULDER': False,
            'RIGHT_SHOULDER': False,
        }

        self._axis_states = {
            'LEFT_X': 0.0,
            'LEFT_Y': 0.0,
            'RIGHT_X': 0.0,
            'RIGHT_Y': 0.0,
            'TRIGGER_LEFT': 0.0,
            'TRIGGER_RIGHT': 0.0,
            'DPAD_X': 0.0,
            'DPAD_Y': 0.0
        }


    def get_key_from_value(self, mapping, value):
        for key, val in mapping.items():
            if val == value:
                return key
        return None

    def update(self, event: InputEvent):
        if isinstance(event, InputEventJoypadButton):
            self._button_states[self.get_key_from_value(JOY_MAPPING, event.button_index)] = event.pressed
        elif isinstance(event, InputEventJoypadAxis):
            self._axis_states[self.get_key_from_value(JOY_MAPPING, event.axis)] = event.axis_value

    def get_axis(self, negative_action: str, positive_action: str) -> float:
        if negative_action not in self.axis_states or positive_action not in self.axis_states:
            raise ValueError(f"无效的 axis 动作: {negative_action}, {positive_action}")
        negative = self._axis_states[negative_action]
        positive = self._axis_states[positive_action]

        return positive - negative
    
    def get_action_strength(self, action: str) -> bool:
        if action in self._axis_states:
            return self._axis_states[action]
        else:
            raise ValueError(f"无效的动作: {action}")
    
    def is_action_pressed(self, action: str) -> bool:
        if action in self._button_states:
            return self._button_states[action]
        else:
            raise ValueError(f"无效的动作: {action}")
        
    def is_action_released(self, action: str) -> bool:
        if action in self._button_states:
            return not self._button_states[action]
        else:
            raise ValueError(f"无效的动作: {action}")
    
    def is_anything_pressed(self) -> bool:
        for value in self._button_states.values():
            if value:
                return True
        return False