# Parser and Aggregator for Intigeo Data Loggers

**parse-logger-.py** - Parses and aggregates data files created by [Intigeo series geolocators](https://www.migratetech.co.uk/geolocators_8.html)

*Usage:* python parse-logger.py DIRECTORY

The directory provided as an argument should contain data files for a single animal.  The resulting CSV data will be sent to STDOUT, and can be piped to a file.

---

**parse.sh** - Wrapper for parse-logger.py that iterates over a directory and executes the script for all subdirectories within it, outputting a separate CSV file for each one containing data files for an animal.

*Usage:* sh parse.sh

This script assumes there is a subdirectory named **data** within the current working directory.  It will iterate over all subdirectories within **data** and generate a CSV file for it in a directory named **out** in the current working directory.
