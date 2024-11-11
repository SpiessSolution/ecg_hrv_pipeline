"""
Common functions
"""


# fmt: off
from typing import Dict, Tuple, Union, List, Optional, Any
import pandas as pd
from pathlib import Path
import yaml
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

