import pint

UNITS = pint.UnitRegistry()

A0 = (2 ** (1 / 4) * UNITS.meter, 1 / (2 ** (1 / 4)) * UNITS.meter)
A1 = (A0[1], A0[0] / 2)
A2 = (A1[1], A1[0] / 2)
A3 = (A2[1], A2[0] / 2)
A4 = (A3[1], A3[0] / 2)
A5 = (A4[1], A4[0] / 2)
A6 = (A5[1], A5[0] / 2)
A7 = (A6[1], A6[0] / 2)
LETTER = (11 * UNITS.inch, 8.5 * UNITS.inch)
TABLOID = (11 * UNITS.inch, 17 * UNITS.inch)
