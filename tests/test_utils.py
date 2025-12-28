from app import allowed_file, get_ip_address, get_cpu_temp, get_system_stats


class _T:
    def __init__(self, current):
        self.current = current


def test_allowed_file_positive():
    assert allowed_file('foo.txt')
    assert allowed_file('image.PNG')


def test_allowed_file_negative():
    assert not allowed_file('')
    assert not allowed_file('noext')
    assert not allowed_file('foo.exe')


def test_get_ip_address_returns_string():
    ip = get_ip_address()
    assert isinstance(ip, str)


def test_get_cpu_temp_with_mock(monkeypatch):
    monkeypatch.setattr('psutil.sensors_temperatures', lambda: {'cpu_thermal': [_T(42.5)]})
    assert get_cpu_temp() == '42.5'


def test_get_system_stats_handles_exception(monkeypatch):
    def bad_cpu(*a, **k):
        raise RuntimeError('oops')

    monkeypatch.setattr('psutil.cpu_percent', bad_cpu)
    stats = get_system_stats()
    assert stats['hostname'] == 'Error' or isinstance(stats['cpu_usage'], (int, float))
