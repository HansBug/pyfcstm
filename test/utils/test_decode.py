import glob
import os.path
import pathlib

import pytest

from pyfcstm.utils import auto_decode
from ..testings import get_testfile


def get_cn_cases():
    return [
        file
        for file in glob.glob(get_testfile("cncode_*.c"))
        if os.path.basename(file) != "cncode_expected.c"
    ]


@pytest.fixture()
def cn_expected_text():
    return pathlib.Path(get_testfile("cncode_expected.c")).read_text(encoding="utf-8")


def get_zh_cases():
    return [
        file
        for file in glob.glob(get_testfile("zhcode_*.c"))
        if os.path.basename(file) != "zhcode_expected.c"
    ]


@pytest.fixture()
def zh_expected_text():
    return pathlib.Path(get_testfile("zhcode_expected.c")).read_text(encoding="utf-8")


@pytest.mark.unittest
class TestUtilsDecode:
    @pytest.mark.parametrize(["code_file"], [(file,) for file in get_cn_cases()])
    def test_auto_decode_for_simplified_chinese(
        self, code_file, cn_expected_text, text_aligner
    ):
        actual_text = auto_decode(pathlib.Path(code_file).read_bytes())
        text_aligner.assert_equal(
            expect=cn_expected_text,
            actual=actual_text,
        )

    @pytest.mark.parametrize(["code_file"], [(file,) for file in get_zh_cases()])
    def test_auto_decode_for_traditional_chinese(
        self, code_file, zh_expected_text, text_aligner
    ):
        actual_text = auto_decode(pathlib.Path(code_file).read_bytes())
        text_aligner.assert_equal(
            expect=zh_expected_text,
            actual=actual_text,
        )
