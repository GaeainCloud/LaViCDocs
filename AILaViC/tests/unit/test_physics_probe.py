
import sys
import os
import unittest
from typing import List

# 添加 src 到路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from agents.auditor.probes.physics import PhysicsProbe
from schemas.agent_data import ScenarioData, AgentInstance, WaypointGroup, WaypointItem

class TestPhysicsProbe(unittest.TestCase):
    def setUp(self):
        self.probe = PhysicsProbe()
        
    def create_agent(self, name: str, atype: str, waypoints_data: List[List[float]], actions: List[dict] = None) -> AgentInstance:
        """
        waypoints_data: [[lon, lat, alt, time], ...]
        """
        wps_items = []
        for wd in waypoints_data:
            wps_items.append(WaypointItem(wpsCore=wd))
            
        group = WaypointGroup(wpsKeyword="Route1", wps=wps_items)
        
        return AgentInstance(
            agentInstId=name,
            agentKey=name,
            instanceName=name,
            agentType=atype,
            waypoints=[group],
            axns=actions or []
        )

    def test_speed_limit(self):
        """测试超速检查"""
        # 创建一个超速的驱逐舰 (Max 35 knots ~= 18 m/s)
        # 1秒内移动 100米 (100 m/s)
        agent = self.create_agent(
            name="DDG-100", 
            atype="destroyer",
            waypoints_data=[
                [120.0, 30.0, 0.0, 0.0],
                [120.0, 30.0009, 0.0, 1.0] # lat 变化 0.0009度 ~= 100米
            ]
        )
        data = ScenarioData(agentInstances=[agent])
        result = self.probe.run(data)
        
        self.assertEqual(result.status, "FAIL")
        found = any("exceeded physical speed limit" in i.message for i in result.issues)
        self.assertTrue(found, "Should detect speed limit violation")

    def test_g_force(self):
        """测试过载检查"""
        # 战斗机 (Max 9G)
        # 极速转弯: 速度 300m/s, 1秒转 90度 (角速度 1.57 rad/s)
        # a = 300 * 1.57 = 471 m/s^2 ~= 48G >> 9G
        
        # 构造三个点形成直角转弯
        # P1 (0,0), P2 (300m, 0), P3 (300m, 300m)
        # 时间间隔 1s
        # 0.0027度 lat ~= 300m
        agent = self.create_agent(
            name="F-16",
            atype="fighter",
            waypoints_data=[
                [120.0, 30.0, 1000.0, 0.0],
                [120.003, 30.0, 1000.0, 1.0], # 向东 300m
                [120.003, 30.0027, 1000.0, 2.0] # 向北 300m
            ]
        )
        data = ScenarioData(agentInstances=[agent])
        result = self.probe.run(data)
        
        self.assertEqual(result.status, "FAIL")
        found = any("Exceeded structural G-Force limit" in i.message for i in result.issues)
        self.assertTrue(found, f"Should detect G-Force violation. Issues: {result.issues}")

    def test_teleport(self):
        """测试瞬移"""
        agent = self.create_agent(
            name="Ghost",
            atype="human",
            waypoints_data=[
                [120.0, 30.0, 0.0, 0.0],
                [121.0, 31.0, 0.0, 0.0] # 瞬间移动很远
            ]
        )
        data = ScenarioData(agentInstances=[agent])
        result = self.probe.run(data)
        
        found = any("teleported" in i.message for i in result.issues)
        self.assertTrue(found)

    def test_horizon_limit(self):
        """测试视距限制"""
        # 雷达高度 10m, 目标高度 10m -> 视距 ~4.12 * (3.16+3.16) = 26km
        # 设置距离 50km
        
        agent = self.create_agent(
            name="RadarShip",
            atype="ship",
            waypoints_data=[[120.0, 30.0, 10.0, 100.0]],
            actions=[{"name": "Lock", "targetId": "TargetShip", "time": 100.0}]
        )
        
        target = self.create_agent(
            name="TargetShip",
            atype="ship",
            waypoints_data=[[120.5, 30.0, 10.0, 100.0]] # 0.5度 lon ~= 48km
        )
        
        data = ScenarioData(agentInstances=[agent, target])
        result = self.probe.run(data)
        
        found = any("Target beyond horizon" in i.message for i in result.issues)
        self.assertTrue(found)

    def test_ammo_limit(self):
        """测试弹药限制"""
        # 坦克 40发
        actions = [{"name": "Fire", "time": i} for i in range(41)]
        agent = self.create_agent(
            name="M1A2",
            atype="tank",
            waypoints_data=[[120.0, 30.0, 0.0, 0.0]],
            actions=actions
        )
        
        data = ScenarioData(agentInstances=[agent])
        result = self.probe.run(data)
        
        found = any("Ammo depletion" in i.message for i in result.issues)
        self.assertTrue(found)

if __name__ == '__main__':
    unittest.main()
