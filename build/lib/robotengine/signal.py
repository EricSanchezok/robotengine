"""

Signal 是 robotengine 实现节点间通信和异步调用的基础。

"""

from typing import Callable
from robotengine.tools import warning, get_variable_name
import threading

class Signal:
    """ 信号类 """
    def __init__(self, *param_types):
        """ 
        初始化信号，需要指定信号的参数类型以保证信号触发时的类型安全，例如：

            signal = Signal(int, float, str)

        如果是复杂的类型，则要使用 python 库中的 typing 模块，例如：

            from typing import List, Dict

            signal = Signal(List[int], Dict[str, float])
        """
        self._callbacks = []
        self._param_types = param_types  # 存储信号的预期参数类型

    def connect(self, callback: Callable):
        """ 
        连接信号，需要指定一个回调函数 

            :param callback: 回调函数

        注意，回调函数的参数类型必须与信号的参数类型一致，否则会抛出 TypeError 异常。
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)
        else:
            warning(f"{callback} 已经存在，请勿重复添加")

    def disconnect(self, callback: Callable):
        """ 
        断开信号，需要指定一个回调函数 
        
            :param callback: 回调函数
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)
        else:
            warning(f"{callback} 不存在，请勿重复删除")

    def emit(self, *args, **kwargs):
        """ 
        触发信号，需要指定信号的参数 

        注意，信号触发后执行的回调函数是异步的，不会阻塞主线程。
        """
        if len(args) != len(self._param_types):
            raise TypeError(f"Expected {len(self._param_types)} arguments, but got {len(args)}")

        for expected_type, actual_arg in zip(self._param_types, args):
            if not isinstance(actual_arg, expected_type):
                raise TypeError(f"Expected argument of type {expected_type}, but got {type(actual_arg)}")
        
        v_name = get_variable_name(self)
        if v_name is None:
            thread_name = "SignalThread"
        else:
            thread_name = v_name + "SignalThread"

        new_thread = threading.Thread(target=self._emit, args=args, kwargs=kwargs, daemon=True, name=thread_name)
        new_thread.start()
    
    def _emit(self, *args, **kwargs):
        for callback in self._callbacks:
            callback(*args, **kwargs)

    def __repr__(self):
        return f"Signal(connected callbacks={len(self._callbacks)})"
