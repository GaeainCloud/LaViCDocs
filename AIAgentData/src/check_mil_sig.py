from logger import get_logger
log = get_logger(__name__)
import military_symbol
import inspect
log.info(inspect.signature(military_symbol.get_symbol_svg_string_from_sidc))
