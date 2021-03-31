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

TODO: Add info about using resampling script

### Activity Labeling

TODO: Add info about activity labeling script

### Instance Filtering

TODO: Add info about script which filters data to only labeled instances
