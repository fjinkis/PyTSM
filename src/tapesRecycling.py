from lib.tsm import getTsmClients
from common.config import getConfig
from common.attributes import getRequired
import pydash as _

config = getConfig('../config/fullTapes.yaml', failRaises=True)
tsmClients = getTsmClients()
DEFAULT_MAX_TAPES_NUMBER = 6
MIN_PCT_UTILIZATION = 81
MAX_PCT_UTILIZATION = 35
for tsmClient in tsmClients:
    print('------------------------------------------')
    print('We are getting info from {} ({})'.format(
        tsmClient.name, tsmClient.ip))
    tapesMaxNumber = config.get('tapesMaxNumber', DEFAULT_MAX_TAPES_NUMBER)
    libraries = getRequired(config, 'libraries')
    response = tsmClient.getFullTapes(libraries, config.get(
        'MIN_PCT_UTILIZATION', MIN_PCT_UTILIZATION))

    # Unmount
    tapesGrupedByLibrary = _.group_by(response, 'library')
    for library, tapes in tapesGrupedByLibrary.items():
        print('')
        print('Unmount the following {} tapes'.format(library))
        print(
            '\n'.join(_.map_(tapes, 'volume')[-tapesMaxNumber:]))

    print('')
    # Mount/MoveData
    response = tsmClient.getEmptyTapes(libraries, config.get(
        'MAX_PCT_UTILIZATION', MAX_PCT_UTILIZATION))
    for action, actionResponse in response.items():
        tapesGrupedByLibrary = _.group_by(actionResponse, 'library')
        for library, tapes in tapesGrupedByLibrary.items():
            print('')
            print('{} the following {} tapes'.format(action, library))
            print(
                '\n'.join(_.map_(tapes, 'volume')[:tapesMaxNumber]))
