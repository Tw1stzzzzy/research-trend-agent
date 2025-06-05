import math

def calculate_score(is_pwcode, stars, days_since_created):
    """
    简单综合打分公式：
      score = 2*is_pwcode + log(stars+1) + 0.5*log(days_since_created+1)
    """
    score = 0.0
    score += 2 * (1 if is_pwcode else 0)
    if stars is not None:
        score += math.log(stars + 1)
    if days_since_created is not None:
        score += 0.5 * math.log(days_since_created + 1)
    return round(score, 2)
