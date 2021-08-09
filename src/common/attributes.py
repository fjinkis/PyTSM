
def getRequired(object, path, pop=False):
    if pop:
        value = object.pop(path)
    else:
        value = object.get(path)
    if not value:
        raise Exception('{} was not found and it is required'.format(path))

    return value
