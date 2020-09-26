from .consts import CORE_LANGUAGE
import inlp.convert.chinese as cv


def core_lans(str):
    if CORE_LANGUAGE == 'cn':
        return cv.t2s(str)
    elif CORE_LANGUAGE == 'tc':
        return cv.s2t(str)
    else:
        return str
