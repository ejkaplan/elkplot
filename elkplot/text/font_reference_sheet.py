import shapely
from shapely import affinity

import elkplot
from elkplot.text.hershey import HersheyFont, Font


def move_to(drawing: shapely.MultiLineString, x: float, y: float):
    x0, y0, _, _ = drawing.bounds
    dx, dy = x - x0, y - y0
    return affinity.translate(drawing, dx, dy)


def font_demo(font: HersheyFont, name: str) -> shapely.MultiLineString:
    name_font = Font(elkplot.FUTURAL, 30)
    sample_font = Font(font, 15)
    # name_text = elkplot.text(name, elkplot.FUTURAL)
    # sample_text = elkplot.text("AaBbCc 123", font)
    name_text = name_font.text(name)
    sample_text = sample_font.text("AaBbCc 123")
    name_text = elkplot.scale_to_fit(name_text, height=0.2)
    sample_text = elkplot.scale_to_fit(sample_text, height=0.3)
    return shapely.union_all([move_to(name_text, 0, 0), move_to(sample_text, 0, 0.3)])


def main():
    fonts = {
        "Astrology": elkplot.ASTROLOGY,
        "Cursive": elkplot.CURSIVE,
        "Cyrillic_1": elkplot.CYRILLIC_1,
        "Cyrillic": elkplot.CYRILLIC,
        "Futural": elkplot.FUTURAL,
        "Futuram": elkplot.FUTURAM,
        "GothGBT": elkplot.GOTHGBT,
        "GothGRT": elkplot.GOTHGBT,
        "Gothiceng": elkplot.GOTHICENG,
        "Gothicger": elkplot.GOTHICGER,
        "Gothicita": elkplot.GOTHICITA,
        "Gothitt": elkplot.GOTHITT,
        "Greek": elkplot.GREEK,
        "Greekc": elkplot.GREEKC,
        "Greeks": elkplot.GREEKS,
        "Japanese": elkplot.JAPANESE,
        "Markers": elkplot.MARKERS,
        "Mathlow": elkplot.MATHLOW,
        "Mathupp": elkplot.MATHUPP,
        "Meteorology": elkplot.METEOROLOGY,
        "Music": elkplot.MUSIC,
        "Rowmand": elkplot.ROWMAND,
        "Rowmans": elkplot.ROWMANS,
        "Rowmant": elkplot.ROWMANT,
        "Scriptc": elkplot.SCRIPTC,
        "Scripts": elkplot.SCRIPTS,
        "Symbolic": elkplot.SYMBOLIC,
        "Timesg": elkplot.TIMESG,
        "Timesi": elkplot.TIMESI,
        "Timesib": elkplot.TIMESIB,
        "Timesr": elkplot.TIMESR,
        "Timesrb": elkplot.TIMESRB,
    }
    samples = []
    size = elkplot.sizes.LETTER
    margin = 0.5
    column = 0
    column_start = 0
    for i, (name, font) in enumerate(fonts.items()):
        drawing = font_demo(font, name)
        drawing = elkplot.scale_to_fit(drawing, height=0.5)
        x = margin + 3.5 * column
        y = margin + (i - column_start) * 0.7
        if y > size[1].m - margin - 0.5:
            column += 1
            column_start = i
            x = margin + 3.5 * column
            y = margin + (i - column_start) * 0.7
        drawing = move_to(drawing, x, y)
        samples.append(drawing)
    output = shapely.union_all(samples)
    output = elkplot.scale_to_fit(output, *size, margin)
    output = elkplot.optimize(output, 0.01)
    elkplot.draw(output, *size, plot=False, preview_dpi=80)


if __name__ == "__main__":
    size = 4 * elkplot.UNITS.inch, 2 * elkplot.UNITS.inch
    font = elkplot.Font(elkplot.METEOROLOGY, 25)  # select the meteorology font at size 15
    text_drawing = font.wrap("The quick brown fox jumps over the lazy dog.", 3)
    text_drawing = elkplot.center(text_drawing, *size)
    elkplot.draw(text_drawing, *size, plot=False)
    # main()
