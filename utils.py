import random

from constants import RECOMMENDED_LIFT_OTW


# Function to format pace to minutes per mile from seconds
def format_pace(sec):
    m = int(sec // 60)
    s = int(sec % 60)
    return f"{m}:{s:02d}/mi"


# Function to get recommended lift of the week based on week number
def get_recommended_lift_of_the_week(week_num: int):
    rng = random.Random(week_num)  # deterministic seed per week
    recommendations = {}
    for key in ("legs", "core", "upper body"):
        options = RECOMMENDED_LIFT_OTW.get(key, [])
        recommendations[key] = rng.choice(options) if options else None
    return recommendations
