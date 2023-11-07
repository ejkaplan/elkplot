# import shapely
# from hypothesis import strategies as st

# from elkplot import UNITS


# def quantities(min_val: float, max_val: float, unit: str | UNITS.Unit):
#     magnitude = st.floats(min_val, max_val, allow_nan=False, allow_subnormal=False)
#     unit = UNITS.Unit(unit)

#     def quant(m: float) -> UNITS.Quantity:
#         return m * unit

#     return st.builds(quant, magnitude)


# coordinates = st.tuples(
#     st.floats(min_value=0, max_value=20, allow_nan=False, allow_subnormal=False),
#     st.floats(min_value=0, max_value=20, allow_nan=False, allow_subnormal=False),
# )

# linestrings = st.builds(
#     shapely.linestrings, st.lists(coordinates, min_size=2, max_size=5, unique=True)
# )

# multilinestrings = st.builds(
#     shapely.multilinestrings,
#     st.lists(linestrings, min_size=10, max_size=20, unique=True),
# )

# layers = st.builds(
#     shapely.geometrycollections,
#     st.lists(multilinestrings, min_size=1, max_size=3, unique=True),
# )
