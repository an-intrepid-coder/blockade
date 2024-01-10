from random import shuffle, randint, choice

def roll3d6() -> list:
    rolls = [randint(1, 6) for x in range(3)]
    rolls.sort()
    return rolls

def roll_for_initiative() -> int:
    return sum(roll3d6())

def roll_torpedo_damage() -> int:
    return sum(roll3d6())

def roll_skill_check(entity, skill, mods=[]) -> int:
    return sum(roll3d6()) - (entity.skills[skill] + sum(mods))

# Similar to a regular skill contest in GURPS
def roll_skill_contest(entity_a, entity_b, skill_a, skill_b, mods_a=[], mods_b=[]) -> dict:
    # NOTE: duck-typing to avoid circular reference
    while True:  # TODO: test
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

