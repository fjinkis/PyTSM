from lib.tsm import getTsmClients
from common.config import getConfig
from common.attributes import getRequired
import pydash as _

config = getConfig('../config/fullTapes.yaml')
tsmClients = getTsmClients()
DEFAULT_MAX_TAPES_NUMBER = 6
for tsmClient in tsmClients:
    print('------------------------------------------')
    print('We are getting info from {}'.format(tsmClient.ip))
    tapes = tsmClient.getFullTapes()
    tapesGrupedByLibrary = _.group_by(tapes, 'library')
    NUMBER_OF_TAPES = getRequired(
        config, 'tapesMaxNumber') if config else DEFAULT_MAX_TAPES_NUMBER
    print('')
    print('Remove the following LT05 tapes')
    print(
        '\n'.join(_.map_(tapesGrupedByLibrary['LIB_LTO5'][-NUMBER_OF_TAPES:], 'volume')))
    print('Remove the following LT06 tapes')
    print(
        '\n'.join(_.map_(tapesGrupedByLibrary['LIB_LTO6'][-NUMBER_OF_TAPES:], 'volume')))
