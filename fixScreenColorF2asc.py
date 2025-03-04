import configparser
import re
import copy
import sys
import tempfile
import pdb
import difflib
import pandas as pd
from jinja2 import Environment, FileSystemLoader
import os
from colorama import Fore, Back, Style

# Where you see WHITE B_BLACK in the ASCII version of the JAM screen as the colors of widgets 
# it's because it needs the SCHEME B_SCHEME instead

if (len(sys.argv) == 2) :
    screenName = sys.argv[1]
    print("fixScreenColorF2asc will scan the jam ascii file for WHITE B_BLACK or similar,")
    print("and replace it with SCHEME B_SCHEME .")
else:
    print("Usage: fixScreenColorF2asc <screenname.jam.asc>")
    print("fixScreenColorF2asc will scan the jam ascii file for WHITE B_BLACK or similar,")
    print("and replace it with SCHEME B_SCHEME .")
    print("If screen name is blank or not found it will exit.")
    sys.exit()

# Uncommenting the pdb line opens the debugger in the command line
# pdb.set_trace()

# True Main functionality is below def's.
def readScreen(screenName):

    curFieldName = ""
    numLinesScreenFile = 0
    # The regular expression pattern
    pattern = r"WHITE B_\S+"
  
    # The replacement string
    replacement = "SCHEME B_SCHEME"
    # Searching for the pattern
    
    with open(screenName, "r") as screenFile:
        with open( screenName + ".out", 'w') as outfile:
            while (line := screenFile.readline()):
                fieldMatch = re.match(r"\s*[GLFBYT]:(\S*)\s*$", line)
          
                if (fieldMatch) :
                    curFieldName = fieldMatch.group(1)
                # Searching for the pattern
                match = re.search(pattern, line)

                if match:
                    print("found:",curFieldName, end=" ")
                    print("Value:",match.string.replace("\n",""), end=" ")
                    print("Replaced with: ",replacement)
                    numLinesScreenFile = numLinesScreenFile + 1
                    updated_text = re.sub(pattern, replacement, line)
                    outfile.write(updated_text)
                else:
                    outfile.write(line)
                
    return numLinesScreenFile

# ---------------------------------------------------------------------------------------
# PROGRAM START (after def's and variables above)

file_path_os = screenName
if os.path.exists(file_path_os):
    print(f"Processing {file_path_os} .")
else:
    print(f"File {file_path_os} does not exist.")
    sys.exit()

fldcounter = readScreen(file_path_os)

if (fldcounter == 0):
    os.remove(file_path_os + "out")
    print("Completed Color Fixup - No Fields Found in "+file_path_os+"\n")
else:
    print("Completed Color Fixup - Fields processed="+str(fldcounter)+"\n")
    print("New Ascii file - "+file_path_os+".out\n")

# Usage




