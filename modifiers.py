from alert_level import AlertLevel
from euclidean import manhattan_distance

# situational roll modifiers

# applies to situations where passive sonar is detecting a torpedo
noisy_torpedo_bonus_to_passive_sonar_detection = 2

# "stealth" skill is much less useful against active sonar
stealth_asonar_penalty = -3

# returns 0 if piloting against an ENGAGED opponent.
# otherwise, a huge bonus.
def pilot_torpedo_alert_mod(alert_level) -> int:
    if alert_level == AlertLevel.ENGAGED: return 0
    return -4

# Returns a penalty to passive psonar detection if target is in fast mode
# and a bonus or penalty based on observer speed
def moving_psonar_mod(observer, target) -> int:
    mod = 0
    if observer.momentum == 0:
        mod += 2
    elif observer.speed_mode == "fast":
        mod += -2
    if target.momentum == 0:
        mod += -2
    elif target.speed_mode == "fast":
        mod += 2
    return mod

def sonar_distance_mod(observer, target) -> int:
    # NOTE: This may be a non-linear function down the road
    return -manhattan_distance(observer.xy_tuple, target.xy_tuple)

