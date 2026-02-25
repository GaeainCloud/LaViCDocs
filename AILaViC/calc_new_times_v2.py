
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Conflict Dolphin
cd_p0 = (24.6203328, 120.5229078)
cd_p1 = (23.9776796, 120.0337292)
cd_p2 = (23.5728136, 120.0270213)

d1 = haversine_distance(*cd_p0, *cd_p1)
d2 = haversine_distance(*cd_p1, *cd_p2)
# Speed limit 850, target 800
t1 = d1 / 800.0
t2 = d2 / 800.0
print(f"CD: D1={d1:.1f}, T1={t1:.1f}, D2={d2:.1f}, T2={t2:.1f}")

# Majestic Penguin
mp_p0 = (24.7052622, 120.1525882)
mp_p1 = (24.0687084, 119.9302105)
mp_p2 = (23.6441499, 119.886538)

md1 = haversine_distance(*mp_p0, *mp_p1)
md2 = haversine_distance(*mp_p1, *mp_p2)
# Speed limit 340, target 200
mt1 = md1 / 200.0
mt2 = md2 / 200.0
print(f"MP: D1={md1:.1f}, T1={mt1:.1f}, D2={md2:.1f}, T2={mt2:.1f}")
