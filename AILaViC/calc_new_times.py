
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# 1. Conflict Dolphin (UAV)
# Waypoints:
# 0: 120.1525882, 24.7052622 (Time=0)
# 1: 120.0337292, 23.9776796 (Time=10)
# 2: 120.0270213, 23.5728136 (Time=20)
dist1 = haversine_distance(24.7052622, 120.1525882, 23.9776796, 120.0337292)
dist2 = haversine_distance(23.9776796, 120.0337292, 23.5728136, 120.0270213)

# Limit: 850 m/s
time1 = dist1 / 800.0 # Use 800 m/s as target speed
time2 = dist2 / 800.0 

print(f"Conflict Dolphin:")
print(f"  Dist1: {dist1:.1f} m, Required Time: {time1:.1f} s")
print(f"  Dist2: {dist2:.1f} m, Required Time: {time2:.1f} s")

# 2. Majestic Penguin (KJ-500)
# Waypoints:
# 0: 120.1525882, 24.7052622 (Time=0)
# 1: 119.9302105, 24.0687084 (Time=10)
# 2: 119.893372, 23.3690671 (Time=20)
dist_kj1 = haversine_distance(24.7052622, 120.1525882, 24.0687084, 119.9302105)
dist_kj2 = haversine_distance(24.0687084, 119.9302105, 23.3690671, 119.893372)

# Limit: 340 m/s. Let's aim for 200 m/s (cruising)
time_kj1 = dist_kj1 / 200.0
time_kj2 = dist_kj2 / 200.0

print(f"Majestic Penguin:")
print(f"  Dist1: {dist_kj1:.1f} m, Required Time: {time_kj1:.1f} s")
print(f"  Dist2: {dist_kj2:.1f} m, Required Time: {time_kj2:.1f} s")
