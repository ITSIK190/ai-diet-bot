def calculate_tdee(weight_kg: float, height_cm: int, age: int, gender: str, activity_level: str) -> float:
    if gender.lower() == "male":
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very active": 1.9,
    }
    return bmr * multipliers.get(activity_level, 1.2)


def calculate_goal_calories(weight_kg: float, height_cm: int, age: int, gender: str, activity_level: str, goal_kg: float) -> int:
    tdee = calculate_tdee(weight_kg, height_cm, age, gender, activity_level)
    weight_diff = goal_kg - weight_kg
    weekly_change = weight_diff / 8
    adjustment = weekly_change * 1100
    result = int(round(tdee + adjustment, 0))
    floor = 1500 if gender.lower() == "male" else 1200
    return max(result, floor)
