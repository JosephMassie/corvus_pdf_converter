def toTitle(string: str):
    words = string.lower().split(' ')
    
    words = list(map(lambda word: word[0].upper() + word[1:], words))

    return ' '.join(words)

def toKey(string: str):
    return string.lower().strip().replace(" ", "_")

def linesToContent(lines: list[str]):
    return ' '.join(lines).strip()

def strToKeys(string: str):
    return string.split(".")

def keysToStr(keys: list[str]):
    return ".".join(keys)