import pytest
import lib.tsm as tsm
from random import randint
import pytest
from mock import patch


@pytest.fixture
def getTsmClient():
    return {
        "ip": "10.10.10.{}".format(randint(10, 250)),
        "port": "1500",
        "username": "jane",
        "password": "jesse"
    }


class TestTsmClient:

    def test_constructor_with_valid_variables(self, getTsmClient):
        client = tsm.TsmClient(**getTsmClient)
        assert not client == None and isinstance(client, tsm.TsmClient)
        assert client.ip == getTsmClient['ip']
        assert client.port == getTsmClient['port']

    def test_constructor_with_extra_variables(self, getTsmClient):
        getTsmClient['some'] = 'new'
        client = tsm.TsmClient(**getTsmClient)
        assert client.ip == getTsmClient['ip']
        assert client.port == getTsmClient['port']
        assert client.some == 'new'

    def test_constructor_with_missing_variables(self, getTsmClient):
        getTsmClient['ip'] = 'A.B.X.Z'
        try:
            client = tsm.TsmClient(**getTsmClient)
        except Exception as err:
            pytest.raises(TypeError)
            assert 'valid IP address' in err.__str__()

        getTsmClient['ip'] = '10.10.10.10'
        getTsmClient.pop('username')
        getTsmClient.pop('password')
        try:
            client = tsm.TsmClient(**getTsmClient)
        except Exception as err:
            pytest.raises(TypeError)
            assert 'need the username and password' in err.__str__()

    def test_object_has_private_password_and_baseDsmadmcOptions(self, getTsmClient):
        client = tsm.TsmClient(**getTsmClient)
        variables = ['__password', '__baseDsmadmcOptions', '__pwd']
        for privateVariable in variables:
            try:
                client.__getattribute__(privateVariable)
                assert False
            except Exception as err:
                pytest.raises(AttributeError)

    def test_output_is_object(self, getTsmClient):
        client = tsm.TsmClient(**getTsmClient)
        headers = ['c1', 'c2', 'c3']

        output = client._TsmClient__getResponseAsObjects(headers, '1,2,3')
        assert output == [{'c1': '1', 'c2': '2', 'c3': '3'}]

        output = client._TsmClient__getResponseAsObjects(
            headers, '1,2,3\n11,22,33')
        assert output == [{'c1': '1', 'c2': '2', 'c3': '3'},
                          {'c1': '11', 'c2': '22', 'c3': '33'}]

        try:
            client._TsmClient__getResponseAsObjects(headers, '1,2')
            assert False
        except Exception as err:
            pytest.raises(IndexError)

    @patch("os.chdir")
    @patch('subprocess.check_output')
    def test_run(self, mock_check, mock_chdir, getTsmClient):
        mock_chdir.return_value = True
        mock_check.return_value = '1,2,3\n11,22,33'
        client = tsm.TsmClient(**getTsmClient)
        output = client.run('command')
        assert output == '1,2,3\n11,22,33'

    # @patch("os.chdir")
    # @patch('subprocess.check_output')
    # def test_run(self, mock_check, mock_chdir, getTsmClient):
    #     mock_chdir.return_value = True
    #     mock_check.return_value = '1,2,3\n11,22,33'
    #     client = tsm.TsmClient(**getTsmClient)
    #     output = client.run('command')
    #     assert output == '1,2,3\n11,22,33'
