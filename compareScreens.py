import re
import copy
import sys
import tempfile
import pdb
import difflib
import pandas as pd

if (len(sys.argv) < 3) or (len(sys.argv) > 4):
    print("Usage: python compareScreens.py <filename1> <filename2>\n")
    sys.exit()

screenName1 = sys.argv[1]
screenName2 = sys.argv[2]
commonFields=[]

# Uncommenting the pdb line opens the debugger in the command line
# pdb.set_trace()

# True Main functionality is below def's.

def readScreen(screenName):

    inFieldText = False
    inScreenText = False
    curField = []
    curFieldName = ""
    fieldSet = {}
    jplText = []
    numLinesScreenFile = 0
    
    with open(screenName, "r") as screenFile:

        while True:
            line = screenFile.readline()

            numLinesScreenFile += 1

            if (line == ""):
                break

            # Read in the screen.
            # Parse out and store the JPLTEXT
            # Parse out and store the fields.

            screenMatch = re.match(r"\s*[S]:(\S+)", line)
            jplMatch = re.match(r"\s*JPLTEXT=(.*)", line)
            fieldMatch = re.match(r"\s*[GLFBYT]:(\S*)\s*$", line)

            # If this is an excluded field line, then just skip this line
            if (stripExtraneousFieldLines(line) is None):
                continue
            
            if (screenMatch):
                curField.append(line)
                inScreenText = True

            elif (jplMatch):
                if (inScreenText):
                    inScreenText = False 
                    fieldSet["__internalScreen__"] = curField.copy()
                    curField.clear()
                
                jplLine = jplMatch.group(1)

                # Check to see if this line has a line continuation character on it.
                # If so, bring in the next line also.
                jplLineExtendsMatch = re.match(r"(.*)\\$", jplMatch.group(1))
                if (jplLineExtendsMatch):
                    jplLine = jplLineExtendsMatch.group(1)
                    nextLineMatch = re.match(r"(.*)\s+", screenFile.readline())
                    
                    # Sometimes the next line has JPLTEXT= on it, sometimes it doesn't.
                    # Remove it if it does.
                    removeJpltextMatch = re.match(r"^\s*JPLTEXT=(.*)", nextLineMatch.group(1))
                    if (removeJpltextMatch):
                        nextLine=removeJpltextMatch.group(1)
                    else:
                        nextLine=nextLineMatch.group(1)
                    jplLine = jplLine + nextLine

                jplText.append(jplLine)

            elif (fieldMatch) :
                # Save the previous field, if any.  
                if (curFieldName != ""):
                    fieldSet[curFieldName] = curField.copy()
                    curFieldName = ""
                    curField.clear()
                if (len(fieldMatch.group(1)) > 0):
                    inFieldText = True
                    curFieldName = fieldMatch.group(1)
                else:
                    # this field name is blank, so ignore this field completely
                    inFieldText = False

            # Only if we are currently within a field or the screen match add this line to whatever we're building
            if (inFieldText or inScreenText):
                curField.append(line)
                
    return jplText, fieldSet

def printRelevantDiffLines(content1, content2):
    diffObject = difflib.Differ()
    differences = list(diffObject.compare(content1, content2))
    trueDiffs = []
    
    unique = True
    
    for diffLine in differences:

        jplMatch = re.match(r"^[\?\-\+] .*", diffLine)
        if (jplMatch):
            print (diffLine)
            unique = False
            trueDiffs.append(diffLine)
    
    if (unique):
        return None

    return trueDiffs


def stripExtraneousFieldLines(fieldLine):

    # Changes in any of the following field characteristics have no functional purpose,
    #   so exclude these field lines

    # Exclude '#  NUMBER=
    if (re.match(r"#  NUMBER=[\d]+", fieldLine)):
        return None

    # Exclude 'LINE=[\d]+ COLUMN=[\d]+

    if (re.match(r"\s+LINE=[\d]+ COLUMN=[\d]+", fieldLine)):
        return None
    
    ## Exclude all PI lines like the following:
    # PI(voff)=18.50
    # PI(hoff)=23.00
    # PI(save-hoff)=138
    # PI(save-voff)=259
    # PI(save-width)=18
    # PI(save-height)=14
    # PI(halign)=0
    # PI(valign)=.5
    # PI(font)=Times New Roman-10-bold

    ## Note that the PI(save-length) paramaeter has meaning
    # (shows actual display length in html, rather than character limit as in LENGTH=
    # so it is no excluded

    if (re.match(r"\s+PI\((voff|hoff|save-hoff|save-voff|save-width|save-height|halign|valign|font)\)=.*", fieldLine)):
        return None

    return fieldLine
    
        
def compareJpl(jplText1, jplText2):

    # Go through JPL first:
    print("Jpl Comparison:")
    print("---------------\n")

    if (printRelevantDiffLines(jplText1, jplText2) is None):
        print ("JPL is identical\n")
        
    return


def compareFields(fieldSet1, fieldSet2):

    # Now, go through all the fields.
    # First check if the fieldSet maps are the same.

    print("---------------\n")
    print("Named Field Comparisons:\n")

    # Check the field Lists are the same
    keys1 = fieldSet1.keys()
    keys2 = fieldSet2.keys()

    if (keys1 == keys2):
        print("No New fields added or deleted\n")
        commonKeys = keys1
        
    else:
        commonKeys = list(set(keys1).intersection(keys2))
        keys1Only = list(set(keys1) - set(keys2))
        keys2Only = list(set(keys2) - set(keys1))

        print("Fields Only in Screen 1: " + ", ".join(keys1Only))
        print("Fields Only in Screen 2: " + ", ".join(keys2Only))
        print("")
    commonFields = commonKeys
    print ("-----\n")

    # Now, print differences in common fields

    print("Differences in Common Fields:\n")
    from prettytable import PrettyTable 

    # Specify the Column Names while initializing the Table 
    myTable = PrettyTable(["Common Fields", screenName1, screenName2]) 

    # Add rows 
    myTable.add_row(["Leanord", "X", "B", "91.2 %"]) 

    unique = True
    
    for fieldName in iter(sorted(commonKeys)):
        
        if (fieldSet1[fieldName] == fieldSet2[fieldName]):
            continue

#        print("---")

        unique = False
        
        print ("Field different for: " + fieldName + "\n")

        truediffs = printRelevantDiffLines(fieldSet1[fieldName], fieldSet2[fieldName])
        # truediffs will have entries - is screen1 + screen 2
        dlen = len(truediffs)
        scrn1diff = []
        scrn2diff = []
        for x in truediffs:
          isscrn1 = re.match(r"^[\?\-] .*", x)
        if (isscrn1):
            scrn1diff.append(x)
        else:    
            scrn2diff.append(x)

        myTable.add_row([fieldName, scrn1diff, scrn2diff]) 
        
    if (unique):
        print("No Differences in Common Fields\n")

    print(myTable)    
    return

def printRawScreenFile(jplText, fieldSet):

    screenRawFile = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
    screenRawFile.write('\n'.join(fieldSet["__internalScreen__"]))
    screenRawFile.write('\n')
    screenRawFile.write('\n'.join(jplText))
    screenRawFile.write('\n')
    for fieldName in iter(sorted(fieldSet.keys())):
        screenRawFile.write(''.join(fieldSet[fieldName]))
        screenRawFile.write('\n')
        
    return screenRawFile.name



# PROGRAM START (after def's and variables above)

jplText1, fieldSet1 = readScreen(screenName1)
jplText2, fieldSet2 = readScreen(screenName2)

# Print Out Statistics:

print("Screen1: " + screenName1 + "\nScreen2: " + screenName2)
print("  JplText lines -- Screen1: " + str(len(jplText1)) + ", Screen2: " + str(len(jplText2)))
print("  Named Fields #'s -- Screen1: : " + str(len(fieldSet1) - 1) + ", Screen2: " + str(len(fieldSet2) - 1))

print("")
print("Comparison Legend:  '- ' is a line only in " + screenName1)
print("                    '+ ' is a line only in " + screenName2)
print("                    '? ' highlights differences")
print("")

# printing out the jpl files as temporary ones.
print("")
jplFile1 = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
jplFile1.write('\n'.join(jplText1))
print("JPL TempFile1: " + jplFile1.name)
jplFile2 = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
jplFile2.write('\n'.join(jplText2))
print("JPL TempFile2: " + jplFile2.name)
print("")

compareJpl(jplText1, jplText2)

compareFields(fieldSet1, fieldSet2)

print("-------------\n")

# RawFiles -- for debugging or maybe examination.

print("RawFile1: " + printRawScreenFile(jplText1, fieldSet1))
print("RawFile2: " + printRawScreenFile(jplText2, fieldSet2))

# Create a DataFrame


# Display the DataFrame
