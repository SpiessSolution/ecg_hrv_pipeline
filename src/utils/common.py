"""
Common functions
"""


# fmt: off
from typing import Dict, Tuple, Union, List, Optional, Any
import pandas as pd
from pathlib import Path
import yaml
import os
import logging
# fmt: on


##########################
#### COMMON FUNCTIONS ####
##########################

def export_to_yaml(data: Dict[str, Any], output_path: Union[str, Path]) -> None:
    """
    Exports a dictionary to a YAML file at the specified output path.

    Args:
        data (Dict[str, Any]): The dictionary to be exported.
        output_path (Union[str, Path]): The path where the YAML file should be saved.
            Can be a string or a Path object.

    Returns:
        None
    """
    # Convert output path to Path object if it is a string
    output_path = Path(output_path)
    
    with output_path.open('w') as file:
        yaml.dump(data, file, default_flow_style=False)
        
def load_from_yaml(input_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Loads parameters from a YAML file into a Python dictionary.

    Args:
        input_path (Union[str, Path]): The path to the YAML file to be loaded.
            Can be a string or a Path object.

    Returns:
        Dict[str, Any]: The dictionary containing the loaded parameters.
    """
    # Convert input path to Path object if it is a string
    input_path = Path(input_path)
    
    with input_path.open('r') as file:
        data = yaml.safe_load(file)
    
    return data

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
class Logger:
    def __init__(self, name: str, log_level: int = logging.INFO, log_file: str = None) -> None:
        """
        Initializes a configurable logger with options for console and/or file logging.

        This class simplifies the setup of logging in Python applications. It creates a logger
        that can output to the console, a file, or both. The logger is configured with a specific 
        logging level and a uniform format for log messages.

        Args:
            name (str): Name of the logger. This is typically the __name__ of the module
                        creating the logger, which helps identify the source of log messages.
            log_level (int): Logging level, which determines the severity of messages that the
                             logger will handle. Common levels include logging.DEBUG, logging.INFO,
                             logging.WARNING, logging.ERROR, and logging.CRITICAL. Default is logging.INFO.
            log_file (str, optional): File path for the log file. If provided, log messages will be
                                      written to this file. If None, logging will be done only to the console.
                                      Default is None.

        Example:
            >>> logger = Logger(__name__, log_level=logging.DEBUG, log_file='app.log').get_logger()
            >>> logger.info("This is an info message")

        Note:
            - The logger uses a standard message format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'.
            - If a log file path is provided, the directory for the log file will be created if it does not exist.
            - The logger is thread-safe and can be used across different modules in an application.
        """
        # Create a logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        # Define formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        # Create handlers (console and/or file handler)
        if log_file:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

        # Always add console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def get_logger(self) -> logging.Logger:
        """
        Retrieves the configured logger instance. This method should be used to obtain the logger
        after its initial configuration in the constructor.

        Returns:
            logging.Logger: The configured logger instance, ready for logging messages.

        Example:
            >>> my_logger = Logger("myApp", log_level=logging.INFO).get_logger()
            >>> my_logger.info("Logger is configured and ready to use.")
        """
        return self.logger
