# 仿真审计报告 (Simulation Audit Report)

**生成时间**: 2026-02-12 16:51:50
**文件源**: `想定_防空反导-v1.60.9-修复版.zip`
**总体状态**: 🔴 FAIL

## 1. 摘要 (Summary)
Audit completed. Overall status: FAIL

## 2. 详细审计结果 (Detailed Results)

### INTEGRITY
**状态**: 🟢 PASS

> 无违规项 (No issues found)

### PHYSICS
**状态**: 🟢 PASS

| 级别 | 代码 | 实体 (Instance/Agent) | 描述 | 证据 |
|---|---|---|---|---|
| 🔵 INFO | `PHY_SUMMARY_PASS` | Conflict Dolphin (网电作战无人机（防空反导想定）) | JSON_DATA:{"max_speed": 790.6571071687466, "max_g": 0.5463323074982941, "stall_warnings": 0, "teleport_count": 0, "min_alt": 1000.0, "max_alt": 1000.0, "domain_violations": 0, "terrain_violations": 0, "los_violations": 0, "max_range": 131996.5013394853, "max_endurance": 170.0, "ammo_used": 0, "payload_issues": 0, "limits": {"max_speed": 850.75, "max_g": 9.0, "ammo_capacity": 12, "max_range": 2000000.0, "max_endurance": 21600, "stall_speed": 60.0, "min_alt": 0.0, "max_alt": 20000.0, "type_keywords": ["aircraft", "fighter", "bomber", "uav", "\u6218\u6597\u673a", "\u8f70\u70b8\u673a", "\u65e0\u4eba\u673a"]}} | `None` |
| 🔵 INFO | `PHY_SUMMARY_PASS` | Majestic Penguin (空警-500（防空反导想定）) | JSON_DATA:{"max_speed": 197.57166560850678, "max_g": 0.01384184237014675, "stall_warnings": 0, "teleport_count": 0, "min_alt": 8000.0, "max_alt": 8000.0, "domain_violations": 0, "terrain_violations": 0, "los_violations": 0, "max_range": 121695.17134906695, "max_endurance": 620.0, "ammo_used": 0, "payload_issues": 0, "limits": {"max_speed": 340.3, "max_g": 5.0, "ammo_capacity": 100, "max_range": 1000000.0, "max_endurance": 86400, "stall_speed": 0.0, "min_alt": -1000.0, "max_alt": 100000.0}} | `None` |
| 🔵 INFO | `PHY_SUMMARY_PASS` | Entrance Teacher (东风-15短程弹道导弹（防空反导想定）) | JSON_DATA:{"max_speed": 2543.4395535435224, "max_g": 0.0, "stall_warnings": 0, "teleport_count": 0, "min_alt": 0.0, "max_alt": 50000.0, "domain_violations": 0, "terrain_violations": 0, "los_violations": 0, "max_range": 269858.9366309677, "max_endurance": 106.1, "ammo_used": 0, "payload_issues": 0, "limits": {"max_speed": 6806.0, "max_g": 50.0, "ammo_capacity": 0, "max_range": 3000000.0, "max_endurance": 3600, "stall_speed": 0.0, "min_alt": 0.0, "max_alt": 1000000.0, "type_keywords": ["df-15", "sm-3", "sm3", "df-17", "hypersonic", "ballistic", "\u4e1c\u98ce", "\u6807\u51c6\u4e09\u578b"]}} | `None` |
| 🔵 INFO | `PHY_SUMMARY_PASS` | Bustling Buzzard (阿利·伯克级驱逐舰（防空反导想定）) | JSON_DATA:{"max_speed": 15.000868935935795, "max_g": 0.0006915636452203556, "stall_warnings": 0, "teleport_count": 0, "min_alt": 0.0, "max_alt": 0.0, "domain_violations": 0, "terrain_violations": 0, "los_violations": 0, "max_range": 308521.2060056948, "max_endurance": 20568.1, "ammo_used": 0, "payload_issues": 0, "limits": {"max_speed": 18.00554, "max_g": 0.5, "ammo_capacity": 96, "max_range": 10000000.0, "max_endurance": 2592000, "stall_speed": 0.0, "min_alt": -10.0, "max_alt": 10.0, "type_keywords": ["ship", "destroyer", "frigate", "corvette", "carrier", "\u9a71\u9010\u8230", "\u62a4\u536b\u8230", "\u822a\u6bcd"]}} | `None` |
| 🔵 INFO | `PHY_SUMMARY_PASS` | Shameful Leopard (标准三型导弹（防空反导想定）) | JSON_DATA:{"max_speed": 4013.2916385376543, "max_g": 0.0, "stall_warnings": 0, "teleport_count": 0, "min_alt": 200.0, "max_alt": 200.0, "domain_violations": 0, "terrain_violations": 0, "los_violations": 0, "max_range": 39330.258057669016, "max_endurance": 9.8, "ammo_used": 0, "payload_issues": 0, "limits": {"max_speed": 6806.0, "max_g": 50.0, "ammo_capacity": 0, "max_range": 3000000.0, "max_endurance": 3600, "stall_speed": 0.0, "min_alt": 0.0, "max_alt": 1000000.0, "type_keywords": ["df-15", "sm-3", "sm3", "df-17", "hypersonic", "ballistic", "\u4e1c\u98ce", "\u6807\u51c6\u4e09\u578b"]}} | `None` |
| 🔵 INFO | `PHY_SUMMARY_PASS` | Daughter Plumber (东风-15短程弹道导弹车（防空反导想定）) | JSON_DATA:{"max_speed": 20.000032860001312, "max_g": 0.0, "stall_warnings": 0, "teleport_count": 0, "min_alt": 0.0, "max_alt": 0.0, "domain_violations": 0, "terrain_violations": 0, "los_violations": 0, "max_range": 265186.4357006154, "max_endurance": 13259.3, "ammo_used": 0, "payload_issues": 0, "limits": {"max_speed": 33.333333333333336, "max_g": 0.8, "ammo_capacity": 40, "max_range": 600000.0, "max_endurance": 86400, "stall_speed": 0.0, "min_alt": 0.0, "max_alt": 5000.0, "type_keywords": ["tank", "vehicle", "artillery", "launcher", "\u5766\u514b", "\u6218\u8f66", "\u53d1\u5c04\u8f66"]}} | `None` |

### LOGIC
**状态**: 🔴 FAIL

| 级别 | 代码 | 实体 (Instance/Agent) | 描述 | 证据 |
|---|---|---|---|---|
| 🟡 WARNING | `CAUSAL_CMD_NO_FEEDBACK` | Majestic Penguin <br> (空警-500（防空反导想定）) | Agent has a commander but no status/feedback variables defined. | `Missing *status/state* in vardefs` |
| 🟡 WARNING | `CAUSAL_PDA_MISSING_INPUT` | Entrance Teacher <br> (东风-15短程弹道导弹（防空反导想定）) | Agent has mission capabilities but no defined sensors (fldmds) or target inputs. | `Missionable: True, Sensors: 0` |
| 🔴 ERROR | `CAUSAL_CMD_ORPHAN` | Entrance Teacher <br> (东风-15短程弹道导弹（防空反导想定）) | Agent refers to non-existent parent ID: 231558595114749999/231558595114750002 | `asmParentPath: 231558595114749999/231558595114750002` |
| 🟡 WARNING | `CAUSAL_CMD_NO_FEEDBACK` | Entrance Teacher <br> (东风-15短程弹道导弹（防空反导想定）) | Agent has a commander but no status/feedback variables defined. | `Missing *status/state* in vardefs` |
| 🟡 WARNING | `CAUSAL_CMD_NO_FEEDBACK` | Bustling Buzzard <br> (阿利·伯克级驱逐舰（防空反导想定）) | Agent has a commander but no status/feedback variables defined. | `Missing *status/state* in vardefs` |
| 🔴 ERROR | `CAUSAL_CMD_ORPHAN` | Shameful Leopard <br> (标准三型导弹（防空反导想定）) | Agent refers to non-existent parent ID: 231558595114750000/231558595114750001 | `asmParentPath: 231558595114750000/231558595114750001` |
| 🟡 WARNING | `CAUSAL_CMD_NO_FEEDBACK` | Shameful Leopard <br> (标准三型导弹（防空反导想定）) | Agent has a commander but no status/feedback variables defined. | `Missing *status/state* in vardefs` |
| 🟡 WARNING | `CAUSAL_PDA_MISSING_INPUT` | Daughter Plumber <br> (东风-15短程弹道导弹车（防空反导想定）) | Agent has mission capabilities but no defined sensors (fldmds) or target inputs. | `Missionable: True, Sensors: 0` |
| 🟡 WARNING | `CAUSAL_CMD_NO_FEEDBACK` | Daughter Plumber <br> (东风-15短程弹道导弹车（防空反导想定）) | Agent has a commander but no status/feedback variables defined. | `Missing *status/state* in vardefs` |

### TACTICS
**状态**: 🟢 PASS

> 无违规项 (No issues found)

### COMPLEXITY
**状态**: 🟢 PASS

> 无违规项 (No issues found)

### SCRIPT
**状态**: 🟢 PASS

> 无违规项 (No issues found)

