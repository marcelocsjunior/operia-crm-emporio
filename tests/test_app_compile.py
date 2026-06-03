import compileall
import py_compile


def test_app_py_compiles():
    py_compile.compile("app.py", doraise=True)


def test_compileall_src_succeeds():
    assert compileall.compile_dir("src", quiet=1)


def test_compileall_tests_succeeds():
    assert compileall.compile_dir("tests", quiet=1)
