"""
Script for resampling CSV Mobile AL data to a new sampling rate.
Outputs new data at specified rate using up/down sampling. Output timestamps will be at uniform
timestamps spaced 1/sample_rate seconds from the starting second of the first input value.
"""
import os
from argparse import ArgumentParser
from datetime import timedelta, datetime
from typing import Dict, Optional, Union
from warnings import warn

from mobiledata import MobileData


# Configuration to exclude non-sensor fields from sampling (only last label in each interval is
# output for resampled data):
stamp_field = 'stamp'  # name of the timestamp field in the CSV data
label_fields = ['user_activity_label']  # name(s) of non-sensor labels in the CSV data


def resample(in_file: str, out_file: str, sample_rate: float):
    """
    Resample the given input file to the specified rate and write to the output file. The output
    data will be at uniform timestamps at the given rate starting from the second when the first
    event of the input file occurs.

    TODO: Add checks for going back in time or skipping too far ahead in the input data, at which
    point we will need to restart our sampling.

    Notes
    _____
    This function is able to handle both up- and down-sampling of the input data. The general
    algorithm is as follows:

    1. Start by calculating the `sample_interval`:
    `sample_interval = 1.0 / sample_rate  # get the sample interval in seconds`

    2. Set the first timestamp for output to be the start of the second containing the first
    timestamp in the input file:
    `out_stamp = first_input_stamp.replace(microsecond=0)  # truncate fraction of starting stamp s`

    3. Repeat the following process up to and including when `next_out_stamp` is past the last
    timestamp in the input file (`next_out_stamp >= last_input_stamp`):

      i. Compute the next output stamp:
      `next_out_stamp = out_stamp + sample_interval`

      ii. Collect the values for each sensor for all input file timestamps between `out_stamp` and
      `next_out_stamp`, tracking each sensor's values in separate lists.

      iii. If one or more input events was found in the interval, write an event to the output file
      at `next_out_stamp` with the means of the collected values for each sensor. If any sensors are
      string (non-float) values, only use the last value of that sensor in the output. If any of the
      interval events had a label, use the newest of the labels to label the output event.

      iv. If there were no input events in the interval, write the values of the previous input
      event seen (whenever that occurred) to the output file at `next_out_stamp`. Include any
      previous label.

      v. If we have not seen *any* events yet (i.e. we have not passed the first event in the input
      file), then don't write anything at stamp `next_out_stamp` and proceed to the next step:

      vi. Set `out_stamp = next_out_stamp`.

    In this way, the code should handle: upsampling, where we want to repeat each event to fill the
    needed time intervals; and downsampling, where we take the mean of events in each interval and
    output them.

    Parameters
    ----------
    in_file : str
        Path to the input file to read data from
    out_file : str
        Path to the output file to write resampled data to
    sample_rate : float
        The new rate to resample to (in Hz)
    """

    # Determine the output sample interval in seconds:
    sample_interval = timedelta(seconds=1.0 / sample_rate)

    with MobileData(in_file, 'r') as in_data, MobileData(out_file, 'w') as out_data:
        # Get the fields from the input file and set them/write headers in output:
        fields = in_data.fields

        out_data.set_fields(fields)
        out_data.write_headers()

        # Set up the sensor fields by removing non-sensor fields:
        sensor_fields = get_sensor_only_fields(fields)

        # Read the first event from the input file:
        next_input_event = next(in_data.rows_dict, None)

        # Warn and exit if we have no input data to read:
        if next_input_event is None:
            msg = f"The input file {in_file} did not have any data rows"
            warn(msg)

            return

        # Determine the starting output stamp (not actually written to output, but used as base):
        prev_out_stamp = next_input_event[stamp_field].replace(microsecond=0)  # truncate to seconds

        # Store the last input event (if any):
        last_seen_input_event = None  # type: Optional[Dict[str, Union[float, str, datetime, None]]]

        # Now iterate through the output intervals:
        while True:
            next_out_stamp = prev_out_stamp + sample_interval

            # Collect all events and labels in the sample interval:
            num_events_in_interval = 0
            interval_sensor_values = {sensor: [] for sensor in sensor_fields.keys()}
            interval_labels = {label_name: [] for label_name in label_fields}

            while next_input_event is not None and next_input_event[stamp_field] <= next_out_stamp:
                num_events_in_interval += 1

                for sensor in sensor_fields.keys():
                    if next_input_event[sensor] is not None:
                        interval_sensor_values[sensor].append(next_input_event[sensor])

                for label_name in label_fields:
                    if next_input_event[label_name] is not None:
                        interval_labels[label_name].append(next_input_event[label_name])

                next_input_event = next(in_data.rows_dict, None)


def get_sensor_only_fields(all_fields: Dict[str, str]) -> Dict[str, str]:
    """Remove all but sensor fields from a fields dictionary."""

    sensor_fields = dict(all_fields)

    del sensor_fields[stamp_field]

    for label_field in label_fields:
        del sensor_fields[label_field]

    return sensor_fields


if __name__ == '__main__':
    parser = ArgumentParser(description="Script to resample CSV Mobile AL data to specified rate.")

    parser.add_argument(
        'input_file', type=str,
        help="AL CSV input file to use as input for resampling"
    )

    parser.add_argument(
        '-o', '--output-file', type=str,
        help="Output file name (defaults to the input with 'sampled' added before extension"
    )

    parser.add_argument('resample_rate', type=float, help="Rate to resample data to (Hz)")

    args = parser.parse_args()

    # If the output file name is not set, use the input adding 'sampled' before the extension:
    output_file = args.output_file
    if output_file is None:
        filename, extension = os.path.splitext(args.input_file)

        new_extension = f'.sampled{extension}'

        output_file = f'{filename}{new_extension}'

    print(f"Resampling data in {args.input_file} to {output_file} at {args.resample_rate}Hz")

    resample(args.input_file, output_file, args.resample_rate)
