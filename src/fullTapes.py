from lib.tsm import getTsmClients
from common.config import getConfig
from common.attributes import getRequired
import pydash as _

config = getConfig('../config/fullTapes.yaml', failRaises=True)
tsmClients = getTsmClients()
DEFAULT_MAX_TAPES_NUMBER = 6
for tsmClient in tsmClients:
    print('------------------------------------------')
    print('We are getting info from {}'.format(tsmClient.ip))
    tapesMaxNumber = config.get('tapesMaxNumber', DEFAULT_MAX_TAPES_NUMBER)
    libraries = getRequired(config, 'libraries')
    response = tsmClient.getFullTapes(libraries)
    tapesGrupedByLibrary = _.group_by(response, 'library')
    for library, tapes in tapesGrupedByLibrary.items():
        print('')
        print('Remove the following {} tapes'.format(library))
        print(
            '\n'.join(_.map_(tapes, 'volume')[-tapesMaxNumber:]))
