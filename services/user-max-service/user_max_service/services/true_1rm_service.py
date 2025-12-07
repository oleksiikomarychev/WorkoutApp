def calculate_true_1rm(user_max):
    if user_max.true_1rm:
        return user_max.true_1rm
    if user_max.rep_max and user_max.rep_max > 0:
        return user_max.max_weight * (1 + user_max.rep_max / 30.0)
    return user_max.max_weight
