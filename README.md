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

The `apply_labels.py` script can be used to take individual label instances in the input file and
apply them to time-based windows of events for output. This is useful if you have single-event
labels at the "instant" when the user provided them, and want to apply them to a range of events
that should be considered part of that activity.

The script looks for labels in the input data. When it finds one, it applies that label to all
events from `window_start` to `window_end` seconds before the labeled event's stamp in the output.
So, for example, if you see `Cook` at `12:00:00`, the default settings will apply the `Cook` label
to all events from `11:55:00` to `12:00:00` in the output.

If a new label is encountered while in the midst of a previous label's window, the script first
finishes the previous label's window before switching to the new label (if any of its window remains
at that point).

If the events in the input file jump backwards in time, the events before the jump will be flushed
out before the processing restarts with the new event.

Basic usage is as follows:
```
python apply_labels.py input_file.csv
```

This will use the following:
- Input file is `input_file.csv`
- Output file name will have `labeled` inserted before the `.csv` extension: 
  `input_file.labeled.csv`
- Each label in the input will be applied to a window from 5 minutes (`window_start`) to 0 seconds 
  (`window_end`) before the label's timestamp.
  
You can modify the `window_start` and `window_end` values using the `-ws` and `-we` parameters,
respectively. You can also change the output file name using `-o`.

Finally, the script provides the option to filter the output to only include labeled data with the
`-f` option. If this option is used, only events that will have a label (i.e. fall into a label's
window) will be written to the output. This also changes the default output file name to use
`instances` instead of `labeled`.
