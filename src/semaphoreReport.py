import pydash as _
from lib.tsm import getTsmClients
from datetime import datetime, timedelta


def calculateSummaryLine(responses, isDB):
    validCategories = ['Completed', 'Started', 'Missed', 'Failed']

    def filterDBs(row):
        node = _.lower_case(row['node'])
        return ('SQL' in node or 'TDP' in node or 'DB2' in node or 'exchange' in node) and row['status'] in validCategories

    def filterFSs(row):
        node = _.lower_case(row['node'])
        return not ('SQL' in node or 'TDP' in node or 'DB2' in node or 'exchange' in node) and row['status'] in validCategories

    if isDB:
        filteredResults = _.filter_(responses, filterDBs)
    else:
        filteredResults = _.filter_(responses, filterFSs)

    resultsGropedByStatus = _.group_by(filteredResults, 'status')
    return [
        str(len(resultsGropedByStatus.get('Started', []))),
        str(len(resultsGropedByStatus.get('Completed', []))),
        str(len(resultsGropedByStatus.get('Missed', [])) +
            len(resultsGropedByStatus.get('Failed', [])))
    ]


def removeInvalidRows(row):
    scheduleName = _.lower_case(row.schedule)
    nodeName = _.lower_case(row.node)
    scheduleIsNotLogOrQa = not ('qa' in scheduleName or 'log' in scheduleName)
    nodeIsNotVcenter = not 'vcenter_dm' in nodeName
    nodeIsNotLgOrSMD = not (_.ends_with('_lg', nodeName) or _.ends_with(
        '_s', nodeName) or _.ends_with('_d', nodeName) or _.ends_with('_m', nodeName))
    return scheduleIsNotLogOrQa and nodeIsNotLgOrSMD and nodeIsNotVcenter


def removeDuplicates(table):
    nodesSeen = []
    NO_DIFFERENCE = 0
    for row in table:
        currentNodeName = row["node"]
        rowIndexAlreadySeen = _.find_index(
            nodesSeen, {"node": currentNodeName})
        if rowIndexAlreadySeen:
            currentDate = datetime(row["start"], '%d.%m.%Y %H:%M:%S')
            nodeSeenDate = datetime(
                nodesSeen[rowIndexAlreadySeen]["start"], '%d.%m.%Y %H:%M:%S')
            currentRowIsNewer = timedelta.total_seconds(
                currentDate-nodeSeenDate) > NO_DIFFERENCE
            if currentRowIsNewer:
                nodesSeen.pop(rowIndexAlreadySeen)
                nodesSeen.append(row)
        else:
            nodesSeen.append(currentDate)


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

tsmCommandOptions = {
    'begind': '-1',
    'begint': '18:00'
}
results = {}
tsmClients = getTsmClients()
for endTime in endTimeList:
    responses = []
    for tsmClient in tsmClients:
        print('-------------------------------------------------')
        print('We will retrive the events from 18:00 to {}'.format(endTime))
        if endTime == endTimeList[FIRST_HOUR_RANGE]:
            _.set_(tsmCommandOptions, 'endd', '-1')
        else:
            _.set_(tsmCommandOptions, 'endd', 'today')
        _.set_(tsmCommandOptions, 'endt', endTime)
        rawResponse = tsmClient.runQueryEvent(**tsmCommandOptions)
        rawResponseFiltered = _.filter_(rawResponse, removeInvalidRows)
        rawResponseFilteredWithoutDuplicates = removeDuplicates(
            rawResponseFiltered)
        responses = _.concat(responses, rawResponseFilteredWithoutDuplicates)
    _.set_(results, endTime, responses)

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
