from lib.tsm import getTsmClients
import pydash as _


tsmClients = getTsmClients()
for tsmClient in tsmClients:
    tapes = tsmClient.getFullTapes()
    tapesGrupedByLibrary = _.group_by(tapes, 'library')
    NUMBER_OF_TAPES = 6
    print('')
    print('Remove the following LT05 tapes')
    print(
        '\n'.join(_.map_(tapesGrupedByLibrary['LIB_LTO5'][-NUMBER_OF_TAPES:], 'volume')))
    print('Remove the following LT06 tapes')
    print(
        '\n'.join(_.map_(tapesGrupedByLibrary['LIB_LTO6'][-NUMBER_OF_TAPES:], 'volume')))
