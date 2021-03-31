"""
Script for resampling CSV Mobile AL data to a new sampling rate.
Outputs new data at specified rate using up/down sampling. Output timestamps will be at uniform
timestamps spaced 1/sample_rate seconds from the starting second of the first input value.
"""
import os
from argparse import ArgumentParser

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

    print(output_file)
