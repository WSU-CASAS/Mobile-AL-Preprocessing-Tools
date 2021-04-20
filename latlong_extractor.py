"""
Script to extract latitude and longitude pairs from CSV data files and write them to a "latlong"
file for mass-reverse-geocoding.

The script will read each of the input files and grab the latitude and longitude from each sensor
event. If the lat/lon are different than the last ones seen, it will write them out to the output
file in the format (just lat and lon space-separated on each line):

lat lon

If the lat/lon are the same as the last seen, it won't write them out since we don't need repeated
copies of the same location.
"""
from argparse import ArgumentParser
from typing import List, Tuple, Optional

from mobiledata import MobileData


def extract_from_files(in_filenames: List[str], out_filename: str):
    last_coords = None  # type: Optional[Tuple[float, float]]

    with open(out_filename, 'a') as out_file:
        for in_filename in in_filenames:
            print(f"Processing {in_filename}")

            with MobileData(in_filename, 'r') as in_data:
                for event in in_data.rows_dict:
                    # Only write the event's lat/long if they don't match the last ones written:
                    if last_coords is None or event['latitude'] != last_coords[0] \
                            or event['longitude'] != last_coords[1]:
                        # Write the event to the file:
                        out_file.write(f"{event['latitude']} {event['longitude']}\n")

                        last_coords = (event['latitude'], event['longitude'])


if __name__ == '__main__':
    parser = ArgumentParser(description="Extract latitude and longitude pairs from CSV data files.")

    parser.add_argument('input_files', nargs='+', help="Path of CSV file(s) to parse")
    parser.add_argument('-o', '--output-file', type=str, default='latlong',
                        help="Output file name (default %(default)s)")

    args = parser.parse_args()

    print(f"Using output file name {args.output_file}")

    extract_from_files(args.input_files, args.output_file)
