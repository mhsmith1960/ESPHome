# coding=utf-8
import logging
import os.path

import voluptuous as vol

import esphomeyaml.config_validation as cv
from esphomeyaml import core
from esphomeyaml.components import display
from esphomeyaml.const import CONF_FILE, CONF_ID, CONF_RESIZE
from esphomeyaml.core import HexInt
from esphomeyaml.helpers import App, ArrayInitializer, MockObj, Pvariable, RawExpression, add

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['display']

Image_ = display.display_ns.Image


def validate_pillow_installed(value):
    try:
        # pylint: disable=unused-variable
        import PIL
    except ImportError:
        raise vol.Invalid("Please install the pillow python package to use images. "
                          "(pip2 install pillow)")

    return value


def validate_image_file(value):
    value = cv.string(value)
    path = os.path.join(core.CONFIG_PATH, value)
    if not os.path.isfile(path):
        raise vol.Invalid(u"Could not find file '{}'. Please make sure it exists.".format(path))
    return value


CONF_RAW_DATA_ID = 'raw_data_id'

FONT_SCHEMA = vol.Schema({
    vol.Required(CONF_ID): cv.declare_variable_id(Image_),
    vol.Required(CONF_FILE): validate_image_file,
    vol.Optional(CONF_RESIZE): cv.dimensions,
    cv.GenerateID(CONF_RAW_DATA_ID): cv.declare_variable_id(None),
})

CONFIG_SCHEMA = vol.All(validate_pillow_installed, cv.ensure_list, [FONT_SCHEMA])


def to_code(config):
    from PIL import Image

    for conf in config:
        path = os.path.join(core.CONFIG_PATH, conf[CONF_FILE])
        try:
            image = Image.open(path)
        except Exception as e:
            raise core.ESPHomeYAMLError(u"Could not load image file {}: {}".format(path, e))

        if CONF_RESIZE in conf:
            image.thumbnail(conf[CONF_RESIZE])

        image = image.convert('1')
        width, height = image.size
        if width > 500 or height > 500:
            _LOGGER.warning("The image you requested is very big. Please consider using the resize "
                            "parameter")
        width8 = ((width + 7) // 8) * 8
        data = [0 for _ in range(height * width8 // 8)]
        for y in range(height):
            for x in range(width):
                if image.getpixel((x, y)):
                    continue
                pos = x + y * width8
                data[pos // 8] |= 0x80 >> (pos % 8)

        raw_data = MockObj(conf[CONF_RAW_DATA_ID])
        add(RawExpression('static const uint8_t {}[{}] PROGMEM = {}'.format(
            raw_data, len(data),
            ArrayInitializer(*[HexInt(x) for x in data], multiline=False))))

        rhs = App.make_image(raw_data, width, height)
        Pvariable(conf[CONF_ID], rhs)
