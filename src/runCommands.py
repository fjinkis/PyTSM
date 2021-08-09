from lib.tsm import getTsmClients
from common.config import getConfig


tsmClients = getTsmClients()
runCommandsConfig = getConfig(
    '../config/runCommandsConfig.yaml').get('tsmServers', [])
for tsmClient in tsmClients:
    for tsmCommand in runCommandsConfig.get('tsmCommands', []):
        response = tsmClient.run(tsmCommand)
        print(response)
