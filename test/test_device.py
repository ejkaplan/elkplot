import pytest
from elkplot import Device
import config

@pytest.mark.skipif(config.SKIP_DRAWING_TESTS, reason="skipping rendering tests")
def test_position():
    d = Device()
    print(d.read_position())


def main():
    test_position()


if __name__ == "__main__":
    main()

