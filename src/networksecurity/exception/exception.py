import sys
from types import TracebackType

from networksecurity.logging.logger import logger


def error_message_detail(error: Exception, error_traceback: TracebackType | None) -> str:
    if error_traceback is None:
        return str(error)

    file_name = error_traceback.tb_frame.f_code.co_filename
    line_number = error_traceback.tb_lineno

    return (
        f"Error occurred in python script [{file_name}] "
        f"at line number [{line_number}] with error message [{error}]"
    )


class NetworkSecurityException(Exception):
    def __init__(self, error_message: Exception, error_detail: object = sys) -> None:
        _, _, exc_tb = error_detail.exc_info()
        self.error_message = error_message_detail(error_message, exc_tb)
        super().__init__(self.error_message)

    def __str__(self) -> str:
        return self.error_message


if __name__ == "__main__":
    try:
        logger.info("Testing custom exception handling")
        a = 1 / 0
        print("This will not be printed", a)
    except Exception as error:
        logger.error("Exception occurred", exc_info=True)
        raise NetworkSecurityException(error, sys)
