"""
Script for resampling CSV Mobile AL data to a new sampling rate.
Outputs new data at specified rate using up/down sampling. Output timestamps will be at uniform
timestamps spaced 1/sample_rate seconds from the starting second of the first input value.
"""
import os
from argparse import ArgumentParser
from datetime import timedelta, datetime
from statistics import mean
from typing import Dict, Optional, Union, List
from warnings import warn

from mobiledata import MobileData


# Configuration to exclude non-sensor fields from sampling (only last label in each interval is
# output for resampled data):
stamp_field = 'stamp'  # name of the timestamp field in the CSV data
label_fields = ['user_activity_label']  # name(s) of non-sensor labels in the CSV data

status_num_events_interval = 1000  # number of input events between status updates


class Resampler:
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
    """

    def __init__(self, in_file: str, out_file: str, sample_rate: float):
        """
        Set up the resampler, but don't actually process anything yet.

        Parameters
        ----------
        in_file : str
            Path to the input file to read data from
        out_file : str
            Path to the output file to write resampled data to
        sample_rate : float
            The new rate to resample to (in Hz)
        """

        self.in_file = in_file
        self.out_file = out_file

        # Set up the input/output file objects:
        self.in_data = MobileData(in_file, 'r')
        self.out_data = MobileData(out_file, 'w')

        # Hold information about the different fields to use:
        # All fields in the input file:
        self.all_fields = None  # type: Optional[Dict[str, str]]

        # Stamp field name:
        self.stamp_field = stamp_field

        # Only sensor fields:
        self.sensor_fields = None  # type: Optional[Dict[str, str]]

        # List of label fields:
        self.label_fields = label_fields

        # Determine the output sample interval in seconds:
        self.sample_interval = timedelta(seconds=1.0 / sample_rate)

        # The previous and next output stamps to use:
        self.prev_out_stamp = None  # type: Optional[datetime]
        self.next_out_stamp = None  # type: Optional[datetime]

        # The next event from the input file:
        self.next_input_event = None  # type: Optional[Dict[str, Union[float, str, datetime, None]]]

        # The last-seen input event:
        self.last_seen_input_event = None  # type: Optional[Dict[str, Union[float, str, datetime, None]]]
        # TODO: Make sure this is cleared if we 'jump' in time and reset

        # Information about input events seen in a sample interval:
        self.num_events_in_interval = 0
        self.interval_sensor_values = None  # type: Optional[Dict[str, List[float, str]]]
        self.interval_labels = None  # type: Optional[Dict[str, List[str]]]

        # Status update info:
        self.status_num_events_interval = status_num_events_interval
        self.num_input_events_processed = 0
        self.num_events_since_last_status = 0
        self.first_event_stamp = None  # type: Optional[datetime]

    def run_resample(self):
        """
        Actually run the resampling.
        """

        self.in_data.open()
        self.out_data.open()

        try:
            # Get the fields from the input file and set them/write headers in output:
            self.all_fields = self.in_data.fields

            self.out_data.set_fields(self.all_fields)
            self.out_data.write_headers()

            # Set up the sensor fields by removing non-sensor fields:
            self.set_sensor_only_fields()

            # Read the first event from the input file:
            self.get_next_input_event()

            # Warn and exit if we have no input data to read:
            if self.next_input_event is None:
                msg = f"The input file {self.in_file} did not have any data rows"
                warn(msg)

                return

            self.first_event_stamp = self.next_input_event[self.stamp_field]

            # Determine the starting output stamp to use as a base by truncating the first input
            # stamp to seconds:
            self.prev_out_stamp = self.next_input_event[stamp_field].replace(microsecond=0)

            # Now iterate through the output intervals:
            while True:
                self.process_next_interval()
        except EOFError:  # catch when we are at the end of the file
            pass
        finally:
            self.in_data.close()
            self.out_data.close()

            print()  # make sure we go to a new output line

    def set_sensor_only_fields(self):
        """Remove all but sensor fields from the fields dictionary."""

        self.sensor_fields = dict(self.all_fields)

        del self.sensor_fields[stamp_field]

        for label_field in label_fields:
            del self.sensor_fields[label_field]

    def get_next_input_event(self):
        """Get next input event from the file."""

        self.next_input_event = next(self.in_data.rows_dict, None)

    def process_next_interval(self):
        """Process the next output interval and any events that should go into it."""

        # Set up the stamp at the end of the next interval:
        self.next_out_stamp = self.prev_out_stamp + self.sample_interval

        # Collect all events and labels in the sample interval:
        self.reset_for_interval()

        while self.next_input_event is not None \
                and self.next_input_event[stamp_field] <= self.next_out_stamp:
            self.num_events_in_interval += 1

            for sensor in self.sensor_fields.keys():
                if self.next_input_event[sensor] is not None:
                    self.interval_sensor_values[sensor].append(self.next_input_event[sensor])

            for label_name in label_fields:
                if self.next_input_event[label_name] is not None:
                    self.interval_labels[label_name].append(self.next_input_event[label_name])

            # Save this input event as last seen:
            self.last_seen_input_event = dict(self.next_input_event)
            self.num_input_events_processed += 1
            self.num_events_since_last_status += 1

            self.get_next_input_event()

        # Now write out the event (if possible):
        self.write_event_for_interval()

        # Check if we've reached the end of the file (no more input events):
        if self.next_input_event is None:
            # Force printing status one last time:
            self.print_status(self.next_out_stamp, force_status=True)
            raise EOFError()

        # Prepare for the next interval:
        self.prev_out_stamp = self.next_out_stamp

        # Print status if needed:
        self.print_status(self.prev_out_stamp)

    def reset_for_interval(self):
        """Reset variables tracking events seen in an interval."""

        self.num_events_in_interval = 0
        self.interval_sensor_values = {sensor: [] for sensor in self.sensor_fields.keys()}
        self.interval_labels = {label_name: [] for label_name in label_fields}

    def write_event_for_interval(self):
        """
        Writes an event (if any) that should be output at the end of the current interval, based on
        the events seen within that interval.
        """

        if self.num_events_in_interval > 0:
            # We have some events, so compute the sensor values and labels from the window:
            sensor_vals_to_write = self.get_sensor_values_for_out_event()
            label_vals_to_write = self.get_label_vals_for_out_event()

            self.write_out_event(self.next_out_stamp, sensor_vals_to_write, label_vals_to_write)
        else:
            # We didn't have any events, so use the last one we saw, if any:
            if self.last_seen_input_event is not None:
                # We have a recently-seen event, so just use that:
                self.out_data.write_row_dict(self.last_seen_input_event)
            else:
                # We don't have any events to write, so just skip this time
                pass

    def get_sensor_values_for_out_event(self) -> Dict[str, Union[float, str, None]]:
        """
        Compute the sensor values to write at end of an interval based on the input values seen in
        the interval and return them.
        """

        sensor_vals = {}

        for sensor, val_type in self.sensor_fields.items():
            vals_from_interval = self.interval_sensor_values[sensor]

            if len(vals_from_interval) < 1:  # this sensor was not seen in the interval
                sensor_vals[sensor] = None
            elif val_type == 'f':  # float values, so grab mean
                sensor_vals[sensor] = mean(vals_from_interval)
            else:  # str values, so grab last one
                sensor_vals[sensor] = vals_from_interval[-1]

        return sensor_vals

    def get_label_vals_for_out_event(self) -> Dict[str, Optional[str]]:
        """
        Compute the labels from those seen in an interval, using the last one of each type seen (if
        any) for that label.
        """

        label_vals = {}

        for label_name in self.label_fields:
            vals_from_interval = self.interval_labels[label_name]

            if len(vals_from_interval) < 1:  # this label was not seen in the interval
                label_vals[label_name] = None
            else:  # use the last instance of this label seen in the interval
                label_vals[label_name] = vals_from_interval[-1]

        return label_vals

    def write_out_event(
            self,
            stamp: datetime,
            sensor_vals: Dict[str, Union[float, str, None]],
            label_vals: Dict[str, Optional[str]]
    ):
        """Write out the given values to the output file."""

        # Form the dictionary to write:
        event_dict = {
            self.stamp_field: stamp,
            **sensor_vals,
            **label_vals
        }

        self.out_data.write_row_dict(event_dict)

    def print_status(self, current_interval_end: datetime, force_status: bool=False):
        """Print a status message if we've processed a certain number of events."""

        # Only update if we've reached the next threshold:
        if self.num_events_since_last_status > self.status_num_events_interval or force_status:
            first_stamp_str = self.first_event_stamp.strftime("%Y-%m-%d %H:%M:%S") \
                if self.first_event_stamp is not None else "?"
            current_stamp_str = current_interval_end.strftime("%Y-%m-%d %H:%M:%S")

            # Print status over previous status:
            print(
                f"Processed {self.num_input_events_processed} events ({first_stamp_str} to {current_stamp_str})              ",
                end='\r'
            )

            self.num_events_since_last_status = 0


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

    # Set up the resampler and then run it:
    resampler = Resampler(args.input_file, output_file, args.resample_rate)
    resampler.run_resample()
