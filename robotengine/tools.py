import math
from typing import List, Tuple

def hex2str(data) -> str:
    """
    将十六进制数据转换为字符串

        :param data: 十六进制数据
        :return: 字符串
    """
    if isinstance(data, int):
        return f'{data:02X}'
    return ' '.join(f'{byte:02X}' for byte in data)

def warning(msg) -> None:
    """
    打印警告信息

        :param msg: 警告信息
    """
    msg = f"[WARNING] {msg}"
    print(f"\033[33m{msg}\033[0m")

def error(msg) -> None:
    """
    打印错误信息，并退出程序

        :param msg: 错误信息
    """
    msg = f"[ERROR] {msg}"
    print(f"\033[31m{msg}\033[0m")
    exit(1)

def info(msg) -> None:
    """
    打印信息

        :param msg: 信息内容
    """

    msg = f"[INFO] {msg}"
    print(f"\033[32m{msg}\033[0m")

def get_variable_name(obj) -> str:
    """
    获取变量名

        :param obj: 变量对象
        :return: 变量名
    """
    for name, val in globals().items():
        if val is obj:
            return name
    return None

def vector_length(x: float, y: float) -> float:
    """ 
    计算向量的长度 
    
        :param x: 向量的 x 分量
        :param y: 向量的 y 分量
        :return: 向量的长度
    """
    return math.sqrt(x * x + y * y)

def vector_angle(x: float, y: float) -> float:
    """ 
    计算向量的角度（弧度制） 
    
        :param x: 向量的 x 分量
        :param y: 向量的 y 分量
        :return: 向量的角度（弧度制）
    """
    return math.atan2(y, x)

def find_closest_vectors(angle: float, base_angles: List[float]) -> Tuple[int, int]:
    """ 
    判断角度在哪两个基向量之间 
    
        param angle: 角度（弧度制）
        param base_angles: 基向量的角度列表（弧度制）
        return: 两个基向量的索引
    """
    if angle < 0:
        angle += 2 * math.pi
    for i in range(4):
        next_i = (i + 1) % 4
        if base_angles[i] <= angle < base_angles[next_i]:
            return i, next_i
    # 如果在最边界情况下
    return 3, 0

def near(a: float, b: float, threshold: float=1.0) -> bool:
    """ 
    判断两个浮点数是否接近 
    
        :param a: 第一个浮点数
        :param b: 第二个浮点数
        :param threshold: 阈值，默认为1.0
        :return: 如果两个浮点数接近，则返回 True，否则返回 False
    """
    return abs(a - b) < threshold

def compute_vector_projection(x, y, base_angles: List[float]) -> List[float]:
    """
    计算一个向量在一组基向量(数量为4)上的投影系数。假设我们有一个向量 (x, y) 和一组基向量 (basis1, basis2, basis3, basis4)。
    我们的目标是找到一个线性组合，使得：

        vector = coeff1 * basis1 + coeff2 * basis2 + coeff3 * basis3 + coeff4 * basis4

    其中 coeff1、coeff2、coeff3 和 coeff4 是我们要求解的系数。
    我们可以使用矩阵的方法来解决这个问题。假设我们有一个矩阵 A 和一个向量 b：

        A = [basis1_x, basis1_y]
            [basis2_x, basis2_y]
            [basis3_x, basis3_y]
            [basis4_x, basis4_y]

        b = [x, y]

    我们的目标是找到一个向量 coeffs，使得：

        coeffs = A^-1 * b

    但是由于矩阵 A 不一定可逆，我们可以使用矩阵的伪逆来代替：

        coeffs = A^+ * b

    其中 A^+ 是矩阵 A 的伪逆。

    现在，我们已经得到了一个向量 coeffs，其中 coeffs[i] 表示向量 (x, y) 在第 i 个基向量上的投影系数。
    
    注意：
        1. 此函数仅适用于基向量数量为4的情况。
        2. 此函数仅适用于二维向量。
        3. 此函数仅适用于基向量的角度为45度的情况。
        4. 此函数仅适用于基向量的长度为1的情况。

        :param x: 向量 x 分量
        :param y: 向量 y 分量
        :param base_angles: 基向量角度列表，长度为4
        :return: 投影系数列表，长度为4
    """

    angle = vector_angle(x, y)
    index1, index2 = find_closest_vectors(angle, base_angles)

    # 计算两个基向量的坐标
    basis1_x = math.cos(base_angles[index1])
    basis1_y = math.sin(base_angles[index1])
    basis2_x = math.cos(base_angles[index2])
    basis2_y = math.sin(base_angles[index2])

    # 构造线性方程 A * coeffs = b
    A = [
        [basis1_x, basis2_x],
        [basis1_y, basis2_y]
    ]
    b = [x, y]

    # 计算行列式
    det = A[0][0] * A[1][1] - A[0][1] * A[1][0]

    # 使用克拉梅尔法则求解系数
    det1 = b[0] * A[1][1] - b[1] * A[0][1]
    det2 = A[0][0] * b[1] - A[1][0] * b[0]

    coeff1 = det1 / det
    coeff2 = det2 / det

    # 准备结果系数数组，长度为 4
    coefficients = [0] * 4
    coefficients[index1] = coeff1
    coefficients[index2] = coeff2

    return coefficients