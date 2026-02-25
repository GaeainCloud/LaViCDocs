from typing import List, Dict, Any, Optional, Tuple
import math
from schemas.audit_report import AuditSection, AuditIssue
from schemas.agent_data import ScenarioData, AgentInstance
from simulation.dynamics.kinematics import Kinematics

class PhysicsProbe:
    """
    物理法则探针 (PhysicsAuditor)
    基于牛顿力学和现代军事/工业常识的“通用仿真世界模型”进行审计。
    遵循四大公理：运动学、空间排他性、能量资源守恒、因果时序。
    """
    
    # --- 物理极限常量表 (Reference Limits) ---
    # 单位转换: 
    # 1 knot = 0.514444 m/s
    # 1 Mach = 340.3 m/s (海平面标准大气压)
    # 1 km/h = 0.277778 m/s
    
    ENTITY_LIMITS = {
        "ship": {
            "max_speed": 35 * 0.514444, # ~18 m/s
            "max_g": 0.5,
            "ammo_capacity": 96,
            "max_range": 10000000.0, # 10000km
            "max_endurance": 30 * 24 * 3600, # 30 days
            "stall_speed": 0.0,
            "min_alt": -10.0, # Allow small draft
            "max_alt": 10.0,  # Strictly surface
            "type_keywords": ["ship", "destroyer", "frigate", "corvette", "carrier", "驱逐舰", "护卫舰", "航母"]
        },
        "aircraft": {
            "max_speed": 2.5 * 340.3, # ~850 m/s
            "max_g": 9.0,
            "ammo_capacity": 12,
            "max_range": 2000000.0, # 2000km
            "max_endurance": 6 * 3600, # 6 hours
            "stall_speed": 60.0, # ~216 km/h
            "min_alt": 0.0,
            "max_alt": 20000.0, # 20km ceiling
            "type_keywords": ["aircraft", "fighter", "bomber", "uav", "战斗机", "轰炸机", "无人机"]
        },
        "hypersonic_missile": {
            "max_speed": 20.0 * 340.3, # ~6800 m/s (Mach 20)
            "max_g": 50.0,
            "ammo_capacity": 0, 
            "max_range": 3000000.0, # 3000km
            "max_endurance": 3600, # 1 hour
            "stall_speed": 0.0, # Ballistic
            "min_alt": 0.0,
            "max_alt": 1000000.0, # Space capable
            "type_keywords": ["df-15", "sm-3", "sm3", "df-17", "hypersonic", "ballistic", "东风", "标准三型"]
        },
        "missile": {
            "max_speed": 10.0 * 340.3, # ~3400 m/s
            "max_g": 30.0,
            "ammo_capacity": 0, # 自杀式
            "max_range": 500000.0, # 500km
            "max_endurance": 1800, # 30 mins
            "stall_speed": 0.0,
            "min_alt": 0.0,
            "max_alt": 30000.0,
            "type_keywords": ["missile", "torpedo", "weapon", "导弹", "鱼雷"]
        },
        "ground": {
            "max_speed": 120 / 3.6, # ~33 m/s
            "max_g": 0.8,
            "ammo_capacity": 40,
            "max_range": 600000.0, # 600km
            "max_endurance": 24 * 3600, # 24 hours
            "stall_speed": 0.0,
            "min_alt": 0.0,
            "max_alt": 5000.0, # Terrain limit
            "type_keywords": ["tank", "vehicle", "artillery", "launcher", "坦克", "战车", "发射车"]
        },
        "human": {
            "max_speed": 15 * 0.277778, # ~4.2 m/s
            "max_g": 3.0,
            "ammo_capacity": 300,
            "max_range": 50000.0, # 50km
            "max_endurance": 8 * 3600, # 8 hours
            "stall_speed": 0.0,
            "min_alt": 0.0,
            "max_alt": 5000.0,
            "type_keywords": ["human", "soldier", "infantry", "士兵", "步兵"]
        },
        "default": {
            "max_speed": 340.3, # 默认 1 Mach
            "max_g": 5.0,
            "ammo_capacity": 100,
            "max_range": 1000000.0,
            "max_endurance": 24 * 3600,
            "stall_speed": 0.0,
            "min_alt": -1000.0,
            "max_alt": 100000.0
        }
    }

    def run(self, data: ScenarioData) -> AuditSection:
        issues = []
        status = "PASS"
        
        for entity in data.agentInstances:
            entity_issues = []
            
            # 0. 识别实体类型
            entity_type_name, limits = self._identify_entity_type(entity)
            
            # Task 1: 轨迹与机动性审计
            traj_issues, traj_stats = self._audit_trajectory(entity, limits)
            entity_issues.extend(traj_issues)
            
            # Task 2: 传感器与环境审计
            sensor_issues, sensor_stats = self._audit_sensors(entity, data)
            entity_issues.extend(sensor_issues)

            # Task 2.5: 环境与空间限制审计
            env_issues, env_stats = self._audit_environment(entity, limits)
            entity_issues.extend(env_issues)
            
            # Task 3: 资源逻辑审计
            res_issues, res_stats = self._audit_resources(entity, limits)
            entity_issues.extend(res_issues)
            
            issues.extend(entity_issues)
            
            # Combine all stats for reporting
            full_stats = {
                # L1: Kinematics
                "max_speed": traj_stats.get("max_speed_obs", 0.0),
                "max_g": traj_stats.get("max_g_obs", 0.0),
                "stall_warnings": traj_stats.get("stall_warnings", 0),
                "teleport_count": traj_stats.get("teleport_count", 0),
                
                # L2: Environment
                "min_alt": env_stats.get("min_alt_obs", 0.0),
                "max_alt": env_stats.get("max_alt_obs", 0.0),
                "domain_violations": env_stats.get("domain_violations", 0),
                "terrain_violations": env_stats.get("terrain_violations", 0),
                "los_violations": sensor_stats.get("los_violations", 0),
                
                # L3: Resources
                "max_range": res_stats.get("max_range_obs", 0.0),
                "max_endurance": res_stats.get("max_endurance_obs", 0.0),
                "ammo_used": res_stats.get("ammo_used", 0),
                "payload_issues": res_stats.get("payload_issues", 0),
                
                "limits": limits
            }
            
            # Serialize stats into JSON string for the summary message
            import json
            summary_json = json.dumps(full_stats)
            
            # The summary message will act as a carrier for the data
            summary_msg = f"JSON_DATA:{summary_json}"
            
            if not entity_issues:
                issues.append(AuditIssue(
                    severity="INFO",
                    code="PHY_SUMMARY_PASS",
                    message=summary_msg,
                    entity_id=f"{entity.instanceName} ({entity.agentName})"
                ))
            else:
                issues.append(AuditIssue(
                    severity="INFO",
                    code="PHY_SUMMARY_FAIL",
                    message=summary_msg,
                    entity_id=f"{entity.instanceName} ({entity.agentName})"
                ))
            
        # Determine status
        has_critical = any(i.severity in ["CRITICAL", "ERROR", "FAIL"] for i in issues)
        has_warning = any(i.severity in ["WARNING", "WARN"] for i in issues)
        
        if has_critical:
            status = "FAIL"
        elif has_warning:
            status = "WARN"

        return AuditSection(name="Physics Consistency", status=status, issues=issues)

    def _identify_entity_type(self, entity: AgentInstance) -> Tuple[str, Dict[str, Any]]:
        """根据 agentType 和 agentDesc 推断实体物理属性"""
        text = (f"{entity.agentType} {entity.agentDesc} {entity.instanceName} {entity.agentName} {entity.agentKeyword}").lower()
        
        # Priority order for checking: Check containers (ground/ship) before contents (missiles)
        priority = ["ship", "ground", "aircraft", "hypersonic_missile", "missile", "human"]
        
        for key in priority:
            limit_data = self.ENTITY_LIMITS.get(key)
            if not limit_data: continue
            
            for kw in limit_data["type_keywords"]:
                if kw in text:
                    return key, limit_data
        
        return "default", self.ENTITY_LIMITS["default"]

    def _audit_trajectory(self, entity: AgentInstance, limits: Dict[str, Any]) -> Tuple[List[AuditIssue], Dict[str, float]]:
        issues = []
        stats = {
            "max_speed_obs": 0.0, 
            "min_speed_obs": 999999.0,
            "max_g_obs": 0.0,
            "teleport_count": 0,
            "stall_warnings": 0
        }
        
        # 1. 扁平化所有 waypoints 并按时间排序
        waypoints = []
        for group in entity.waypoints:
            for wp in group.wps:
                # 假设 wpsCore 格式: [lon, lat, alt, val1, time, ...]
                if len(wp.wpsCore) >= 5:
                    t = wp.wpsCore[4]
                    pos = (wp.wpsCore[0], wp.wpsCore[1], wp.wpsCore[2])
                    waypoints.append({"time": t, "pos": pos})
                elif len(wp.wpsCore) == 4:
                    pass 
        
        waypoints.sort(key=lambda x: x["time"])
        
        # 2. 遍历检查
        total_dist = 0.0
        
        for i in range(len(waypoints) - 1):
            curr = waypoints[i]
            next_wp = waypoints[i+1]
            
            dt = next_wp["time"] - curr["time"]
            dist_m = self._geo_distance(curr["pos"], next_wp["pos"])
            total_dist += dist_m
            
            if dt <= 0:
                if dist_m > 1.0: # 允许1米内的误差
                    stats["teleport_count"] += 1
                    issues.append(AuditIssue(
                        severity="CRITICAL",
                        code="PHY_KIN_INSTANT_TELEPORT",
                        message=f"Entity {entity.instanceName} teleported {dist_m:.1f}m in {dt:.3f}s.",
                        location=f"Time:{curr['time']}",
                        entity_id=entity.instanceName,
                        time_step=f"T+{curr['time']}s",
                        evidence=f"Pos A -> Pos B in {dt}s."
                    ))
                continue
                
            speed = dist_m / dt
            
            # Update stats
            if speed > stats["max_speed_obs"]:
                stats["max_speed_obs"] = speed
            if speed < stats["min_speed_obs"]:
                stats["min_speed_obs"] = speed
            
            max_speed = limits["max_speed"]
            stall_speed = limits.get("stall_speed", 0.0)
            
            # Speed Checks
            if speed > max_speed * 1.5: # 严重超速
                issues.append(AuditIssue(
                    severity="CRITICAL",
                    code="PHY_KIN_SPEED_LIMIT",
                    message=f"CRITICAL Speed Violation. Calculated: {speed:.1f} m/s, Limit: {max_speed:.1f} m/s.",
                    location=f"Entity:{entity.instanceName} Time:{curr['time']}->{next_wp['time']}",
                    entity_id=entity.instanceName,
                    time_step=f"T+{curr['time']}s",
                    evidence=f"Traveled {dist_m:.1f}m in {dt:.1f}s."
                ))
            elif speed > max_speed * 1.1: # 轻微超速
                 issues.append(AuditIssue(
                    severity="WARNING",
                    code="PHY_KIN_SPEED_WARN",
                    message=f"Speed Warning. Calculated: {speed:.1f} m/s, Limit: {max_speed:.1f} m/s.",
                    location=f"Entity:{entity.instanceName} Time:{curr['time']}->{next_wp['time']}",
                    entity_id=entity.instanceName,
                    time_step=f"T+{curr['time']}s",
                    evidence=f"Traveled {dist_m:.1f}m in {dt:.1f}s."
                ))
            
            # Stall Speed Check (Stall if speed < stall_speed and altitude > 10m)
            avg_alt = (curr["pos"][2] + next_wp["pos"][2]) / 2.0
            if stall_speed > 0 and speed < stall_speed and avg_alt > 10.0:
                 stats["stall_warnings"] += 1
                 issues.append(AuditIssue(
                    severity="CRITICAL",
                    code="PHY_KIN_STALL",
                    message=f"Stall Warning. Speed {speed:.1f} m/s below stall speed {stall_speed:.1f} m/s at alt {avg_alt:.1f}m.",
                    location=f"Entity:{entity.instanceName} Time:{curr['time']}->{next_wp['time']}",
                    entity_id=entity.instanceName,
                    time_step=f"T+{curr['time']}s",
                    evidence=f"Speed: {speed:.1f} < Stall: {stall_speed:.1f}"
                ))

            # G-Force Checks (需要3个点)
            if i > 0:
                prev = waypoints[i-1]
                v1_vec = self._get_displacement_vector(prev["pos"], curr["pos"])
                v2_vec = self._get_displacement_vector(curr["pos"], next_wp["pos"])
                
                dt_prev = curr["time"] - prev["time"]
                dt_curr = next_wp["time"] - curr["time"]
                
                # Fix: Convert displacement to velocity
                v1_vel = tuple(d / dt_prev for d in v1_vec) if dt_prev > 1e-6 else v1_vec
                v2_vel = tuple(d / dt_curr for d in v2_vec) if dt_curr > 1e-6 else v2_vec
                
                dt_turn = (dt_prev + dt_curr) / 2.0
                g_force = Kinematics.calculate_turn_g_force(v1_vel, v2_vel, dt_turn)
                
                if g_force > stats["max_g_obs"]:
                    stats["max_g_obs"] = g_force
                
                max_g = limits["max_g"]
                
                if g_force > max_g * 1.5:
                    issues.append(AuditIssue(
                        severity="CRITICAL",
                        code="PHY_KIN_G_FORCE",
                        message=f"CRITICAL G-Force Violation. Calculated: {g_force:.1f}G, Limit: {max_g}G.",
                        location=f"Entity:{entity.instanceName} Time:{curr['time']}",
                        entity_id=entity.instanceName,
                        time_step=f"T+{curr['time']}s",
                        evidence=f"Turn G-Force: {g_force:.1f}G."
                    ))
                elif g_force > max_g:
                    issues.append(AuditIssue(
                        severity="WARNING",
                        code="PHY_KIN_G_FORCE_WARN",
                        message=f"G-Force Warning. Calculated: {g_force:.1f}G, Limit: {max_g}G.",
                        location=f"Entity:{entity.instanceName} Time:{curr['time']}",
                        entity_id=entity.instanceName,
                        time_step=f"T+{curr['time']}s",
                        evidence=f"Turn G-Force: {g_force:.1f}G."
                    ))

        # Check total range (Fuel check)
        max_range = limits.get("max_range", 1e9)
        if total_dist > max_range:
            issues.append(AuditIssue(
                severity="WARNING",
                code="PHY_RES_FUEL_RANGE",
                message=f"Range/Fuel Warning. Total distance {total_dist/1000:.1f}km exceeds limit {max_range/1000:.1f}km.",
                location=f"Entity:{entity.instanceName}",
                entity_id=entity.instanceName,
                time_step="N/A",
                evidence=f"Total Dist: {total_dist/1000:.1f}km"
            ))

        if stats["min_speed_obs"] == 999999.0:
            stats["min_speed_obs"] = 0.0
            
        return issues, stats

    def _audit_sensors(self, entity: AgentInstance, data: ScenarioData) -> Tuple[List[AuditIssue], Dict[str, float]]:
        issues = []
        stats = {"los_violations": 0}
        
        for action in entity.axns:
            if action.get("name") in ["Detect", "Attack", "Lock"]:
                target_id = action.get("targetId")
                time = action.get("time")
                if not target_id or time is None:
                    continue
                
                target = next((e for e in data.agentInstances if e.agentInstId == target_id or e.instanceName == target_id), None)
                if not target:
                    continue
                
                my_pos = self._get_pos_at_time(entity, time)
                target_pos = self._get_pos_at_time(target, time)
                
                if not my_pos or not target_pos:
                    continue
                
                h_sensor = my_pos[2]
                h_target = target_pos[2]
                
                max_los = Kinematics.calculate_horizon_distance(h_sensor, h_target)
                actual_dist = self._geo_distance(my_pos, target_pos)
                
                if actual_dist > max_los:
                     stats["los_violations"] += 1
                     issues.append(AuditIssue(
                        severity="CRITICAL",
                        code="PHY_ENV_HORIZON",
                        message=f"Target beyond horizon. Dist: {actual_dist/1000:.1f}km, MaxLOS: {max_los/1000:.1f}km.",
                        location=f"Entity:{entity.instanceName} Action:{action.get('name')} Time:{time}",
                        entity_id=entity.instanceName,
                        time_step=f"T+{time}s",
                        evidence=f"Dist: {actual_dist/1000:.1f}km > MaxLOS: {max_los/1000:.1f}km"
                    ))
        
        return issues, stats

    def _audit_environment(self, entity: AgentInstance, limits: Dict[str, Any]) -> Tuple[List[AuditIssue], Dict[str, float]]:
        issues = []
        stats = {
            "min_alt_obs": 999999.0, 
            "max_alt_obs": -999999.0,
            "domain_violations": 0,
            "terrain_violations": 0
        }
        
        min_alt = limits.get("min_alt", -1000.0)
        max_alt = limits.get("max_alt", 100000.0)
        
        # Check all waypoints for altitude violation
        for group in entity.waypoints:
            for wp in group.wps:
                # wpsCore: [lon, lat, alt, ...]
                if len(wp.wpsCore) >= 3:
                    alt = wp.wpsCore[2]
                    time_val = wp.wpsCore[4] if len(wp.wpsCore) >= 5 else 0
                    
                    if alt > stats["max_alt_obs"]: stats["max_alt_obs"] = alt
                    if alt < stats["min_alt_obs"]: stats["min_alt_obs"] = alt
                    
                    if alt > max_alt:
                        stats["domain_violations"] += 1
                        issues.append(AuditIssue(
                            severity="CRITICAL",
                            code="PHY_ENV_CEILING",
                            message=f"Altitude violation. Alt {alt:.1f}m > Max Ceiling {max_alt:.1f}m.",
                            location=f"Entity:{entity.instanceName} Time:{time_val}",
                            entity_id=entity.instanceName,
                            time_step=f"T+{time_val}s",
                            evidence=f"Alt: {alt:.1f}m"
                        ))
                    elif alt < min_alt:
                         stats["domain_violations"] += 1
                         stats["terrain_violations"] += 1
                         issues.append(AuditIssue(
                            severity="CRITICAL",
                            code="PHY_ENV_DEPTH",
                            message=f"Depth/Terrain violation. Alt {alt:.1f}m < Min Alt {min_alt:.1f}m.",
                            location=f"Entity:{entity.instanceName} Time:{time_val}",
                            entity_id=entity.instanceName,
                            time_step=f"T+{time_val}s",
                            evidence=f"Alt: {alt:.1f}m"
                        ))
        
        if stats["min_alt_obs"] == 999999.0: stats["min_alt_obs"] = 0.0
        if stats["max_alt_obs"] == -999999.0: stats["max_alt_obs"] = 0.0
        
        return issues, stats

    def _audit_resources(self, entity: AgentInstance, limits: Dict[str, Any]) -> Tuple[List[AuditIssue], Dict[str, float]]:
        issues = []
        stats = {
            "max_range_obs": 0.0, 
            "max_endurance_obs": 0.0,
            "ammo_used": 0,
            "payload_issues": 0
        }
        
        # Ammo Check
        for action in entity.axns:
            if action.get("name") in ["Launch", "Fire", "Shoot"]:
                stats["ammo_used"] += 1
                
        if stats["ammo_used"] > limits["ammo_capacity"]:
            issues.append(AuditIssue(
                severity="CRITICAL",
                code="PHY_RES_AMMO_DEPLETION",
                message=f"Ammo depletion. Attempted to fire {stats['ammo_used']} times, capacity is {limits['ammo_capacity']}.",
                location=f"Entity:{entity.instanceName}",
                entity_id=entity.instanceName,
                time_step="N/A",
                evidence=f"Launch Count: {stats['ammo_used']} > Capacity: {limits['ammo_capacity']}"
            ))

        # Calculate Total Distance and Total Time
        waypoints = []
        for group in entity.waypoints:
            for wp in group.wps:
                if len(wp.wpsCore) >= 5:
                    t = wp.wpsCore[4]
                    pos = (wp.wpsCore[0], wp.wpsCore[1], wp.wpsCore[2])
                    waypoints.append({"time": t, "pos": pos})
        
        waypoints.sort(key=lambda x: x["time"])
        
        if not waypoints:
            return issues, stats
            
        total_time = waypoints[-1]["time"] - waypoints[0]["time"]
        total_dist = 0.0
        for i in range(len(waypoints) - 1):
            total_dist += self._geo_distance(waypoints[i]["pos"], waypoints[i+1]["pos"])
            
        stats["max_range_obs"] = total_dist
        stats["max_endurance_obs"] = total_time
        
        # Check against limits
        if total_dist > limits["max_range"]:
            issues.append(AuditIssue(
                severity="WARNING",
                code="PHY_RES_RANGE",
                message=f"Range Limit Exceeded. {total_dist/1000:.1f}km > {limits['max_range']/1000:.1f}km.",
                entity_id=entity.instanceName,
                evidence=f"Total Range: {total_dist:.1f}m"
            ))
            
        if total_time > limits["max_endurance"]:
             issues.append(AuditIssue(
                severity="WARNING",
                code="PHY_RES_ENDURANCE",
                message=f"Endurance Limit Exceeded. {total_time/3600:.1f}h > {limits['max_endurance']/3600:.1f}h.",
                entity_id=entity.instanceName,
                evidence=f"Total Time: {total_time:.1f}s"
            ))
            
        return issues, stats

    def _geo_distance(self, p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> float:
        lon1, lat1, _ = p1
        lon2, lat2, _ = p2
        R = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        d_horizontal = R * c
        d_vertical = abs(p1[2] - p2[2])
        return math.sqrt(d_horizontal**2 + d_vertical**2)

    def _get_displacement_vector(self, p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> Tuple[float, float, float]:
        lon1, lat1, alt1 = p1
        lon2, lat2, alt2 = p2
        lat_m_per_deg = 111132.0
        avg_lat_rad = math.radians((lat1 + lat2) / 2.0)
        lon_m_per_deg = 111132.0 * math.cos(avg_lat_rad)
        dx = (lon2 - lon1) * lon_m_per_deg
        dy = (lat2 - lat1) * lat_m_per_deg
        dz = alt2 - alt1
        return (dx, dy, dz)

    def _get_pos_at_time(self, entity: AgentInstance, t: float) -> Optional[Tuple[float, float, float]]:
        waypoints = []
        for group in entity.waypoints:
            for wp in group.wps:
                if len(wp.wpsCore) >= 5:
                    waypoints.append((wp.wpsCore[4], wp.wpsCore[0], wp.wpsCore[1], wp.wpsCore[2]))
                elif len(wp.wpsCore) == 4:
                    pass
        waypoints.sort()
        if not waypoints: return None
        if len(waypoints) == 1:
            if abs(t - waypoints[0][0]) < 1e-3: return (waypoints[0][1], waypoints[0][2], waypoints[0][3])
            return None
        if t < waypoints[0][0] or t > waypoints[-1][0]:
            if abs(t - waypoints[0][0]) < 1e-3: return (waypoints[0][1], waypoints[0][2], waypoints[0][3])
            if abs(t - waypoints[-1][0]) < 1e-3: return (waypoints[-1][1], waypoints[-1][2], waypoints[-1][3])
            return None
        for i in range(len(waypoints) - 1):
            t1, x1, y1, z1 = waypoints[i]
            t2, x2, y2, z2 = waypoints[i+1]
            if t1 <= t <= t2:
                if t2 == t1: return (x1, y1, z1)
                factor = (t - t1) / (t2 - t1)
                return (x1 + (x2 - x1) * factor, y1 + (y2 - y1) * factor, z1 + (z2 - z1) * factor)
        return None
