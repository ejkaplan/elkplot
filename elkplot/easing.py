import numpy as np
import numpy.typing as npt


# Implementations adapted from https://easings.net


def ease_in_sine(x: npt.ArrayLike) -> npt.ArrayLike:
    return 1 - np.cos((x * np.pi) / 2)


def ease_out_sine(x: npt.ArrayLike) -> npt.ArrayLike:
    return np.sin((x * np.pi) / 2)


def ease_in_out_sine(x: npt.ArrayLike) -> npt.ArrayLike:
    return -(np.cos(np.pi * x) - 1) / 2


def ease_in_nth_order(x: npt.ArrayLike, n: int = 2) -> npt.ArrayLike:
    """
    Nth order ease in.
    Args:
        x: The x-coordinate in [0, 1]
        n: The order of the polynomial. (n=2 is quadratic ease in, n=3 is cubic, etc.)

    Returns:
        The y-coordinate in [0, 1]
    """
    return np.power(x, n)


def ease_out_nth_order(x: npt.ArrayLike, n: int = 2) -> npt.ArrayLike:
    """
    Nth order ease out.
    Args:
        x: The x-coordinate in [0, 1]
        n: The order of the polynomial. (n=2 is quadratic ease out, n=3 is cubic, etc.)

    Returns:
        The y-coordinate in [0, 1]
    """
    return 1 - np.power(1 - x, n)


def ease_in_out_nth_order(x: npt.ArrayLike, n: int = 2) -> npt.ArrayLike:
    """
    Nth order ease in and out.
    Args:
        x: The x-coordinate in [0, 1]
        n: The order of the polynomial. (n=2 is quadratic ease in and out, n=3 is cubic, etc.)

    Returns:
        The y-coordinate in [0, 1]
    """
    return np.where(
        x < 0.5, np.power(2, n - 1) * np.power(x, n), 1 - np.power(-2 * x + 2, n) / 2
    )


def ease_in_expo(x: npt.ArrayLike) -> npt.ArrayLike:
    return np.where(x == 0, 0, np.power(2, 10 * x - 10))


def ease_out_expo(x: npt.ArrayLike) -> npt.ArrayLike:
    return np.where(x == 1, 1, 1 - np.power(2, -10 * x))


def ease_in_out_expo(x: npt.ArrayLike) -> npt.ArrayLike:
    return np.select(
        [x == 0, x == 1, x < 0.5],
        [0, 1, np.power(2, 20 * x - 10) / 2],
        (2 - np.power(2, -20 * x + 10)) / 2,
    )


def ease_in_circ(x: npt.ArrayLike) -> npt.ArrayLike:
    return 1 - np.sqrt(1 - np.power(x, 2))


def ease_out_circ(x: npt.ArrayLike) -> npt.ArrayLike:
    return np.sqrt(1 - np.power(x - 1, 2))


def ease_in_out_circ(x: npt.ArrayLike) -> npt.ArrayLike:
    return np.where(
        x < 0.5,
        (1 - np.sqrt(1 - np.power(2 * x, 2))) / 2,
        (np.sqrt(1 - np.power(-2 * x + 2, 2)) + 1) / 2,
    )


def ease_in_back(x: npt.ArrayLike, c: float = 1.7) -> npt.ArrayLike:
    """
    Pull slightly negative at the start before blasting off towards (1, 1)
    Args:
        x: The x-coordinate in [0, 1]
        c: The degree to which it pulls back into the negative before racing to 1.
            (If this is 0, it just becomes cubic easing.)

    Returns:
        The y-coordinate in [0, 1]
    """
    return (1 + c) * np.power(x, 3) - c * np.power(x, 2)


def ease_out_back(x: npt.ArrayLike, c: float = 1.7) -> npt.ArrayLike:
    """
    Overshoots slightly over 1 before pulling back to (1, 1)
    Args:
        x: The x-coordinate in [0, 1]
        c: The degree to which it overshoots 1 before pulling back.
            (If this is 0, it just becomes cubic easing.)

    Returns:
        The y-coordinate in [0, 1]
    """
    return 1 + (1 + c) * np.power(x - 1, 3) + c * np.power(x - 1, 2)


def ease_in_out_back(x: npt.ArrayLike, c: float = 1.7) -> npt.ArrayLike:
    """
    Pull slightly negative at the start and overshoots slightly over at the end before pulling back to (1, 1)
    Args:
        x: The x-coordinate in [0, 1]
        c: The degree to which it overshoots/pulls back
            (If this is 0, it just becomes cubic easing.)

    Returns:
        The y-coordinate in [0, 1]
    """
    c2 = c * 1.525
    return np.where(
        x < 0.5,
        (np.power(2 * x, 2) * ((c2 + 1) * 2 * x - c2)) / 2,
        (np.power(2 * x - 2, 2) * ((c2 + 1) * (x * 2 - 2) + c2) + 2) / 2,
    )


def ease_in_elastic(x: npt.ArrayLike, c: float = 2 * np.pi / 3) -> npt.ArrayLike:
    """
    Wiggles back and forth before going off to (1, 1)
    Args:
        x: The x-coordinate in [0, 1]
        c: The "bounciness" factor.

    Returns:
        The y-coordinate in [0, 1]
    """
    return np.select(
        [x == 0, x == 1],
        [0, 1],
        -np.power(2, 10 * x - 10) * np.sin((x * 10 - 10.75) * c),
    )


def ease_out_elastic(x: npt.ArrayLike, c: float = 2 * np.pi / 3) -> npt.ArrayLike:
    """
    Like a snapping elastic band, gets to the top very quickly and then wiggles about y=1 until the wiggles damp down
    to a constant at (1, 1)
    Args:
        x: The x-coordinate in [0, 1]
        c: The "bounciness" factor.

    Returns:
        The y-coordinate in [0, 1]
    """
    return np.select(
        [x == 0, x == 1], [0, 1], np.power(2, -10 * x) * np.sin((x * 10 - 0.75) * c) + 1
    )


def ease_in_out_elastic(x: npt.ArrayLike, c: float = 2 * np.pi / 4.5) -> npt.ArrayLike:
    """
    Wiggles about y=0 at the start with the wiggles increasing in magnitude, then races up to y=1 and damps down to a
    constant at (1, 1)
    Args:
        x: The x-coordinate in [0, 1]
        c: The "bounciness" factor.

    Returns:
        The y-coordinate in [0, 1]
    """
    return np.select(
        [x == 0, x == 1, x < 0.5],
        [0, 1, -(np.power(2, 20 * x - 10) * np.sin((20 * x - 11.125) * c)) / 2],
        (np.power(2, -20 * x + 10) * np.sin((20 * x - 11.125) * c)) / 2 + 1,
    )


def ease_in_bounce(x: npt.ArrayLike) -> npt.ArrayLike:
    return 1 - ease_out_bounce(1 - x)


def ease_out_bounce(x: npt.ArrayLike) -> npt.ArrayLike:
    n = 7.5625
    d = 2.75
    return np.select(
        [x < 1 / d, x < 2 / d, x < 2.5 / d],
        [
            n * np.power(x, 2),
            n * np.power(x - 1.5 / d, 2) + 0.75,
            n * np.power(x - 2.25 / d, 2) + 0.9375,
        ],
        n * np.power(x - 2.625 / d, 2) + 0.984375,
    )


def ease_in_out_bounce(x: npt.ArrayLike) -> npt.ArrayLike:
    first_half = (1 - ease_out_bounce(1 - 2 * x)) / 2
    second_half = (1 + ease_out_bounce(2 * x - 1)) / 2
    return np.where(x < 0.5, first_half, second_half)
