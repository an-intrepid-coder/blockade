# Returns first instance of a thing in a list, or else None
def first(fn, ls):
    result = list(filter(fn, ls))
    if len(result) > 0:
        return result[0]
    return None

# Apply a function to every element of a list
def apply(fn, ls):
    for element in ls:
        fn(element)

# Recursively flatten a multi-dimensional list
def flatten(ls) -> list:
    lists = []
    new_ls = []
    for element in ls:
        if isinstance(element, list):
            lists.append(element)
        else:
            new_ls.append(element)

    while len(lists) > 0:
        element = lists[0]
        for sub_element in element:
            if isinstance(sub_element, list):
                lists.append(sub_element)
            else:
                new_ls.append(sub_element)
        lists.remove(element)

    return new_ls
 
