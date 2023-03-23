#!/bin/python
#
# Any line that has a # as the first non-whitespace character is a comment. You may see some scripts
# start with a line like the first one in this file.  It's known as a "shebang", and instructs Unix-
# like systems how to execute the script, so that they can be run like a normal program
#

#
# import loads additional libraries that may be needed by the script.  Some of these are part of the
# default python installation, but sometimes they may have to be installed with the 'pip' command
#
import sys
import os
import re
import csv
import glob
import time

#
# You can choose to import only certain parts of a library as well
#
from datetime import datetime
from collections import OrderedDict,defaultdict

#
# Hey! Our first bit of actual code.  This is just a variable storing how many hours the times need
# to be adjusted by to make it local to where the loggers were used.
#
timezone_offset = 4

#
# def defines a function.  Here we are making a parse_time function that takes a date in the string
# format of "06/10/2022 13:35:33", and turns it into a unix timestamp, which is the number of seconds
# that have passed since Midnight on Jan 1 1970.  This time is known as the Unix Epoch.
#
def parse_time(timestring):
    try:
        return int(time.mktime(datetime.strptime(timestring, '%d/%m/%Y %H:%M:%S').timetuple()))
    except:
        return 0

#
# Python is white space based (which is one of the main things I don't like about it).  When you start
# a function, or a conditional block like an if statement (which you will see later), you indent the body
# of the function of conditional.  It's common to use 4 spaces as the indentation.  You can use a tab, or
# any number of spaces, but they need to be uniform.  When another line is indented by the same amount
# as the line that started the block (the def or if), then the block ends.  Comments do not count, so
# the function definition below would be the first line that is no longer part of the function above
#

#
# This function converts the unix timestamp back to a string with the format of "2022-10-06 13:35:33"
#
def time_to_string(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

#
# This is the meat of the script.  It parses individual log files.
#
def read_data_file(path):
    #
    # Create an ordered dictionary to store the data from the file.  Dictionaries will be talked about
    # further down.
    #
    data = OrderedDict([])

    #
    # This is a mapping of the header values used in the different logger files, to how they are stored
    # in our data dictionaries for processing
    #
    fields = OrderedDict([
        ("T('C)",       "temp"),
        ("light(lux)",  "light"),
        ("wets0-50",    "wets"),
        ("wet min('C)", "wet_temp_min"),
        ("wet/dry",     "wetdry"),
        ("duration",    "duration")
    ])

    #
    # These are variables used for processing.  They will be explained as we go.
    #
    start   = 0
    end     = 0
    drift   = 0
    dps     = 0
    field   = None
    in_data = False
    match   = None

    #
    # try/except blocks are used to handle errors.  If an error is thrown in the "try" block, then
    # the "except" block will be executed.  This is needed to ensure that processing does not stop
    # if an error is encountered.
    #
    try:
        #
        # "with" blocks create variables that are only visible in their blocks of code.  It will also
        # clean up any used resources automatically, to avoid resource leaks.  In this case, we are
        # opening a file, and it will automatically be closed when the "with" block completes.
        #
        with open(path, 'r') as file:
            #
            # "file" is a file handle, but python lets you read from it as if it was an array if you
            # want to
            #
            for line in file:
                #
                # strip() just removes the new line characters from the end of the line
                line = line.strip()

                #
                # "in_data" is a variable that indicates whether or not we are in the data section of the
                # file or still processing the headers.
                #
                if in_data:
                    #
                    # if we are in the data section, we use split() to split the line into an array using
                    # tabs (\t) as the delimiter
                    #
                    row = line.split("\t")

                    #
                    # if the first item is empty just ignore the line and goto the next
                    #
                    if not row[0]:
                        continue

                    #
                    # parse the time into a unix timestamp.  if the time can't be parsed correctly,
                    # just move on to the next line
                    #
                    time = parse_time(row[0])
                    if time < 1:
                        continue

                    #
                    # "dps" is "delta per second".  It's the amount of skew that should be applied per second of
                    # time to the times in the log files.  "time" minus "start" is how many seconds have passed
                    # since the start of the log file.  Multiple that by the "dps" value to get the amount of skew,
                    # and then add that to the time stamp.  Sometimes "dps" will be negative, so adding it has the
                    # same effect as subtracting the skew.
                    #
                    adjtime = time + (dps * (time - start))

                    #
                    # Set the local time to be the adjusted time minus the timezone offset
                    #
                    localtime = adjtime - 3600 * timezone_offset

                    #
                    # Convert the "adjtime" timestamp back to a string time and store in "atime"
                    #
                    atime = time_to_string(adjtime)

                    #
                    # if "atime" does not already exist in the data dictionary, then create it
                    #
                    if atime not in data.keys():
                        data[atime] = {}

                    #
                    # Store the time and local time as strings in the data dictionary
                    #
                    data[atime]['time']      = time_to_string(time)
                    data[atime]['localtime'] = time_to_string(localtime)

                    #
                    # This assigns the data from the file to the proper fields depending on the type of file it is.
                    # "elif" is like doing "else if".
                    if (field == 'wetdry'):
                        data[atime]['wetdry']   = row[2]
                        data[atime]['duration'] = row[1]
                    elif (field == 'wet_temp_min'):
                        data[atime]['wet_temp_min']     = row[1]
                        data[atime]['wet_temp_max']     = row[2]
                        data[atime]['wet_temp_mean']    = row[3]
                        data[atime]['wet_temp_samples'] = row[4]
                    else:
                        data[atime][field] = row[1]

                #
                # Remember this lines up with the "if" statement above that checks the "in_data" variable.
                # If we aren't in data, it means we are still processing the headers.  Each of these is a "regular
                # expression" that is used to match strings.  Those are a whole different lesson.
                #
                # This is the header at the start of the data rows. Once this line is seen, the "in_data" variable
                # is set to true.
                #
                elif (m := re.match(r'^DD/MM/YYYY HH:MM:SS\t(.*?)(\t(.*?))?$', line)):
                    field = fields[m.group(1)]
                    if (field == 'duration'):
                        field = 'wetdry'

                    in_data = True

                #
                # since we are still aligned with the elif above, this is part of the if/elif/else that started with
                # the check to see if we were in data.  It's looking for the line that says when you programmed the
                # data logger, and saves the time to "start"
                #
                elif (m := re.match(r'^Programmed: (.*?)\.', line)):
                    start = parse_time(m.group(1))

                #
                # Still aligned, this only executes if the previous if and two elifs aren't true.  This looks for
                # when you stopped the logger and saves the time to "end"
                #
                elif (m := re.match(r'^End of logging \(DD/MM/YYYY HH:MM:SS\): (.*?)$', line)):
                    end = parse_time(m.group(1))

                #
                # Last, look for the line that gives us the drift, and use that to calculate the "dps".  We calculate
                # that by taking the amount of drift divided by the number of seconds between "start" and "end"
                elif (m := re.match(r'^Drift \(secs\): (.*?)\.', line)):
                    drift = int(m.group(1))
                    dps = drift / (end - start)

    #
    # If there is an error opening the file, just report it.
    #
    except IOError:
        print("Could not read file:", path)

    #
    # this exits the funtion and returns data back to what ever called it.
    #
    return data

#
# This is where execution of our code starts when you run the script.  You can put the function
# definitions later if you want, but it's pretty common to define functions before they are used.
#

#
# sys.argv is an array (called lists in Python, but I am used to calling them arrays) that contains
# command line arguments.  First we check if at least 2 arguments are given (the program name itself
# counts as one), and also if the second argument is a directory that exists.  If either thing is
# not true, it prints a message and quits.
#
if (len(sys.argv) < 2 or not os.path.isdir(sys.argv[1])):
    print("USAGE:", sys.argv[0], "[FOLDER]\n")
    quit()

#
# First we save the command line argument to a variable named "path" just to make it easier to reference.
# and then we get a list of files from that directory.  The first glob() call returns an array of files
# that we save in the "files" variable.  Then we use the extend() method on the array to append the results
# of the next two glob calls.
#
# NOTE:  We are calling glob.glob here, because up above the script imported the whole glob library.  You
# can do:
#
#     from glob import glob
#
# so that you can just call glob() instead of glob.glob()
#
path = sys.argv[1]
files = glob.glob(path + '/*.deg')
files.extend(glob.glob(path + '/*.lux'))
files.extend(glob.glob(path + '/*.sst'))

#
# Dictionaries are at type of data in Python that allow you to store key/value pairs.  You can assign data
# by doing:
#
#     dict[key] = value
#
# By default, the order of data in the dictionary is not preserved, so we are using an OrderedDict for our
# data to ensure we can sort it and maintain order.  We pass an empty array to the OrderedDict() method to
# create an empty ordered dictionary.
#
output = OrderedDict()

#
# "files" is the array of file names that we created above.  We use a "for" loop to iterate over it.  For
# each iteration, the variable "file" is filled in as the current value.
#
for file in files:
    #
    # This checks to see if the string 'driftadj' is part of the filename.  If it is, we use "continue"
    # to move to the next iteration without doing anything more.
    #
    if 'driftadj' in file:
        continue

    #
    # This just logs the filename to stderr.  By sending it to stderr, you can pipe the output of the program
    # to a file, but this will still show in the console.
    #
    print(file, file=sys.stderr)

    #
    # Pass the filename to the read_data_file() function we created above, and save the result in a variable
    # name "data"
    #
    data = read_data_file(file)

    #
    # The result of read_data_file is a dictionary.  You can iterate over a dictionary with "for" the same way
    # you do with an array, but you can capture the key name along with the value.  In this case, we are storing
    # the key as "date", and the value in "values".
    #
    for date,values in data.items():
        #
        # Check to see if the date already exists in our output dictionary.  If it doesn't, then set it to an
        # empty dictionary to avoid KeyErrors
        #
        if date not in output.keys():
            output[date] = {}

        #
        # Here we iterate over an array of field names, check if they exist in the data from the file, and if so
        # merge them into the output.  If the field does not exist in the data, just set it to a null value, which
        # is "None" in python.  This avoids some KeyErrors later when we output the data.
        #
        for field in ['time','localtime','temp','wets','light','wetdry','duration','wet_temp_min','wet_temp_max','wet_temp_mean','wet_temp_samples']:
            if field in values.keys():
                output[date][field] = values[field]
            elif field not in output[date].keys():
                output[date][field] = None

#
# All files have been read at this point.  We need to clean up the data by interpolating some values so there
# are not any gaps.  First we need to sort the data in reverse order by time, so we can interpolate wet/dry
# and water temp values
#

#
# We create an array called "keys" that stores a reverse sorted array of dates from the "output" dictionary.
#
keys = sorted(output.keys(), reverse=True)

#
# Then use the sorted keys to create a temporary dictionary, so that the keys are in order
#
temp = OrderedDict()
for key in keys:
    temp[key] = output[key]

#
# "state" is a dictonary used to store the current values that we need to fill into the blanks
#
state = dict()

for time,values in temp.items():
    #
    # Check to see if the current time has wet values set.  Set the state to the current value.
    #
    if 'wet_temp_min' in values.keys() and values['wet_temp_min'] != None:
        state['wet_temp_min'] = values['wet_temp_min']
        state['wet_temp_max'] = values['wet_temp_max']
        state['wet_temp_mean'] = values['wet_temp_mean']
        state['wet_temp_samples'] = values['wet_temp_samples']

    #
    # If the state contains wet values, and if so, fill it into the current time.  In cases where wet
    # values were already set, this is redundant, but doesn't cause any problems.
    #
    if 'wet_temp_min' in state.keys():
        values['wet_temp_min'] = state['wet_temp_min']
        values['wet_temp_max'] = state['wet_temp_max']
        values['wet_temp_mean'] = state['wet_temp_mean']
        values['wet_temp_samples'] = state['wet_temp_samples']

    #
    # Same as above, but for some other values
    #
    if 'wetdry' in values.keys() and values['wetdry'] != None:
        state['wetdry'] = values['wetdry']
        state['duration'] = values['duration']

    if 'wetdry' in state.keys():
        values['wetdry'] = state['wetdry']

    #
    # Save the modified values into our temporary dictionary
    #
    temp[time] = values

#
# With all the values interpolated, we sort the temp dictionary in forward order, and save it back to
# the output dictionary
#
keys = sorted(temp.keys(), reverse=False)
output = OrderedDict()
for key in keys:
    output[key] = temp[key]

#
# The data is now done being processed, and we just need to dump it to a CSV file.  You can use the "csv"
# library to write to files or to stdout.  I choose to write to stdout... I don't know why, but that's what
# I did.
#
writer = csv.writer(sys.stdout)

#
# Write the header row of the csv
#
writer.writerow(['Adjusted UTC Time','Adjusted Local Time','Original UTC Time','Temp','Light','Wets','Wet/Dry','Duration','Wet Temp (min)','Wet Temp (max)','Wet Temp (mean)','Wet Temp (samples)'])

#
# Iterate over the output, and write each data point as a row in the csv file
#
for time,values in output.items():
    writer.writerow([time, values['localtime'],values['time'],values['temp'],values['light'],values['wets'],values['wetdry'],values['duration'],values['wet_temp_min'],values['wet_temp_max'],values['wet_temp_mean'],values['wet_temp_samples']])

