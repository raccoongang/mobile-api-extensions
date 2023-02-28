"""
Fake test for pass test by CI/CD
"""

from mobile_api_extensions.sample_app import Fake, NewFake


def test_pass(json_response):
    assert json_response.status_code == 200
    assert isinstance(json_response.message, str)


def test_fail(false_json_response):
    assert false_json_response.status_code == 400


def test_fake_class():
    base_num = 42
    fake = Fake(base_num)

    assert fake.a == base_num


def test_new_fake_class():
    base_num = 42
    new_fake = NewFake(base_num)

    assert new_fake.b == base_num
    new_fake.b = base_num + 1
    assert new_fake.b == base_num + 1
