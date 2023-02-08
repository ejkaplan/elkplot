from elkplot.calibrate import calibrate_penlift
from elkplot.cli import penlift


def test_calibrate_penlift():
    calibrate_penlift(10, 10, 0.5)
