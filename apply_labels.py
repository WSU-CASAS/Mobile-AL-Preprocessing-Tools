"""
Script to apply labels from a CSV Mobile AL data file to certain ranges of events in the file
preceeding the labels using certain rules.
"""
import os
from argparse import ArgumentParser

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

    print(f"Applying labels to windows of {args.window_start}-{args.window_end}s before labels")
    print(f"Reading file {args.input_file} and writing to {output_file}")

    if args.filter_instances:
        print("Output will be filtered to only instances")
