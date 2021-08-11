import pydash as _
import os
import ping3
import subprocess
from platform import system
from ipaddress import ip_address
from common.attributes import getRequired
from common.config import getConfig


def getTsmClients(configFile=None):
    def createEach(tsmDetails):
        ip = getRequired(tsmDetails, 'ip', pop=True)
        port = tsmDetails.pop('port', '1500')
        return TsmClient(ip, port=port, **tsmDetails)

    config = configFile if configFile else getConfig(
        '../config/tsmConfig.yaml')
    return _.map_(config.get('tsmServers', []), createEach)


class TsmClient:

    DEFAULT_ENV_USERNAME_VARIABLE = 'TSM_USERNAME'
    DEFAULT_ENV_PASSWORD_VARIABLE = 'TSM_PASSWORD'
    DEFAULT_TSM_PORT = '1500'
    TIMEOUT_IN_SECONDS = 300
    WINDOWS_SYSTEMS = ['Windows']
    MAC_SYSTEMS = ['Darwin']
    UNIX_SYSTEMS = ['SunOS']

    def __init__(self, ip, **configs):
        try:
            ip_address(ip)
        except:
            raise TypeError(
                'We was expecting a valid IP address. {} given'.format(ip))

        self.ip = ip
        self.port = configs.pop('port', self.DEFAULT_TSM_PORT)
        self.user = configs.pop('username', os.environ.get(
            self.DEFAULT_ENV_USERNAME_VARIABLE))
        self.__password = configs.pop('password', os.environ.get(
            self.DEFAULT_ENV_PASSWORD_VARIABLE))
        self.__pwd = os.getcwd()
        self.binPath = configs.pop('binPath', self.__getDsmadmcBinaryPath())
        if _.some([self.port, self.user, self.__password], _.is_none):
            raise TypeError('We need the username and password. By default this program takes the environment variables {} and {} but it seems like they were not defined'.format(
                self.DEFAULT_ENV_USERNAME_VARIABLE, self.DEFAULT_ENV_PASSWORD_VARIABLE))

        for config, value in configs.items():
            _.set_(self, config, value)

        self.__baseDsmadmcOptions = {
            'noconf': True,
            'comma': True,
            'dataonly': 'yes'
        }
        _.set_(self.__baseDsmadmcOptions, 'id', self.user)
        _.set_(self.__baseDsmadmcOptions, 'password', self.__password)
        _.set_(self.__baseDsmadmcOptions, 'TCPServeraddress', self.ip)
        _.set_(self.__baseDsmadmcOptions, 'tcpport', self.port)

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

    def __getResponseAsObjects(self, headers, runResponse):
        FIRST_ELEMENT = 0

        def transformRowToObject(row):
            objectToReturn = {}
            values = row.split(',')
            for head in headers:
                value = values.pop(FIRST_ELEMENT)
                _.set_(objectToReturn, head, value)

            return objectToReturn

        return _.map_(
            runResponse.splitlines(), lambda row: transformRowToObject(row))

    def run(self, command, failRaises=True, outfile=None, **options):
        if not command or not _.is_string(command):
            raise ValueError(
                'Remember that we need to run a command. This must be an string')

        runResponse = None

        dsmadmcOptions = self.__baseDsmadmcOptions
        outfileProperty = {'outfile': outfile} if outfile else {}
        _.assign(dsmadmcOptions, outfileProperty, options)
        dsmadmcOptions = _.map_(dsmadmcOptions, self.__getDsmadmcOptionsString)

        currentdsmadmcCommand = 'dsmadmc {} "{}"'.format(
            ' '.join(dsmadmcOptions), command)

        try:
            os.chdir(self.binPath)
            print('We are attempting to run: "{}"'.format(command))
            if outfile:
                subprocess.run(currentdsmadmcCommand, shell=True,
                               timeout=self.TIMEOUT_IN_SECONDS)
            else:
                runResponse = subprocess.check_output(currentdsmadmcCommand,
                                                      shell=True, encoding='utf-8')
            os.chdir(self.__pwd)
        except FileNotFoundError as err:
            message = 'Check where is the executable dsmadmc file. It seems like is not in {}'.format(
                self.binPath)
            raise FileNotFoundError(message)
        except Exception as err:
            print(err)
            isAlive = ping3.ping(dest_addr=self.ip)
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
            response = self.__getResponseAsObjects(headers, runResponse)

        return response

    def runQueryLibVolume(self, library='*', volume='*', failRaises=True, outfile=None):
        response = None
        command = 'query libvolume {} {}'.format(library, volume)
        runResponse = self.run(command, failRaises=failRaises, outfile=outfile)
        if runResponse:
            headers = ['library', 'volume', 'status',
                       'owner', 'last_use', 'home' 'device']
            response = self.__getResponseAsObjects(headers, runResponse)

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
            response = self.__getResponseAsObjects(headers, runResponse)

        return response

    def runQueryProcess(self, process='', failRaises=True, outfile=None, **options):
        response = None
        currentOptions = _.map_(options, self.__getTsmOptionsString)
        command = 'query process {} {}'.format(
            process, ' '.join(currentOptions))
        runResponse = self.run(command, failRaises=failRaises, outfile=outfile)
        if runResponse:
            headers = ['process', 'description', 'status']
            response = self.__getResponseAsObjects(headers, runResponse)

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
        if runResponse:
            headers = ['library', 'volume', 'utilized']
            response = self.__getResponseAsObjects(headers, runResponse)

        return response
