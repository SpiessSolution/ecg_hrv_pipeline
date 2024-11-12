# ECG-HRV Data Processing Pipeline

## Description

This repository contains Python code to preprocess ECG data and to calculate HRV metrics from Mindware recording devices with or without event files. The code essentially combines preprocessing and analysis methods from the [Neurokit2 package](https://neuropsychology.github.io/NeuroKit/ "Link to documentation") with custom workflows used to segment and parameterize the data processing. For a complete overview of the preprocessing and analysis algorithms, the reader is strongly encouraged to throughly go through the [Neurokit2 documentation](https://neuropsychology.github.io/NeuroKit/).

Importantly, the code is primarly tailored towards processing and analysing the dyadic ECG recordings from the WeLoveReading (WLR) study. Nevertheless, the code is modular in nature and so can be adapted to be applicable to other study designs for as long as the Mindware recording device is used.

## Overview of the repository

- **environment.yml:** A text file that contains information about the python packages required to run the pipeline. A package manager such as [Anaconda](https://www.anaconda.com) can be used to create from this file a computing environment that is capable of running the ECG-HRV data processing pipeline.

The repository contains three important directories:

### ~/src/utils directory

- **common.py:** Functions and classes that will probably be used for any project such as code for logging, exporting files, and checking data types. It is unlikely that the existing code needs to be changed when adjusting the overal pipeline to a new experimental setup.
- **data_utils.py:** Contains functionality w.r.t. loading and preparing the input data (i.e., the mindware ECG and Event data) as well as segmenting the data. Since the (structure of) input data might change from one experiment to another (e.g., whether or not dyadic recordings, etc), it is very likely that existing functions need to be adjusted or complemented with new functions tailored to the experimental specifics.
- **parameters.py:** Contains the default parameters (called base_params) as well functions that can be used to change individual settings (e.g., segmentation and/or preprocessing settings) at the dyadic level (for the segmentation parameters) or the individual level (different preprocessing for mother and child).
- **plot_utils.py:** Contains functionality related to producing quality-control visualizations.
- **nk_pipeline.py:** Contains functionality related to the ECG preprocessing and HRV calculations. Most of the functions essentially wrap functionalities provided in the Neurokit2 package. Almost all functions take ECG data and parameters from parameters.py as input and generate either processed ECG data and/or HRV metrics.

### ~/src/app directory

- **analyse_we_love_reading.py:** Contains high-level function combine the functionality from common.py, data_utils.py, parameters.py, plot_utils.py, and nk_pipeline.py into easy-to-understand workflows to preprocess the ECG data and to calculate HRV metrics specifically tailored towards the We Love Reading study.

### ~/notebooks directory

- **ShowCasing the pipeline for WLR.ipynb:** A [Jupyter notebook](https://jupyter.org) with demonstrations on how the pipeline can be used to process the ECG data for the We Love Reading Study. Jupyter notebooks provide an interactive way to execute parts of python code and to inspect the underlying data. Moreover, Jupyter notebooks support Markdown so that code, documentation, and even visualizations can be combined in a single document.

    **>>>>Tip**: It is recommended to use [Microsoft Visual Studio Code ]()to work with Jupyter notebooks.

- It is possible to experiment with the pipeline code in a jupyter notebook and to even run the entire pipeline for all dyads in it. Just make a copy of the notebook that is already there and modify to your needs. At the very top of the notebook, you see that it imports functionalities from common.py, data_utils.py, nk_pipeline.py and so forth.

## How the pipeline works

The pipeline 

**Configuration for the We Love Reading Study**

 By looking at either `~src/app/analyse_we_love_rading.py` or studying `~notebooks/ShowCasing the pipeline for WLR.ipynb` ShowCase 1, we can see that the pipeline does the following things:

1. Looking in the directory `~data/raw` for all text files that end with *_mc.txt to define the ECG recordings and for all files that end with *event.txt to define the events. Output of this step is a list of filepaths for the ECG recordings and a list of filepaths for the events.
2. Using the filepaths from the previous step to (1) import an ECG recording and (2) the corresponding events. It also changes some column names and adjusts the formatting of the event files. Moreover, the ECG recording will be splitted into an ECG timeseries for the mother and an ECG timeseries for the child.
3. In the next step, the parameters for segmentation and preprocessing will be loaded. If adjustments have been made to the parameters in the file `~src/utils/parameters.py` by using either of the two functions in that file, the pipeline will use the subject/dyad ID inferred from the filename and adjust the parameters accordingly.
4. Based on the ECG signal, the event data and the parameters, the ECG signal of the mother and the child will be preprocesed. That is, data cleaning (i.e., filtering) and peak extraction.
5. The preprocessed signal and identified peaks are then segmented based on the segmentation parameters.
6. Next, the HRV metrics such as RMSSD are calculated for every, say 30, non-overlapping seconds of data per segment. The analysis window can be changed to any duration using the (base)parameters in `~src/utils/parameters.py`.
7. Finally, the HRV metrics will be exported separetely for the mother and the child as Excel files. The segmented raw and cleaned, and identified peaks are exported as csv files. Per segment, a quality control visualization will be saved that shows the raw data as well as the cleaned data with the identified peaks. Finally, the parameters are exported separately for the mother and the child.

**Customizing** 

**How to quality control**

## Requirements

**Software requirements**

**Data format requirements**

*Filenames*

*Data schema*

ECG recordings and Event files need to have their timestamp defined in relative time!

--> put pictures to show schema

## Install

## Use

### Input and output parameters

Data format

## Configuring pipeline parameters

Setting the analysis window for the HRV calculations to as long as the 

## Customizing the pipeline

When customizations are needed, those should be done at the lowest level. High-level work flows then need to be adapted as well.

- What really is different across studies might be the data.
  - `prepare_ecg_data()` needs to be modified
  - Some other functions might not be needed (e.g., `split_in_child_mother_series()`, `load_dyad_ecg_events()`, `extract_subject_id_condition_from_filepath()` ) and might need to be removed from higher-level workflows
- Parameters

## Limitations

Event offset = duration instead of dedicated stop event

## Notes

Parameters.segmentation.duration: mention that the duration needs to make sense (i.e., there will not be a check whether the duration of event_onset_e1 includes the onset of event_e2, for example).

ECG data and event date need to have timestamp in relative time (i.e., milliseconds starting at 0)
