import pydash as _
from os import environ, chdir, getcwd
from platform import system
from ipaddress import ip_address
from ping3 import ping
from subprocess import run, check_output, TimeoutExpired
from common.attributes import getRequired
from common.config import getConfig


def getTsmClients():
    def createEach(tsmDetails):
        ip = getRequired(tsmDetails, 'ip', pop=True)
        port = tsmDetails.pop('port', '1500')
        return TsmClient(ip, port=port, **tsmDetails)

    config = getConfig('../config/tsmConfig.yaml')
    return _.map_(config.get('tsmServers', []), createEach)


class TsmClient:

    def __init__(self, ip, **configs):
        try:
            ip_address(ip)
        except:
            raise TypeError(
                'We was expecting a valid IP address. {} given'.format(ip))

        self.__setConsts()
        self.ip = ip
        self.port = configs.pop('port', self.DEFAULT_TSM_PORT)
        self.user = configs.pop('username', environ.get(
            self.DEFAULT_ENV_USERNAME_VARIABLE))
        self.password = configs.pop('password', environ.get(
            self.DEFAULT_ENV_PASSWORD_VARIABLE))
        self.__pwd = getcwd()
        self.__binPath = configs.pop('binPath', self.__getDsmadmcBinaryPath())
        if _.some([self.port, self.user, self.password], _.is_none):
            raise TypeError('We need the username and password. By default this program takes the environment variables {} and {} but it seems like they were not defined'.format(
                self.DEFAULT_ENV_USERNAME_VARIABLE, self.DEFAULT_ENV_PASSWORD_VARIABLE))

        for config, value in configs.items():
            _.set_(self, config, value)

        _.set_(self.BASE_DSMADMC_OPTIONS, 'id', self.user)
        _.set_(self.BASE_DSMADMC_OPTIONS, 'password', self.password)
        _.set_(self.BASE_DSMADMC_OPTIONS, 'TCPServeraddress', self.ip)
        _.set_(self.BASE_DSMADMC_OPTIONS, 'tcpport', self.port)

    def __setConsts(self):
        self.DEFAULT_ENV_USERNAME_VARIABLE = 'TSM_USERNAME'
        self.DEFAULT_ENV_PASSWORD_VARIABLE = 'TSM_PASSWORD'
        self.DEFAULT_TSM_PORT = '1500'
        self.BASE_DSMADMC_OPTIONS = {
            'noconf': True,
            'comma': True,
            'dataonly': 'yes'
        }
        self.TIMEOUT_IN_SECONDS = 300
        self.WINDOWS_SYSTEMS = ['Windows']
        self.MAC_SYSTEMS = ['Darwin']
        self.UNIX_SYSTEMS = ['SunOS']

    def __getDsmadmcBinaryPath(self):
        os = system()

        # Linux
        binPath = '/usr/bin/dsmadmc'
        if (os in self.WINDOWS_SYSTEMS):
            binPath = 'C:/Program Files/Tivoli/TSM/baclient'
        elif (os in self.MAC_SYSTEMS):
            binPath = '/usr/bin/dsmadmc'
        elif (os in self.UNIX_SYSTEMS):
            binPath = '/usr/bin/dsmadmc'

        return binPath

    def __getDsmadmcOptionsString(self, value, key):
        return '-{}'.format(key) if _.is_boolean(value) else '-{}={}'.format(key, value)

    def __getTsmOptionsString(self, value, key):
        return '{}'.format(key) if _.is_boolean(value) else '{}={}'.format(key, value)

    def __getFunctionToTransformRowToObject(self, headers):
        def transformRowToObject(row):
            objectToReturn = {}
            values = row.split(',')
            for head in headers:
                value = values.pop(0)
                _.set_(objectToReturn, head, value)

            return objectToReturn

        return transformRowToObject

    def run(self, command, failRaises=True, outfile=None, **options):
        if not command or not _.is_string(command):
            raise ValueError(
                'Remember that we need to run a command. This must be an string')

        runResponse = None

        dsmadmcOptions = self.BASE_DSMADMC_OPTIONS
        outfileProperty = {'outfile': outfile} if outfile else {}
        _.assign(dsmadmcOptions, outfileProperty, options)
        dsmadmcOptions = _.map_(dsmadmcOptions, self.__getDsmadmcOptionsString)

        currentdsmadmcCommand = 'dsmadmc {} "{}"'.format(
            ' '.join(dsmadmcOptions), command)

        try:
            chdir(self.__binPath)
            print('We are attempting to run: "{}"'.format(command))
            if outfile:
                run(currentdsmadmcCommand, shell=True,
                    timeout=self.TIMEOUT_IN_SECONDS)
            else:
                runResponse = check_output(currentdsmadmcCommand,
                                           shell=True, encoding='utf-8')
            chdir(self.__pwd)
        except FileNotFoundError as err:
            message = 'Check where is the executable dsmadmc file. It seems like is not in {}'.format(
                self.__binPath)
            raise FileNotFoundError(message)
        except Exception as err:
            print(err)
            isAlive = ping(dest_addr=self.ip)
            if not isAlive:
                message = 'Bad news, the TSM server did not respond and we are not reaching with a simple ping. Maybe it is a network issue'
                if failRaises:
                    raise TimeoutError(message)
            else:
                message = 'Bad news, the command did not run successfully. This is the message: {}'.format(
                    err)
                if failRaises:
                    raise Exception(message)
            print(message)

        return runResponse

    def runQueryEvent(self, domain='*', schedule='*', failRaises=True, outfile=None, **options):
        response = None
        currentOptions = _.map_(options, self.__getTsmOptionsString)
        command = 'query event {} {} {}'.format(
            domain, schedule, ' '.join(currentOptions))
        runResponse = self.run(command, failRaises=failRaises, outfile=outfile)
        if runResponse:
            headers = ['scheduled_at', 'start', 'schedule', 'node', 'status']
            transformFunction = self.__getFunctionToTransformRowToObject(
                headers)
            response = _.map_(
                runResponse.splitlines(), lambda row: transformFunction(row))

        return response

    def runQueryLibVolume(self, library='*', volume='*', failRaises=True, outfile=None):
        response = None
        command = 'query libvolume {} {}'.format(library, volume)
        runResponse = self.run(command, failRaises=failRaises, outfile=outfile)
        if runResponse:
            headers = ['library', 'volume', 'status',
                       'owner', 'last_use', 'home' 'device']
            transformFunction = self.__getFunctionToTransformRowToObject(
                headers)
            response = _.map_(
                runResponse.splitlines(), lambda row: transformFunction(row))

        return response

    def runQueryVolume(self, volume='*', failRaises=True, outfile=None, **options):
        response = None
        currentOptions = _.map_(options, self.__getTsmOptionsString)
        command = 'query volume {} {}'.format(
            volume, ' '.join(currentOptions))
        runResponse = self.run(command, failRaises=failRaises, outfile=outfile)
        if runResponse:
            headers = ['name', 'pool', 'device_class',
                       'capacity', 'utilization', 'status']
            transformFunction = self.__getFunctionToTransformRowToObject(
                headers)
            response = _.map_(
                runResponse.splitlines(), lambda row: transformFunction(row))

        return response

    def runQueryProcess(self, process='', failRaises=True, outfile=None, **options):
        response = None
        currentOptions = _.map_(options, self.__getTsmOptionsString)
        command = 'query process {} {}'.format(
            process, ' '.join(currentOptions))
        runResponse = self.run(command, failRaises=failRaises, outfile=outfile)
        if runResponse:
            headers = ['process', 'description', 'status']
            transformFunction = self.__getFunctionToTransformRowToObject(
                headers)
            response = _.map_(
                runResponse.splitlines(), lambda row: transformFunction(row))

        return response

    def getFullTapes(self, libraries, failRaises=True, outfile=None):
        if not libraries:
            raise ValueError(
                'Remember that we need the library list to look up for full tapes')
        response = None
        librariesCondition = 'libvolumes.library_name LIKE {}'.format(
            ' OR libvolumes.library_name LIKE '.join(_.map_(libraries, lambda value: "'%{}%'".format(value))))
        command = "SELECT library_name, volumes.volume_name, pct_utilized FROM volumes INNER JOIN media ON volumes.volume_name=media.volume_name INNER JOIN libvolumes ON volumes.volume_name=libvolumes.volume_name WHERE media.state LIKE '%Mountable in%' AND ({}) AND volumes.status='FULL' AND pct_utilized>81 ORDER BY library_name, pct_utilized".format(
            librariesCondition)
        runResponse = self.run(command, failRaises=failRaises, outfile=outfile)
        headers = ['library', 'volume', 'utilized']
        transformFunction = self.__getFunctionToTransformRowToObject(
            headers)
        response = _.map_(
            runResponse.splitlines(), lambda row: transformFunction(row))

        return response
