"""
Data loading functions
"""


# fmt: off
from typing import Dict, Tuple, Union, List, Optional, Any
import warnings
import pandas as pd
from pathlib import Path
import utils.common as common
# fmt: on



################################################
#### DATA LOADING AND PREPARATION FUNCTIONS ####
################################################

def load_dyad_ecg_events(filepath_ecg: Union[str, Path], filepath_events: Union[str, Path]) -> pd.DataFrame:
    """
    Load ECG and event data, merging them into a single DataFrame.

    This function reads ECG and event data from the specified file paths, 
    and performs a left join on the event data using the timestamp as the 
    index. The resulting DataFrame contains the ECG signal data along 
    with associated event information.

    Parameters:
    ----------
    filepath_ecg : Union[str, Path]
        The file path to the ECG data file. This can be a string or a 
        Path object.

    filepath_events : Union[str, Path]
        The file path to the event data file. This can be a string or a 
        Path object.

    Returns:
    -------
    pd.DataFrame
        A DataFrame containing the merged ECG and event data, indexed 
        by the timestamps of the ECG data.

    Raises:
    ------
    FileNotFoundError
        If either of the provided file paths does not exist.
    ValueError
        If the data cannot be merged due to incompatible indices.
    """
    # Load datasets
    event_df = load_event_data(filepath_events)
    ecg_df = load_ecg_data(filepath_ecg)
    # Left-join the events on the signal data
    merged_df = ecg_df.merge(
        event_df.set_index("timestamp_ms"), 
        left_index=True, 
        right_index=True, 
        how='left'
    )
    return merged_df

def prepare_ecg_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares a DataFrame for analysis by renaming specific columns and setting the index.

    This function renames the columns 'Time (s)', 'MWCHILD_Bio', and 'MOTHER_Bio' to 
    'seconds', 'child_ecg', and 'mother_ecg' respectively. It also sets the 'seconds' 
    column as the index of the DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame containing columns 'Time (s)', 'MWCHILD_Bio', 
            and 'MOTHER_Bio'.

    Returns:
        pd.DataFrame: A new DataFrame with renamed columns and 'seconds' as the index.

    Raises:
        KeyError: If any of the specified columns are missing in the input DataFrame.
    """
    df = df.rename(columns={'Time (s)': 'seconds', 'MWCHILD_Bio': 'child_ecg', 'MOTHER_Bio': 'mother_ecg'}, errors='raise')
    df = df.set_index("seconds")
    return df

def split_in_child_mother_series(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """
    Splits a DataFrame into separate Series for child and mother ECG data.

    This function extracts the 'child_ecg' and 'mother_ecg' columns from the provided
    DataFrame and returns them as separate Series, each retaining the original index
    from the DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame containing 'child_ecg' and 'mother_ecg' columns.

    Returns:
        Tuple[pd.Series, pd.Series]: A tuple containing two Series: the first for 'child_ecg'
            data and the second for 'mother_ecg' data, both with the original index.

    Raises:
        KeyError: If 'child_ecg' or 'mother_ecg' columns are missing in the input DataFrame.
    """
    child_ecg = df['child_ecg']
    child_ecg.index = df.index
    mother_ecg = df['mother_ecg']
    mother_ecg.index = df.index
    
    return child_ecg, mother_ecg

def load_ecg_data(file_path: Union[str, Path]) -> Tuple[pd.Series, pd.Series]:
    """
    Loads and processes data from a specified file, returning separated ECG 
    series for child and mother.

    Args:
        file_path (Union[str, Path]): The file path to the data file (tab-separated format).
    
    Returns:
        Tuple[pd.Series, pd.Series]: A tuple containing the child data series and mother data series.
    
    Raises:
        FileNotFoundError: If the file does not exist at the specified path.
        pd.errors.ParserError: If there is an error reading the CSV file.
    
    Notes:
        - The data file should be in tab-separated format.
    """
    
    df = pd.read_csv(file_path, sep='\t', skiprows=1)
    df = prepare_ecg_data(df)
    # child_series, mother_series = split_in_child_mother_series(df)
    return df #child_series, mother_series

def extract_subject_id_condition_from_filepath(file_path: Union[str, Path]) -> Tuple[int, str]:
    """
    Extracts the subject ID and condition code from a file path.

    Args:
        file_path (Union[str, Path]): The path to the file, containing a file name 
            with the subject ID and condition information.

    Returns:
        Tuple[str, str]: A tuple containing:
            - subject_id (int): The ID of the subject as integer.
            - condition (str): A single-character code representing the condition.
    
    Raises:
        AssertionError: If the condition code is not a single character or the 
            subject ID length is not between 2 and 3 characters.
    
    Example:
        For a file path with the file name "C123_data.txt", this function extracts:
            - condition = "C"
            - subject_id = "123"
    """
    file_path = Path(file_path)
    file_name = file_path.stem
    condition_subject_wave_type_string = file_name.split('_')
    assert len(condition_subject_wave_type_string) == 3, f"Error parsing file {file_name}. File should be of format B01_W1_event.txt or B01_W1_mc.txt"
    condition = (condition_subject_wave_type_string[0][0]).upper() # first element = condition letter
    subject_id = int(condition_subject_wave_type_string[0][1:]) # digits
    wave = condition_subject_wave_type_string[1]
    file_type = condition_subject_wave_type_string[-1]
    
    assert len(condition) == 1
    assert len(wave) == 2, f"Error: wave should be 2 letters/digits but is {len(wave)} in file {file_path}"
    assert ('mc' in file_type) or ('event' in file_type)
   
    return subject_id, condition, wave

def load_event_data(filepath: Union[str, Path]) -> pd.DataFrame:
    """
    Load an event file, preproces the it and return it as DataFrame.

    Args:
        filepath (Union[str, Path]): The file path to the event file.

    Returns:
        pd.DataFrame: The event data as a DataFrame.
    """
    df = pd.read_csv(filepath, delimiter='\t', skiprows=1)
    df_clean = prepare_event_data(df)
    
    return df_clean

def prepare_event_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preprocesses the event DataFrame by renaming its columns and validating its structure.
    Args:
        df (pd.DataFrame): The input DataFrame containing event data. It must have a column named 'Acquisition Start' 
                           and exactly 3 columns.
    Returns:
        pd.DataFrame: The processed DataFrame with columns renamed to ['event', 'event_description', 'timestamp_ms'].
    Raises:
        AssertionError: If the 'Acquisition Start' column is not found in the DataFrame.
        AssertionError: If the DataFrame does not have exactly 3 columns.
    """
    assert 'Acquisition Start' in df.columns, "Acquisition Start column not found in the event file."
    assert df.shape[1] == 3, "Event file should have 3 columns."
    df.columns = ['event', 'event_description', 'timestamp_ms']
    df['event_description'] = df['event_description'].apply(lambda x: x.strip())
    
    return df

def iterate_batches(df: pd.DataFrame, batch_size: int):
    """Iterates over a DataFrame in batches of a specific size.

    Args:
        df (pd.DataFrame): The DataFrame to iterate over.
        batch_size (int): The number of rows per batch.

    Yields:
        pd.DataFrame: A DataFrame representing the current batch.
    """
    for start in range(0, len(df), batch_size):
        yield df.iloc[start:start + batch_size]


################################
#### SEGMENTATION FUNCTIONS ####
################################

def get_event_time_from_dataframe_index(event: Union[str, float], df: pd.DataFrame) -> float:
    """Note that df must have ms as time index"""
    assert 'event_description' in df.columns 
    if (isinstance(event, str)):
        if common.is_number(event):
            return float(event)
        row = df[df['event_description'] == event]
        if len(row) == 1:
            return row.index[0]
        else:
            raise ValueError(f"Found {len(row)} rows in df for event: {event}")
    elif isinstance(event, float):
        return event

def segment_df(df: pd.DataFrame, pipeline_params: Dict) -> List[pd.DataFrame]:
    segments = []
    for segment_info in pipeline_params['segmentation'].items():
        # Extract the information from the dictionary. 
        segment_name = segment_info[0]
        event_onset = segment_info[1]['event_onset']
        event_offset = segment_info[1]['duration']
        if common.is_number(event_offset):
            event_offset = float(event_offset)
        
        # get the onset and offset times
        event_onset_time = get_event_time_from_dataframe_index(event_onset, df)
        event_offset_time = event_onset_time + event_offset - 1/pipeline_params['general']['sampling_frequency']
        
        # retrieve the data in between (inclusive bounds) the onset and offset time using the index
        segment = df[(df.index >= event_onset_time) & (df.index < event_offset_time)]
        if segment.empty:
            warnings.warn(f"Segment {segment_name} is empty between {event_onset_time} and {event_offset_time} ms. Please check the event indices.")
            continue
        segments.append(segment)
    
    return segments
        
    