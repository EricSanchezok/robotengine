from typing import Callable
from .tools import warning

class Signal:
    def __init__(self, *param_types):
        self._callbacks = []
        self.param_types = param_types  # 存储信号的预期参数类型

    def connect(self, callback: Callable):
        if callback not in self._callbacks:
            self._callbacks.append(callback)
        else:
            warning(f"{callback} 已经存在，请勿重复添加")

    def disconnect(self, callback: Callable):
        if callback in self._callbacks:
            self._callbacks.remove(callback)
        else:
            warning(f"{callback} 不存在，请勿重复删除")

    def emit(self, *args, **kwargs):
        if len(args) != len(self.param_types):
            raise TypeError(f"Expected {len(self.param_types)} arguments, but got {len(args)}")

        for expected_type, actual_arg in zip(self.param_types, args):
            if not isinstance(actual_arg, expected_type):
                raise TypeError(f"Expected argument of type {expected_type}, but got {type(actual_arg)}")

        for callback in self._callbacks:
            callback(*args, **kwargs)

    def __repr__(self):
        return f"Signal(connected callbacks={len(self._callbacks)})"
