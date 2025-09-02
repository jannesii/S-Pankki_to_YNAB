import shutil
import logging

logger = logging.getLogger(__name__)

def move_file(source: str, destination_dir: str) -> None:
    try:
        logger.info(f"Attempting to move file from {source} to {destination_dir}")
        shutil.move(source, destination_dir)
        logger.info(f'File moved from {source} to {destination_dir}')
    except FileNotFoundError:
        logger.exception(f'The file {source} does not exist.')
    except PermissionError:
        logger.exception(f'Permission denied: Unable to move the file {source}.')
    except Exception as e:
        logger.exception(f'Error moving file: {e}')
