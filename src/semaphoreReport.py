from yaml import safe_load
import pydash as _
from tsm import TsmClient


def getRequired(object, path, pop=False):
    if pop:
        value = object.pop(path)
    else:
        value = object.get(path)
    if not value:
        raise Exception('{} was not found and it is required'.format(path))

    return value


def createEach(tsmDetails):
    ip = getRequired(tsmDetails, 'ip', pop=True)
    port = tsmDetails.pop('port', '1500')
    return TsmClient(ip, port=port, **tsmDetails)


def calculateSummaryLine(responses, isDB):
    validCategories = ['Completed', 'Started', 'Missed', 'Failed']
    if isDB:
        filteredResults = _.filter_(
            responses, lambda row: 'TDP' in row['node'] and 'LOG' not in row['schedule'] and row['status'] in validCategories)
    else:
        filteredResults = _.filter_(
            responses, lambda row: 'TDP' not in row['node'] and 'LOG' not in row['schedule'] and row['status'] in validCategories)

    resultsGropedByStatus = _.group_by(filteredResults, 'status')
    return [
        str(len(resultsGropedByStatus.get('Started', []))),
        str(len(resultsGropedByStatus.get('Completed', []))),
        str(len(resultsGropedByStatus.get('Missed', [])) +
            len(resultsGropedByStatus.get('Failed', [])))
    ]


config = None
with open('tsmReporterConfig.yaml') as configFile:
    config = safe_load(configFile)

FIRST_HOUR_RANGE = 0
LAST_HOUR_RANGE = -1
endTimeList = [
    '22:00',
    '00:01',
    '02:00',
    '04:00',
    '06:00',
    '07:45'
]
tsmServers = _.map_(config.get('tsmServers', []), createEach)
tsmCommandOptions = {
    'begind': '-1',
    'begint': '18:00'
}
results = {}
for endTime in endTimeList:
    responses = []
    for tsmClient in tsmServers:
        print('-------------------------------------------------')
        print('We will retrive the events from 18:00 to {}'.format(endTime))
        if endTime == endTimeList[FIRST_HOUR_RANGE]:
            _.set_(tsmCommandOptions, 'endd', 'today')
            _.set_(tsmCommandOptions, 'endt', endTime)
        else:
            _.set_(tsmCommandOptions, 'endd', '-1')
            _.set_(tsmCommandOptions, 'endt', endTime)
        response = tsmClient.runQueryEvent(**tsmCommandOptions)
        responses = _.concat(responses, response)
    _.set_(results, endTime, response)

summary = []
for endTime, responses in results.items():
    if endTime == endTimeList[LAST_HOUR_RANGE]:
        nodesInExecution = _.map_(_.filter_(
            responses, lambda row: 'LOG' not in row['schedule'] and row['status'] == 'Started'), 'node')
        print('')
        print('')
        print('There are ({}) in execution:'.format(len(nodesInExecution)))
        print('\n'.join(nodesInExecution))

    dbResult = calculateSummaryLine(responses, True)
    fsResult = calculateSummaryLine(responses, False)
    summaryLine = '{} {}'.format('  '.join(dbResult), ' '.join(fsResult))
    summary.append(summaryLine)

print('')
print('')
print('This is the semaphore table:')
print('\n'.join(summary))
