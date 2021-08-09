from yaml import safe_load


def getConfig(yamlFile, failRaises=False):
    config = None
    try:
        with open(yamlFile) as configFile:
            config = safe_load(configFile)
    except Exception as err:
        if failRaises:
            raise err

    return config
