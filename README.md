# Mobile AL Preprocessing Tools

Tools for preprocessing mobile AL CSV data files, for use with AL program and other cases.

These tools provide scripts to do things like resample data to a different frequency, apply labels
to data within certain ranges, and filter out unlabeled data. They all use the new AL CSV data layer
provided by the [Mobile AL Data library](https://github.com/WSU-CASAS/Mobile-AL-Data).

## Setup
After cloning the repository, you will want to initialize the `mobiledata` submodule (Git does not
usually do this for you). Simply run the following commands, which will check out the mobile data
submodule and update it to the needed commit:
```
git submodule init
git submodule update
```

There are no dependencies for this repository, other than Python 3 itself. We have tested this
repository with Python 3.7 and up in Anaconda. Presumably older versions and other implementations
of Python 3 will work, but we have not tested against these.

## Tools
### Resampling

The `resample.py` script is used to resample a CSV AL file to a specified sampling rate. The script
can take in data at any sampling rate, resampling it to the specified rate. The output events will
be at uniform timestamps spaced every `1/sample_rate` seconds apart.

The script uses the following logic to determine how to resample:
1. Determine the `sample_period = 1/sample_rate`
2. Consider all input events with timestamps from the end of the last period (or start) 
   `period_start` to the new period end `period_end = period_start + sample_period`.
3. For each sensor field, get the mean of that sensor's values from input events in the period (if
   the sensor has `float` values) or the last non-`None` value (if a `str` type). For label fields,
   grab the last non-`None` value. Use these to output an event at `period_end` with the computed
   values (downsampling).
4. If there are no input events between `period_start` and `period_end`, use the last seen input
   event's values to create an output event at `period_end` (upsampling). (Note that an input event
   may be repeated as often as needed to get an output for each period.)
5. Repeat 2-4 above for each period of time, ending with the period that contains the last input
   event.
6. If there is a gap of 10 seconds (default) between input events, or an input event is seen that 
   is *before* the start of the current period, then output the current period and restart the
   sampling at the new timestamp.
   
To use the script, simply call it by passing an input file and a sample rate:
```
# Resample to 5Hz:
python resample.py input_file.csv 5.0
```

By default, the output filename will have `sampled` prepended before the `.csv` extension (in the
previous example, the output would be `input_file.sampled.csv`). You can override this with the `-o`
option. (See all options available with `python resample.py --help`.)

### Activity Labeling

TODO: Add info about activity labeling script

### Instance Filtering

TODO: Add info about script which filters data to only labeled instances
