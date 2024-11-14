import pandas as pd
from pathlib import Path
import numpy as np
from typing import Union, List


def plausible_to_nan(
    df: pd.DataFrame, 
    column: str, 
    lower_bound: float = 9, 
    upper_bound: float = 110
) -> pd.DataFrame:
    """
    Creates a new colum based on the specified column, replacing implausible values with NaN.
    
    Parameters:
    ----------
    df : pd.DataFrame
        The input DataFrame containing the data to process.
    column : str
        The name of the column to check for plausibility.
    lower_bound : float, optional
        The lower bound for plausible values. Values below this will be set to NaN. Default is 9.
    upper_bound : float, optional
        The upper bound for plausible values. Values above this will be set to NaN. Default is 110.
        
    Returns:
    -------
    pd.DataFrame
        A DataFrame with implausible values in the specified column replaced by NaN.
    """
    df = df.copy()  # To avoid modifying the original DataFrame
    df[f"{column}_plausible"] = np.where(
        (df[column] < lower_bound) | (df[column] > upper_bound), 
        np.nan, 
        df[column]
    )
    return df

def identify_outliers_zscore(
    data: Union[List[float], np.ndarray, pd.Series], 
    threshold: float = 1.96
) -> List[bool]:
    """
    Identify outliers in a dataset based on the Z-score method.
    
    Parameters:
    ----------
    data : Union[List[float], np.ndarray, pd.Series]
        The input data, which can be a list, numpy array, or pandas series.
    threshold : float, optional
        The Z-score threshold to determine outliers. Default is 1.96 (i.e., >95%).
        
    Returns:
    -------
    List[bool]
        A list of booleans indicating whether each value is an outlier (True) or not (False).
        NaN values are treated as outliers.
    """
    # Convert data to a numpy array
    data_array = np.asarray(data, dtype=np.float64)
    
    # Identify NaN values (NaN will be treated as outliers)
    nan_mask = np.isnan(data_array)
    
    # Calculate Z-scores only for non-NaN values
    valid_data = data_array[~nan_mask]
    mean = valid_data.mean()
    std = valid_data.std(ddof=0)
    
    z_scores = (valid_data - mean) / std
    outliers_non_nan = np.abs(z_scores) > threshold
    
    # Create a boolean array for the entire data, marking NaNs as outliers
    outliers = np.full(data_array.shape, True)  # Default to True for NaN values
    outliers[~nan_mask] = outliers_non_nan
    
    return outliers.tolist()

def replace_outliers_zscore(
    data: Union[List[float], np.ndarray, pd.Series], 
    outliers: List[bool], 
    method: str = "median"
) -> Union[np.ndarray, pd.Series]:
    """
    Replace outliers in a dataset based on Z-score detection with the mean or median of non-outlier values.
    
    Parameters:
    ----------
    data : Union[List[float], np.ndarray, pd.Series]
        The input data containing original values.
    outliers : List[bool]
        A list of booleans indicating whether each value is an outlier (True) or not (False).
    method : str, optional
        The method to replace outliers, either 'median' or 'mean'. Default is 'median'.
        
    Returns:
    -------
    Union[np.ndarray, pd.Series]
        The dataset with outliers replaced by the specified method's value.
    """
    # Convert data to a numpy array for consistent processing
    data_array = np.asarray(data)
    
    # Validate the method parameter
    if method not in {"median", "mean"}:
        raise ValueError("Invalid method. Use 'median' or 'mean'.")
    
    # Compute the replacement value based on the specified method
    non_outliers = data_array[~np.array(outliers)]
    replacement_value = np.median(non_outliers) if method == "median" else np.mean(non_outliers)
    
    # Replace outliers with the calculated value
    data_array[outliers] = replacement_value
    
    # Return the modified data in the same type as the input
    if isinstance(data, pd.Series):
        return pd.Series(data_array, index=data.index)
    elif isinstance(data, list):
        return data_array.tolist()
    return data_array

def identify_clean_outliers(
    df: pd.DataFrame, 
    hrv_variable_name: str = "HRV_RMSSD", 
    method: str = "mean", 
    threshold_z_score: float = 1.96
) -> pd.DataFrame:
    """
    Identifies outliers in a specified HRV variable using the IQR method and replaces them with 
    the median or mean of the non-outlier values.
    
    Parameters:
    ----------
    df : pd.DataFrame
        The input DataFrame containing the data to process. 
        Must include 'segment_name' and the specified `hrv_variable_name`.
    hrv_variable_name : str, optional
        The name of the HRV variable to process. Default is "HRV_RMSSD".
    method : str, optional
        The method to replace outliers, either "median" or "mean". Default is "mean".
    threshold_z_score : float, optional
        The Z-score threshold to determine outliers. Default is 1.96 (i.e., >95%).
        
    Returns:
    -------
    pd.DataFrame
        The original DataFrame with two additional columns:
        - `{hrv_variable_name}_z_score_outlier`: Boolean column indicating outliers.
        - `{hrv_variable_name}_imputed`: Column with outliers replaced by the specified method.
    """
    # Ensure method is valid
    if method not in {"median", "mean"}:
        raise ValueError("Invalid method. Use 'median' or 'mean'.")

    for segment in df['segment_name'].unique():
        subset_df = df[df['segment_name'] == segment].copy()

        rmssd_values = subset_df[hrv_variable_name]
        
        # Identify outliers
        subset_df[f'{hrv_variable_name}_z_score_outlier'] = identify_outliers_zscore(rmssd_values, threshold=threshold_z_score)
        
        # Replace outliers
        subset_df[f'{hrv_variable_name}_imputed'] = replace_outliers_zscore(
            rmssd_values, 
            subset_df[f'{hrv_variable_name}_z_score_outlier'], 
            method=method
        )

        # Update the original DataFrame
        df.loc[df['segment_name'] == segment, f'{hrv_variable_name}_z_score_outlier'] = subset_df[f'{hrv_variable_name}_z_score_outlier'].values
        df.loc[df['segment_name'] == segment, f'{hrv_variable_name}_imputed'] = subset_df[f'{hrv_variable_name}_imputed'].values

    return df

def detect_segment_level_outliers(
    df: pd.DataFrame, 
    hrv_variable_name: str = "HRV_RMSSD", 
    cv_threshold: float = 0.75,
    min_datapoints_required: int = 4
) -> pd.DataFrame:
    """
    Detects segment-level outliers by checking the coefficient of variation (CV) for each segment.
    Also flags segments as outliers if:
      - They contain fewer than 2 non-NaN data points.
      - The standard deviation is zero (indicating no variability).
      - The CV is outside the specified threshold.
    
    Parameters:
    ----------
    df : pd.DataFrame
        The input DataFrame containing the data to process.
    hrv_variable_name : str
        The name of the HRV variable to process.
    cv_threshold : float, optional
        Threshold for the coefficient of variation. Segments with CV greater than this will be flagged.
    min_datapoints_required : int, optional
        Min number of data points needed. If less non-NaN values than specified, the segment is flagged as outlier.
        
    Returns:
    -------
    pd.DataFrame
        Original DataFrame with an additional column 'segment_outlier' indicating segment-level outliers.
    """
    segment_outliers = []
    
    for segment in df['segment_name'].unique():
        segment_data = df[df['segment_name'] == segment][hrv_variable_name]
        
        # Exclude NaN values for calculations
        non_nan_data = segment_data.dropna()
        
        # Check if the segment has fewer than min_datapoints_required non-NaN data points
        if len(non_nan_data) < min_datapoints_required:
            segment_outliers.extend([True] * len(segment_data))
            continue
        
        # Calculate mean and standard deviation
        mean = non_nan_data.mean()
        std = non_nan_data.std()
        
        # Calculate Coefficient of Variation
        cv = std / mean if mean != 0 else np.inf
        
        # Determine if the segment is an outlier
        is_outlier = (cv > cv_threshold) or (std < 0.00001)
        segment_outliers.extend([is_outlier] * len(segment_data))
    
    df['segment_outlier'] = segment_outliers
    return df
