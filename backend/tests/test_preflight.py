"""Startup preflight (scripts/preflight.py): clear one-line problems, never the offending values."""

import pytest

from scripts.preflight import BAD_DATABASE_URL, database_warning, load_settings

GOOD_SECRET = "s" * 40


def test_valid_configuration_has_no_problems():
    settings, problems = load_settings(_env_file=None, jwt_secret_key=GOOD_SECRET)
    assert settings is not None and problems == []


def test_invalid_number_names_the_setting_without_its_value():
    settings, problems = load_settings(_env_file=None, jwt_secret_key=GOOD_SECRET, access_token_expire_minutes="abc")
    assert settings is None and len(problems) == 1
    assert problems[0].startswith("ACCESS_TOKEN_EXPIRE_MINUTES in backend\\.env is invalid")
    assert "abc" not in problems[0] and "Traceback" not in problems[0]


def test_out_of_range_value_is_reported():
    _, problems = load_settings(_env_file=None, jwt_secret_key=GOOD_SECRET, login_lockout_minutes=0)
    assert problems and problems[0].startswith("LOGIN_LOCKOUT_MINUTES")


def test_weak_jwt_secret_is_reported_without_echoing_it():
    weak = "short-secret"
    settings, problems = load_settings(_env_file=None, jwt_secret_key=weak)
    assert settings is None and "JWT_SECRET_KEY" in problems[0] and weak not in problems[0]


def test_environment_variable_source_is_named(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "abc")
    _, problems = load_settings(_env_file=None, jwt_secret_key=GOOD_SECRET)
    assert problems == [
        "ACCESS_TOKEN_EXPIRE_MINUTES set as an environment variable is invalid: "
        "Input should be a valid integer, unable to parse string as an integer."
    ]


@pytest.mark.parametrize("url", ["this is :: not a url topsecret-pw", "nosuchdriver://user:topsecret-pw@host/db"])
def test_bad_database_url_never_echoes_it(url):
    settings, _ = load_settings(_env_file=None, jwt_secret_key=GOOD_SECRET, database_url=url)
    warning = database_warning(settings)
    assert warning and "topsecret-pw" not in warning and "user" not in warning
    if url.startswith("this is"):
        assert warning == BAD_DATABASE_URL  # run_backend.ps1 refuses to start
