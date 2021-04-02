"""
Script to apply labels from a CSV Mobile AL data file to certain ranges of events in the file
preceeding the labels using certain rules.
"""
import os
from argparse import ArgumentParser
from collections import deque
from datetime import timedelta

from mobiledata import MobileData

default_stamp_field = 'stamp'
default_activity_label_field = 'user_activity_label'


class LabelApplier:
    """
    AKA "The Label Apply-inator" :)

    Read in the input file and look for label instances. Apply those labels to windows of events
    from the given window_start to window_end times before the label instance, and write to output
    file. If filter_instances is set, the output file is limited to only events in labeled windows.

    Notes
    -----
    The algorithm will store a queue of input events. As events are seen, they are added to the
    front of the queue. Events more than `window_start` before the newest event are pulled off the
    back of the queue and written to the output file.

    When a label instance is found in the incoming events, events that are pulled from th back of
    the queue (again, `window_start` time before the label) are labeled with that label. This
    continues until `window_end` time before the label is reached, at which it goes back to no
    labels being applied to events. (If a new label is found while still using the old one, then
    we switch to the new label and restart the window time.

    If the events jump backwards in time, then we flush the rest of the queue to the output (with
    labels as needed) and then restart the queue at the new time. (We do not specifically handle
    forward jumps as this is handled by the normal queue windows.) Also, at the end of the file, we
    flush out the remaining events in the queue to make sure we write everything needed.

    When using the filtering, we simply don't write out events that aren't labeled.
    """

    def __init__(self, in_file: str, out_file: str, window_start_s: float, window_end_s: float,
                 filter_instances: bool = False):
        """
        Set up the LabelApplier

        Parameters
        ----------
        in_file : str
            Name of the input file to read events from
        out_file : str
            Name of the output file to write events to
        window_start_s : float
            Seconds before a label to start window of events that get that label
        window_end_s : float
            Seconds before a label to end window of events that get that label
        filter_instances : bool, default False
            If True, only write labeled events to the output file
        """

        self.in_file = in_file
        self.out_file = out_file

        # Set up the input/output file objects:
        self.in_data = MobileData(in_file, 'r')
        self.out_data = MobileData(out_file, 'w')

        # Set window start/end deltas:
        self.window_start = timedelta(seconds=window_start_s)
        self.window_end = timedelta(seconds=window_end_s)

        # Whether to filter to only labeled instances:
        self.filter_instances = filter_instances

        # Queue to store incoming events:
        self.event_queue = deque()

        # Store the field names for stamp and activity label:
        self.stamp_field = default_stamp_field
        self.label_field = default_activity_label_field

    def run_labels(self):
        """Actually run the label application"""

        self.in_data.open()
        self.out_data.open()

        try:
            # Get the fields from the input file and set them/write headers in output:
            fields = self.in_data.fields

            self.out_data.set_fields(fields)
            self.out_data.write_headers()

            for in_event in self.in_data.rows_dict:
                print(in_event)
        finally:
            self.in_data.close()
            self.out_data.close()


if __name__ == '__main__':
    parser = ArgumentParser(
        description="Script to apply labels to windows of data before the label instance."
    )

    parser.add_argument('input_file', type=str, help="AL CSV input file to read in")
    parser.add_argument(
        '-o', '--output-file', type=str,
        help="Output file name (defaults to the input with 'labeled' added before extension, or 'instances' if --filter-instances is set)"
    )

    parser.add_argument('-ws', '--window-start', type=float, default=5*60.0,
                        help="Seconds before a label to start its window (default %(default)s s)")
    parser.add_argument('-we', '--window-end', type=float, default=0.0,
                        help="Seconds before a label to end its window (default %(default)s s)")

    parser.add_argument('-f', '--filter-instances', action='store_true',
                        help="If set, filter output to only include labeled instances")

    args = parser.parse_args()

    # If the output file name is not set, use the input but add 'labeled' or 'instances' depending
    # on whether we're filtering to only instances:
    output_file = args.output_file
    if output_file is None:
        filename, extension = os.path.splitext(args.input_file)

        if args.filter_instances:
            # Add 'instances':
            new_extension = f'.instances{extension}'
        else:
            # Add 'filtered':
            new_extension = f'.filtered{extension}'

        output_file = f'{filename}{new_extension}'

    # Verify the window start/end times are sensible:
    if args.window_start < 0:
        msg = f"Window start of {args.window_start} is invalid - must be non-negative"
        raise ValueError(msg)

    if args.window_end < 0:
        msg = f"Window end of {args.window_end} is invalid - must be non-negative"
        raise ValueError(msg)

    if args.window_start < args.window_end:
        msg = "Window start cannot be less than window end"
        raise ValueError(msg)

    print(f"Applying labels to windows of {args.window_start}-{args.window_end}s before labels")
    print(f"Reading file {args.input_file} and writing to {output_file}")

    if args.filter_instances:
        print("Output will be filtered to only instances")

    label_applier = LabelApplier(args.input_file, output_file, args.window_start, args.window_end,
                                 args.filter_instances)

    label_applier.run_labels()
