import locale
import logging

logger = logging.getLogger(__name__)

def set_finnish_locale() -> None:
    logger.info('Setting locale...')
    try:
        locale.setlocale(locale.LC_ALL, 'fi_FI.UTF-8')
    except Exception as e:
        logger.warning(f'Failed to set fi_FI.UTF-8 locale: {e}. Continuing with default locale.')
