"""
Generate the following packages:

- Chip resistors SMT

"""
from os import path, makedirs
from typing import Iterable, Optional, Dict, Any  # noqa
from uuid import uuid4

from common import now, init_cache, save_cache
from common import format_float as ff, format_ipc_dimension as fd


generator = 'librepcb-parts-generator (generate_chip.py)'

line_width = 0.25
line_width_thin = 0.15
line_width_thinner = 0.1
pkg_text_height = 1.0
label_offset = 1.1
label_offset_thin = 0.8
silkscreen_clearance = 0.15


# Initialize UUID cache
uuid_cache_file = 'uuid_cache_chip.csv'
uuid_cache = init_cache(uuid_cache_file)


def uuid(category: str, full_name: str, identifier: str) -> str:
    """
    Return a uuid for the specified pin.

    Params:
        category:
            For example 'cmp' or 'pkg'.
        full_name:
            For example "RESC3216X65".
        identifier:
            For example 'pad-1' or 'pin-13'.
    """
    key = '{}-{}-{}'.format(category, full_name, identifier).lower().replace(' ', '~')
    if key not in uuid_cache:
        uuid_cache[key] = str(uuid4())
    return uuid_cache[key]


class ChipConfig:
    def __init__(
        self,
        size_imperial: str,  # String, e.g. "1206"
        length: float,
        width: float,
        height: float,
        pad_length: float,
        pad_width: float,
        gap: float,
    ):
        self._size_imperial = size_imperial
        self.length = length
        self.width = width
        self.height = height
        self.pad_length = pad_length
        self.pad_width = pad_width
        self.gap = gap

    def size_metric(self) -> str:
        return str(int(self.length * 10)).rjust(2, '0') + str(int(self.width * 10)).rjust(2, '0')

    def size_imperial(self) -> str:
        return self._size_imperial


def generate_pkg(
    dirpath: str,
    author: str,
    name: str,
    description: str,
    configs: Iterable[ChipConfig],
    pkgcat: str,
    keywords: str,
    create_date: Optional[str],
):
    category = 'pkg'
    for config in configs:
        lines = []

        fmt_params = {
            'size_metric': config.size_metric(),
            'size_imperial': config.size_imperial(),
        }  # type: Dict[str, Any]
        fmt_params_name = {
            **fmt_params,
            'height': fd(config.height),
        }
        fmt_params_desc = {
            **fmt_params,
            'length': config.length,
            'width': config.width,
            'height': config.height,
        }
        full_name = name.format(**fmt_params_name)
        full_desc = description.format(**fmt_params_desc)

        def _uuid(identifier):
            return uuid(category, full_name, identifier)

        # UUIDs
        uuid_pkg = _uuid('pkg')
        uuid_pads = [_uuid('pad-1'), _uuid('pad-2')]

        print('Generating {}: {}'.format(full_name, uuid_pkg))

        # General info
        lines.append('(librepcb_package {}'.format(uuid_pkg))
        lines.append(' (name "{}")'.format(full_name))
        lines.append(' (description "{}\\n\\nGenerated with {}")'.format(full_desc, generator))
        lines.append(' (keywords "{},{},{}")'.format(
            config.size_metric(), config.size_imperial(), keywords,
        ))
        lines.append(' (author "{}")'.format(author))
        lines.append(' (version "0.3")')
        lines.append(' (created {})'.format(create_date or now()))
        lines.append(' (deprecated false)')
        lines.append(' (category {})'.format(pkgcat))
        lines.append(' (pad {} (name "1"))'.format(uuid_pads[0]))
        lines.append(' (pad {} (name "2"))'.format(uuid_pads[1]))

        def add_footprint_variant(key: str, name: str):
            uuid_footprint = _uuid('footprint-{}'.format(key))
            uuid_text_name = _uuid('text-name-{}'.format(key))
            uuid_text_value = _uuid('text-value-{}'.format(key))
            uuid_silkscreen_top = _uuid('line-silkscreen-top-{}'.format(key))
            uuid_silkscreen_bot = _uuid('line-silkscreen-bot-{}'.format(key))
            uuid_outline = _uuid('polygon-outline-{}'.format(key))

            # Line width adjusted for size of element
            if config.length >= 2.0:
                silk_lw = line_width
                doc_lw = line_width
            elif config.length >= 1.0:
                silk_lw = line_width_thin
                doc_lw = line_width_thin
            else:
                silk_lw = line_width_thin
                doc_lw = line_width_thinner

            lines.append(' (footprint {}'.format(uuid_footprint))
            lines.append('  (name "{}")'.format(name))
            lines.append('  (description "")')

            # Pads
            for p in [0, 1]:
                pad_uuid = uuid_pads[p - 1]
                sign = -1 if p == 1 else 1
                dx = ff(sign * (config.gap / 2 + config.pad_length / 2))  # x offset (delta-x)
                lines.append('  (pad {} (side top) (shape rect)'.format(pad_uuid))
                lines.append('   (position {} 0) (rotation 0.0) (size {} {}) (drill 0.0)'.format(
                    dx,
                    ff(config.pad_length),
                    ff(config.pad_width),
                ))
                lines.append('  )')

            # Documentation
            lines.append('  (polygon {} (layer {})'.format(uuid_outline, 'top_documentation'))
            lines.append('   (width {}) (fill false) (grab_area true)'.format(doc_lw))
            hl = ff(config.width / 2)  # half length
            hw = ff(config.length / 2)  # half width
            lines.append('   (vertex (position -{} {}) (angle 0.0))'.format(hw, hl))  # NW
            lines.append('   (vertex (position {} {}) (angle 0.0))'.format(hw, hl))  # NE
            lines.append('   (vertex (position {} -{}) (angle 0.0))'.format(hw, hl))  # SE
            lines.append('   (vertex (position -{} -{}) (angle 0.0))'.format(hw, hl))  # SW
            lines.append('   (vertex (position -{} {}) (angle 0.0))'.format(hw, hl))  # NW
            lines.append('  )')

            # Silkscreen
            if config.length > 1.0:
                dx = ff(config.gap / 2 - silk_lw / 2 - silkscreen_clearance)
                dy = ff(config.width / 2 + silk_lw / 2)
                lines.append('  (polygon {} (layer {})'.format(uuid_silkscreen_top, 'top_placement'))
                lines.append('   (width {}) (fill false) (grab_area false)'.format(silk_lw))
                lines.append('   (vertex (position -{} {}) (angle 0.0))'.format(dx, dy))
                lines.append('   (vertex (position {} {}) (angle 0.0))'.format(dx, dy))
                lines.append('  )')
                lines.append('  (polygon {} (layer {})'.format(uuid_silkscreen_bot, 'top_placement'))
                lines.append('   (width {}) (fill false) (grab_area false)'.format(silk_lw))
                lines.append('   (vertex (position -{} -{}) (angle 0.0))'.format(dx, dy))
                lines.append('   (vertex (position {} -{}) (angle 0.0))'.format(dx, dy))
                lines.append('  )')

            # Labels
            if config.width < 2.0:
                offset = label_offset_thin
            else:
                offset = label_offset
            dy = ff(config.width / 2 + offset)  # y offset (delta-y)
            text_attrs = '(height {}) (stroke_width 0.2) ' \
                         '(letter_spacing auto) (line_spacing auto)'.format(pkg_text_height)
            lines.append('  (stroke_text {} (layer top_names)'.format(uuid_text_name))
            lines.append('   {}'.format(text_attrs))
            lines.append('   (align center bottom) (position 0.0 {}) (rotation 0.0)'.format(dy))
            lines.append('   (auto_rotate true) (mirror false) (value "{{NAME}}")')
            lines.append('  )')
            lines.append('  (stroke_text {} (layer top_values)'.format(uuid_text_value))
            lines.append('   {}'.format(text_attrs))
            lines.append('   (align center top) (position 0.0 -{}) (rotation 0.0)'.format(dy))
            lines.append('   (auto_rotate true) (mirror false) (value "{{VALUE}}")')
            lines.append('  )')

            lines.append(' )')

        add_footprint_variant('reflow', 'reflow')
        add_footprint_variant('handsoldering', 'hand soldering')

        lines.append(')')

        pkg_dir_path = path.join(dirpath, uuid_pkg)
        if not (path.exists(pkg_dir_path) and path.isdir(pkg_dir_path)):
            makedirs(pkg_dir_path)
        with open(path.join(pkg_dir_path, '.librepcb-pkg'), 'w') as f:
            f.write('0.1\n')
        with open(path.join(pkg_dir_path, 'package.lp'), 'w') as f:
            f.write('\n'.join(lines))
            f.write('\n')


if __name__ == '__main__':
    def _make(dirpath: str):
        if not (path.exists(dirpath) and path.isdir(dirpath)):
            makedirs(dirpath)
    _make('out')
    _make('out/chip')
    _make('out/chip/pkg')
    generate_pkg(
        dirpath='out/chip/pkg',
        author='Danilo B.',
        name='RESC{size_metric}X{height} ({size_imperial})',
        description='Chip resistor {size_metric} (imperial {size_imperial}).\\n\\n'
                    'Length: {length}mm\\nWidth: {width}mm\\nHeight: max {height}mm',
        configs=[
            #        imperial, len, wid,  hght, plen, pwid, gap
            ChipConfig('01005', .4,  .2,  0.15,  .17,  .18, 0.2),   # noqa
            ChipConfig('0201',  .6,  .3,  0.26,  .37,  .29, 0.28),  # noqa
            ChipConfig('0402', 1.0,  .5,  0.35,  .6,   .5,  0.5),   # noqa
            ChipConfig('0603', 1.6,  .8,  0.55,  .8,   .8,  0.8),   # noqa
            ChipConfig('0805', 2.0, 1.25, 0.60,  .9,  1.2,  1.4),   # noqa
            ChipConfig('0805', 2.0, 1.25, 0.65,  .9,  1.2,  1.4),   # noqa
            ChipConfig('0805', 2.0, 1.25, 0.70,  .9,  1.2,  1.4),   # noqa
            ChipConfig('1206', 3.2, 1.6,  0.60, 1.3,  1.5,  1.8),   # noqa
            ChipConfig('1206', 3.2, 1.6,  0.65, 1.3,  1.5,  1.8),   # noqa
            ChipConfig('1206', 3.2, 1.6,  0.70, 1.3,  1.5,  1.8),   # noqa
            ChipConfig('1210', 3.2, 2.55, 0.60, 1.3,  2.4,  1.8),   # noqa
            ChipConfig('1210', 3.2, 2.55, 0.65, 1.3,  2.4,  1.8),   # noqa
            ChipConfig('1210', 3.2, 2.55, 0.70, 1.3,  2.4,  1.8),   # noqa
            ChipConfig('2010', 5.0, 2.5,  0.65, 1.4,  2.4,  3.3),   # noqa
            ChipConfig('2010', 5.0, 2.5,  0.70, 1.4,  2.4,  3.3),   # noqa
            ChipConfig('2512', 6.4, 3.2,  0.65, 1.4,  3.0,  4.6),   # noqa
            ChipConfig('2512', 6.4, 3.2,  0.70, 1.4,  3.0,  4.6),   # noqa
        ],
        pkgcat='a20f0330-06d3-4bc2-a1fa-f8577deb6770',
        keywords='r,resistor,chip',
        create_date='2018-12-19T00:08:03Z',
    )
    save_cache(uuid_cache_file, uuid_cache)
