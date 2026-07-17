import functools
import sys
import inspect
from core.logger import get_logger
from core.custom_exception import CustomException

logger = get_logger(__name__)

def with_logging_and_exceptions(func):
    if inspect.isgeneratorfunction(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Starting generator {func.__name__}")
            try:
                gen = func(*args, **kwargs)
                for item in gen:
                    yield item
                logger.info(f"Completed generator {func.__name__} successfully.")
            except Exception as e:
                logger.error(f"Error in generator {func.__name__}: {e}")
                raise CustomException(e, sys)
        return wrapper
    else:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger.info(f"Starting {func.__name__}")
            try:
                result = func(*args, **kwargs)
                logger.info(f"Completed {func.__name__} successfully.")
                return result
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                raise CustomException(e, sys)
        return wrapper
