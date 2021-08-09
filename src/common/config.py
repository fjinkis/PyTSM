from yaml import safe_load


def getConfig(yamlFile):
    config = None
    with open(yamlFile) as configFile:
        config = safe_load(configFile)

    return config
