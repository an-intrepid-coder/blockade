from random import shuffle, randint, choice

def roll3d6() -> list:
    rolls = [randint(1, 6) for x in range(3)]
    rolls.sort()
    return rolls

# NOTE: Specific rolls may use more/less dice, or take
#       more modifiers, at some point.

def roll_asw_encounter(danger_points, mods=[]) -> int:
    return sum(roll3d6()) - (2 + min(danger_points, 3) + sum(mods))

def roll_shipping_encounter(traffic_points, mods=[]) -> int:
    return sum(roll3d6()) - (2 + traffic_points + sum(mods))

def roll_large_encounter(traffic_points, mods=[]) -> bool:
    return sum(roll3d6()) - (2 + traffic_points + sum(mods)) <= 0

def roll_sub_encounter(traffic_points, mods=[]) -> bool:
    return sum(roll3d6()) - (2 + traffic_points + sum(mods)) <= 0

def roll_heavy_escort_encounter(traffic_points, mods=[]) -> bool:
    return sum(roll3d6()) - (2 + traffic_points + sum(mods)) <= 0

def roll_offmap_asw_encounter(traffic_points, mods=[]) -> bool:
    return sum(roll3d6()) - (2 + traffic_points + sum(mods)) <= 0

def roll_neutrals_encounter(traffic_points, mods=[]) -> bool:
    return sum(roll3d6()) - (2 + traffic_points + sum(mods)) <= 0

def roll_torpedo_damage() -> int:
    return sum(roll3d6())

def roll_missile_damage() -> int:
    return sum(roll3d6())

def roll_for_acc_degradation() -> int:
    return sum(roll3d6()) // 2

def roll_for_acc_upgrade() -> int:
    return sum(roll3d6()) // 2

def roll_for_front_change(mods) -> int:
    return sum(roll3d6()) <= 6 + sum(mods)

# Similar to the way skill checks work in GURPS.
def roll_skill_check(entity, skill, mods=[]) -> int:
    return sum(roll3d6()) - (entity.skills[skill] + sum(mods))

# Similar to a regular skill contest in GURPS
def roll_skill_contest(entity_a, entity_b, skill_a, skill_b, mods_a=[], mods_b=[]) -> dict:
    while True:  
        roll_a = roll_skill_check(entity_a, skill_a, mods_a)
        roll_b = roll_skill_check(entity_b, skill_b, mods_b)
        if roll_a <= 0 and roll_b > 0:
            return {"entity": entity_a, "skill": skill_a, "roll": roll_a}
        elif roll_b <= 0 and roll_a > 0:
            return {"entity": entity_b, "skill": skill_b, "roll": roll_b}
        elif roll_a < roll_b:
            return {"entity": entity_a, "skill": skill_a, "roll": roll_a}
        elif roll_b < roll_a:
            return {"entity": entity_b, "skill": skill_b, "roll": roll_b}

