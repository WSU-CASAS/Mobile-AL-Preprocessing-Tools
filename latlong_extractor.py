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

if __name__ == '__main__':
    parser = ArgumentParser(description="Extract latitude and longitude pairs from CSV data files.")

    parser.add_argument('input_files', nargs='+', help="Path of CSV file(s) to parse")
    parser.add_argument('-o', '--output-file', type=str, default='latlong',
                        help="Output file name (default %(default)s)")

    args = parser.parse_args()

    output_file = args.output_file
    if output_file is None:
        output_file = 'latlong'
