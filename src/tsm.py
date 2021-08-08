import pydash as _
from os import environ, chdir, getcwd
from platform import system
from ipaddress import ip_address
from subprocess import run, check_output, TimeoutExpired


class TsmClient:

    DEFAULT_ENV_USERNAME_VARIABLE = 'TSM_USERNAME'
    DEFAULT_ENV_PASSWORD_VARIABLE = 'TSM_PASSWORD'
    DEFAULT_TSM_PORT = '1500'
    BASE_DSMADMC_OPTIONS = {
        'noconf': True,
        'comma': True,
        'dataonly': 'yes'
    }
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
            try:
                run('ping {}'.format(self.ip), shell=True,
                    timeout=self.TIMEOUT_IN_SECONDS)
            except TimeoutExpired:
                message = 'Bad news, the TSM server did not respond and we are not reaching with a simple ping. Maybe it is a network issue'
                if failRaises:
                    raise TimeoutError(message)
                print(message)
            except Exception as err:
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
