# Расчет true_1rm: если значение уже задано, используем его. Иначе, если известно rep_max (количество повторений с max_weight),
# рассчитываем по формуле Эпли, которая аппроксимирует 1ПМ для малого числа повторений (<=10). 
# Если rep_max неизвестен, используем max_weight как 1ПМ.
def calculate_true_1rm(user_max):
    if user_max.true_1rm:
        return user_max.true_1rm
    if user_max.rep_max and user_max.rep_max > 0:
        return user_max.max_weight * (1 + user_max.rep_max / 30.0)
    return user_max.max_weight
