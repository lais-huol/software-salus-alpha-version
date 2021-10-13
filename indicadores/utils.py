from Levenshtein import distance


def levenshtein_closest(string, multi, force_upper=False):
    if force_upper:
        string = string.upper()
    processed = [(item, distance(string, item.upper() if force_upper else item)) for item in multi]
    processed.sort(key=lambda x: x[1])
    return processed
