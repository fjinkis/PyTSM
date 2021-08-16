from re import match
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
    ERROR_MESSAGE_PATTERN = r'(ANE|ANR)\d{4}E'

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
        optionToReturn = ''
        if value:
            optionToReturn = '-{}'.format(key) if _.is_boolean(
                value) else '-{}={}'.format(key, value)

        return optionToReturn

    def __getTsmOptionsString(self, value, key):
        optionToReturn = ''
        if value:
            return '{}'.format(key) if _.is_boolean(value) else '{}={}'.format(key, value)

        return optionToReturn

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

    '''
    Runs a command in TSM
    Parameters:
        command (str) TSM command to run
        failRaises (bool) Determinates if the object will raise an error if the command has an non-cero status code. Default is True
        v (string|None) Determinates if the output will be redirected to a file. Default is None
        options (dict) extra options to define. This param has as many keys as dsmadmc's options and additionaly it could be defined a config key whose dict value will change some behaviors:
            headers->list could be defined to return the response in a dict format
            isAlive->bool to try with a simple ping if the server is alive after an exception

    Returns
        (dict|string|None) command response. It could be None if the outfile option was defined
    '''

    def run(self, command, failRaises=True, outfile=None, **options):
        if not command or not _.is_string(command):
            raise ValueError(
                'Remember that we need to run a command. This must be an string')

        runResponse = None

        dsmadmcOptions = self.__baseDsmadmcOptions
        extraConfig = options.pop('config', None)
        outfileProperty = {'outfile': outfile} if outfile else {}
        _.assign(dsmadmcOptions, outfileProperty, options)
        dsmadmcOptions = _.compact(
            _.map_(dsmadmcOptions, self.__getDsmadmcOptionsString))

        currentdsmadmcCommand = 'dsmadmc {} "{}"'.format(
            ' '.join(dsmadmcOptions), command)

        try:
            os.chdir(self.binPath)
            if extraConfig and extraConfig.get('hide_command'):
                print('We are attempting to run: "{}"'.format(command))
            if outfile:
                subprocess.run(currentdsmadmcCommand, shell=True,
                               timeout=self.TIMEOUT_IN_SECONDS)
            else:
                rawResponse = subprocess.check_output(
                    currentdsmadmcCommand, shell=True)
                runResponse = rawResponse.decode('utf-8', errors='ignore')
                if match(self.ERROR_MESSAGE_PATTERN, runResponse):
                    raise RuntimeError(runResponse)
                if extraConfig:
                    headers = extraConfig.get('headers')
                    if headers:
                        runResponse = self.__getResponseAsObjects(
                            headers, runResponse)
            os.chdir(self.__pwd)
        except FileNotFoundError as err:
            message = 'Check where is the executable dsmadmc file. It seems like is not in {}'.format(
                self.binPath)
            raise FileNotFoundError(message)
        except RuntimeError as err:
            message = 'Bad news, the command did not run successfully. This is the message: {}'.format(
                err)
            print(message)
            if failRaises:
                raise RuntimeError(message)
        except Exception as err:
            message = 'Unfortunately something not expected happened!. This is the message: {}'.format(
                err)
            print(message)
            if extraConfig and extraConfig.get('isAlive'):
                isAlive = ping3.ping(dest_addr=self.ip)
                if not isAlive:
                    message = 'The TSM server did not respond and we are not reaching with a simple ping. Maybe it is a network issue'
                    if failRaises:
                        raise TimeoutError(message)
            if failRaises:
                raise Exception(message)

        return runResponse

    def runQueryEvent(self, domain='*', schedule='*', failRaises=True, outfile=None, **options):
        response = None
        currentOptions = _.compact(_.map_(options, self.__getTsmOptionsString))
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
        currentOptions = _.compact(_.map_(options, self.__getTsmOptionsString))
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
        currentOptions = _.compact(_.map_(options, self.__getTsmOptionsString))
        command = 'query process {} {}'.format(
            process, ' '.join(currentOptions))
        runResponse = self.run(command, failRaises=failRaises, outfile=outfile)
        if runResponse:
            headers = ['process', 'description', 'status']
            response = self.__getResponseAsObjects(headers, runResponse)

        return response

    def getFullTapes(self, libraries, outfile=None):
        if not libraries:
            raise ValueError(
                'Remember that we need the library list to look up for full tapes')
        response = None
        librariesCondition = 'libvolumes.library_name LIKE {}'.format(
            ' OR libvolumes.library_name LIKE '.join(_.map_(libraries, lambda value: "'%{}%'".format(value))))
        command = "SELECT library_name, volumes.volume_name, pct_utilized FROM volumes INNER JOIN media ON volumes.volume_name=media.volume_name INNER JOIN libvolumes ON volumes.volume_name=libvolumes.volume_name WHERE media.state LIKE '%Mountable in%' AND ({}) AND volumes.status='FULL' AND pct_utilized>81 ORDER BY library_name, pct_utilized".format(
            librariesCondition)
        runResponse = self.run(command, failRaises=False, outfile=outfile)
        if runResponse:
            headers = ['library', 'volume', 'utilized']
            response = self.__getResponseAsObjects(headers, runResponse)

        return response

    def getEmptyTapes(self, libraries, outfile=None):
        if not libraries:
            raise ValueError(
                'Remember that we need the library list to look up for empty tapes')
        response = None
        librariesCondition = 'libvolumes.library_name LIKE {}'.format(
            ' OR libvolumes.library_name LIKE '.join(_.map_(libraries, lambda value: "'%{}%'".format(value))))
        command = "SELECT library_name, volumes.volume_name, pct_reclaim, media.state FROM volumes INNER JOIN media ON volumes.volume_name=media.volume_name INNER JOIN libvolumes ON volumes.volume_name=libvolumes.volume_name WHERE ({}) AND volumes.status='FULL' AND pct_utilized<10 ORDER BY library_name, pct_utilized".format(
            librariesCondition)
        runResponse = self.run(command, failRaises=False, outfile=outfile)
        if runResponse:
            headers = ['library', 'volume', 'utilized', 'state']
            response = self.__getResponseAsObjects(headers, runResponse)

        return response
