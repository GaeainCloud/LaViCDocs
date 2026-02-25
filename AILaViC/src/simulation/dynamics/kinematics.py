import math
from typing import Tuple, Optional

class Kinematics:
    """
    轻量级运动学计算工具，用于快速验证物理合理性。
    """
    
    @staticmethod
    def calculate_distance_3d(p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
        """计算三维欧氏距离 (米)"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    @staticmethod
    def estimate_travel_time(distance: float, speed: float) -> float:
        """估算移动时间 (秒)"""
        if speed <= 0:
            return float('inf')
        return distance / speed

    @staticmethod
    def validate_speed(current_speed: float, max_speed: float, tolerance: float = 0.1) -> bool:
        """验证速度是否超限"""
        return current_speed <= max_speed * (1 + tolerance)

    @staticmethod
    def extrapolate_position(
        start_pos: Tuple[float, float, float], 
        velocity_vector: Tuple[float, float, float], 
        time_delta: float
    ) -> Tuple[float, float, float]:
        """
        线性外推位置
        pos = start_pos + v * t
        """
        return (
            start_pos[0] + velocity_vector[0] * time_delta,
            start_pos[1] + velocity_vector[1] * time_delta,
            start_pos[2] + velocity_vector[2] * time_delta
        )

    @staticmethod
    def calculate_turn_g_force(
        v1: Tuple[float, float, float], 
        v2: Tuple[float, float, float], 
        time_delta: float
    ) -> float:
        """
        计算转弯过载 (G-Force)
        基于角速度估算: a = v * omega = v * (d_theta / dt)
        """
        if time_delta <= 1e-6:
            return 0.0
            
        # 计算速度模长
        speed1 = math.sqrt(sum(x*x for x in v1))
        speed2 = math.sqrt(sum(x*x for x in v2))
        avg_speed = (speed1 + speed2) / 2.0
        
        if avg_speed < 1e-3:
            return 0.0

        # 计算夹角 (使用点积)
        dot_product = sum(a*b for a, b in zip(v1, v2))
        cos_theta = dot_product / (speed1 * speed2)
        # 限制在 [-1, 1] 避免浮点误差
        cos_theta = max(-1.0, min(1.0, cos_theta))
        theta = math.acos(cos_theta) # 弧度
        
        # 向心加速度 a = v * (theta / t)
        acc_centripetal = avg_speed * (theta / time_delta)
        
        # 转换为 G 值 (1G = 9.8 m/s^2)
        return acc_centripetal / 9.80665

    @staticmethod
    def calculate_horizon_distance(h_sensor: float, h_target: float) -> float:
        """
        计算雷达视距 (考虑大气折射)
        公式: D (km) = 4.12 * (sqrt(H1) + sqrt(H2))
        输入高度单位: 米
        返回距离单位: 米 (为了统一单位，这里将公式结果 km 转换为 m)
        """
        # 避免负高度
        h1 = max(0.0, h_sensor)
        h2 = max(0.0, h_target)
        
        dist_km = 4.12 * (math.sqrt(h1) + math.sqrt(h2))
        return dist_km * 1000.0
