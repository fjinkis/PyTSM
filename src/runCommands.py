from lib.tsm import getTsmClients
from common.config import getConfig


tsmClients = getTsmClients()
runCommandsConfig = getConfig(
    '../config/runCommandsConfig.yaml')
for tsmClient in tsmClients:
    print('------------------------------------------')
    print('We are getting info from {}'.format(tsmClient.ip))
    for tsmCommand in runCommandsConfig.get('tsmCommands', []):
        response = tsmClient.run(tsmCommand)
        print(response)
