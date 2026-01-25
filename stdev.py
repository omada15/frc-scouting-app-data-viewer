import math

def standard_deviation(numbers):
    if not numbers:
        return 0
    mean = sum(numbers) / len(numbers)
    squared_diffs = [(x - mean) ** 2 for x in numbers]
    variance = sum(squared_diffs) / len(numbers)
    return math.sqrt(variance)