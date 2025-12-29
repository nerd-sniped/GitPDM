from freecad_gitpdm.core.result import Result


def test_result_success():
    r = Result.success(123)
    assert r.ok is True
    assert r.value == 123
    assert r.error is None


def test_result_failure():
    r = Result.failure("NOPE", "Nope", details="x")
    assert r.ok is False
    assert r.value is None
    assert r.error is not None
    assert r.error.code == "NOPE"
    assert r.error.message == "Nope"
    assert r.error.details == "x"


def test_result_unwrap_or():
    assert Result.success("a").unwrap_or("b") == "a"
    assert Result.failure("ERR", "bad").unwrap_or("b") == "b"
