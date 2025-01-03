import re
import copy
import sys
import tempfile
import pdb
import difflib
import pandas as pd
from prettytable import PrettyTable 
from jinja2 import Environment, FileSystemLoader

if (len(sys.argv) < 3) or (len(sys.argv) > 4):
    print("Usage: python compareScreens.py <filename1> <filename2>\n")
    sys.exit()

screenName1 = sys.argv[1]
screenName2 = sys.argv[2]

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
            line = screenFile.readline().lstrip(' ')

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

                jplText.append(jplLine.strip(' '))

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

        jplMatch = re.match(r"^[\-\+] .*", diffLine)
        if (jplMatch):
            #print (diffLine)
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
    #print("Jpl Comparison:")
    #print("---------------\n")
    truediffs = printRelevantDiffLines(jplText1, jplText2)
    if (truediffs is None):
        #print ("JPL is identical\n")
        myTable.add_row(["JPL", "Same", "Same"]) 
    else:
        scrn1diff = []
        scrn2diff = []
        for x in truediffs:
            isscrn1 = re.match(r"^[\-] .*", x)
            if (isscrn1):
                scrn1diff.append(x)
                scrn2diff.append("")
            else:    
                scrn2diff.append(x)
                scrn1diff.append("")
        scrn1diffout = "\n".join(scrn1diff)
        scrn2diffout = "\n".join(scrn2diff)
        myTable.add_row(["JPL Text", scrn1diffout, scrn2diffout]) 

    return

def compareJplPandas(jplText1, jplText2):

    # Go through JPL first:
    #print("Jpl Comparison:")
    #print("---------------\n")
    truediffs = printRelevantDiffLines(jplText1, jplText2)
    if (truediffs is None):
        #print ("JPL is identical\n")
        return(["JPL", "Same", "Same"]) 
    else:
        scrn1diff = []
        scrn2diff = []
        for x in truediffs:
            isscrn1 = re.match(r"^[\-] .*", x)
            if (isscrn1):
                scrn1diff.append(x)
                scrn2diff.append("")
            else:    
                scrn2diff.append(x)
                scrn1diff.append("")
        scrn1diffout = "\n".join(scrn1diff)
        scrn2diffout = "\n".join(scrn2diff)
        return(["JPL Text", scrn1diffout, scrn2diffout]) 

    return


def compareFields(fieldSet1, fieldSet2):
    # Now, go through all the fields.
    # First check if the fieldSet maps are the same.
 #   print("---------------\n")
 #   print("Named Field Comparisons:\n")
    # Specify the Column Names while initializing the Table 
    # Check the field Lists are the same
    keys1 = fieldSet1.keys()
    keys2 = fieldSet2.keys()

    if (keys1 == keys2):
#        print("No New fields added or deleted\n")
        myTable.add_row(["New Fields", "None", "None"]) 
        commonKeys = keys1
    else:
        commonKeys = list(set(keys1).intersection(keys2))
        keys1Only = list(set(keys1) - set(keys2))
        keys2Only = list(set(keys2) - set(keys1))
        
        for fieldNameS1 in iter(sorted(keys1Only)):
            myTable.add_row(["Unique Field", "".join(fieldNameS1), ""]) 

        for fieldNameS2 in iter(sorted(keys2Only)):
            myTable.add_row(["Unique Field", "", "".join(fieldNameS2)]) 
#        print("Fields Only in Screen 1: " + ", ".join(keys1Only))
#        print("Fields Only in Screen 2: " + ", ".join(keys2Only))
#        print("")
 #   print ("-----\n")
    # Now, print differences in common fields
  #  print("Differences in Common Fields:\n")
    # Add rows 
    unique = True
    for fieldName in iter(sorted(commonKeys)):
        if (fieldSet1[fieldName] == fieldSet2[fieldName]):
            continue
#        print("---")
        unique = False
#        print ("Field different for: " + fieldName + "\n")
        truediffs = printRelevantDiffLines(fieldSet1[fieldName], fieldSet2[fieldName])
        # truediffs will have entries - is screen1 + screen 2
        dlen = len(truediffs)
        scrn1diff = []
        scrn2diff = []
        for x in truediffs:
            isscrn1 = re.match(r"^[\-] .*", x)
            if (isscrn1):
                scrn1diff.append(x)
                scrn2diff.append("")
            else:    
                scrn2diff.append(x)
                scrn1diff.append("")
        scrn1diffout = "".join(scrn1diff)
        scrn2diffout = "".join(scrn2diff)
        myTable.add_row([fieldName, scrn1diffout, scrn2diffout]) 
        
    if (unique):
        #print("No Differences in Common Fields\n")
        myTable.add_row(["Common Fields", "None", "None"]) 

    return

def compareFieldsPandas(fieldSet1, fieldSet2):
    # Now, go through all the fields.
    # First check if the fieldSet maps are the same.
 #   print("---------------\n")
 #   print("Named Field Comparisons:\n")
    # Specify the Column Names while initializing the Table 
    # Check the field Lists are the same
    keys1 = fieldSet1.keys()
    keys2 = fieldSet2.keys()
    resultArr = []
    if (keys1 == keys2):
#        print("No New fields added or deleted\n")
        resultArr.append(["New Fields", "None", "None"]) 
        commonKeys = keys1
    else:
        commonKeys = list(set(keys1).intersection(keys2))
        keys1Only = list(set(keys1) - set(keys2))
        keys2Only = list(set(keys2) - set(keys1))
        
        for fieldNameS1 in iter(sorted(keys1Only)):
            resultArr.append(["Unique Field", "".join(fieldNameS1), ""]) 

        for fieldNameS2 in iter(sorted(keys2Only)):
            resultArr.append(["Unique Field", "", "".join(fieldNameS2)]) 
#        print("Fields Only in Screen 1: " + ", ".join(keys1Only))
#        print("Fields Only in Screen 2: " + ", ".join(keys2Only))
#        print("")
 #   print ("-----\n")
    # Now, print differences in common fields
  #  print("Differences in Common Fields:\n")
    # Add rows 
    unique = True
    for fieldName in iter(sorted(commonKeys)):
        if (fieldSet1[fieldName] == fieldSet2[fieldName]):
            continue
#        print("---")
        unique = False
#        print ("Field different for: " + fieldName + "\n")
        truediffs = printRelevantDiffLines(fieldSet1[fieldName], fieldSet2[fieldName])
        # truediffs will have entries - is screen1 + screen 2
        dlen = len(truediffs)
        scrn1diff = []
        scrn2diff = []
        for x in truediffs:
            isscrn1 = re.match(r"^[\-] .*", x)
            if (isscrn1):
                scrn1diff.append(x)
                scrn2diff.append("")
            else:    
                scrn2diff.append(x)
                scrn1diff.append("")
        scrn1diffout = "".join(scrn1diff)
        scrn2diffout = "".join(scrn2diff)
        resultArr.append([fieldName, scrn1diffout, scrn2diffout]) 
        
    if (unique):
        #print("No Differences in Common Fields\n")
        resultArr.append(["Common Fields", "None", "None"]) 

    return resultArr

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
myTable = PrettyTable(["Screens", screenName1, screenName2]) 
myTable.hrules = True

#print("Screen1: " + screenName1 + "\nScreen2: " + screenName2)
#print("  JplText lines -- Screen1: " + str(len(jplText1)) + ", Screen2: " + str(len(jplText2)))
myTable.add_row(["JPL Text Lines", str(len(jplText1)), str(len(jplText2))])

print("  Named Fields #'s -- Screen1: : " + str(len(fieldSet1) - 1) + ", Screen2: " + str(len(fieldSet2) - 1))
myTable.add_row(["Named Fields", str(len(fieldSet1)), str(len(fieldSet2))])

#print("")
#print("Comparison Legend:  '- ' is a line only in " + screenName1)
#print("                    '+ ' is a line only in " + screenName2)
#print("                    '? ' highlights differences")
#print("")

# printing out the jpl files as temporary ones.
#print("")
jplFile1 = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
jplFile1.write('\n'.join(jplText1))
print("JPL TempFile1: " + jplFile1.name)
jplFile2 = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
jplFile2.write('\n'.join(jplText2))
print("JPL TempFile2: " + jplFile2.name)
#print("")

compareJpl(jplText1, jplText2)

compareFields(fieldSet1, fieldSet2)

pjpldiffs = compareJplPandas(jplText1, jplText2)
pflddiffs = compareFieldsPandas(fieldSet1, fieldSet2)

#print("-------------\n")
print(myTable)    
# RawFiles -- for debugging or maybe examination.

print("RawFile1: " + printRawScreenFile(jplText1, fieldSet1))
print("RawFile2: " + printRawScreenFile(jplText2, fieldSet2))

# Create a DataFrame for pandas
jpldata = [[ str(len(jplText1)),str(len(jplText2))]]
flddata = [[ str(len(fieldSet1)),str(len(fieldSet2))]]
newflddata = pflddiffs[0]
technologies = ({
    'Screen':["JPL Lines","Num Fields","JPL Text"],
    screenName1 :[str(len(jplText1)),str(len(fieldSet1)),pjpldiffs[1]],
    screenName2 :[str(len(jplText2)),str(len(fieldSet1)),pjpldiffs[2]]
               })
df = pd.DataFrame(technologies)

# Array of new rows 
new_rows = pflddiffs

# Create a DataFrame from the new rows
new_df = pd.DataFrame(new_rows, columns=df.columns)

# Concatenate the two DataFrames
df = pd.concat([df, new_df], ignore_index=True)

print(df)

# Style the table for datatables   <table id="example" class="table table-striped" style="width:100%">
styler = df.style
styler.set_table_attributes('id="example" class="table table-striped" style="width:100%"')

#styler.set_td_classes(pd.DataFrame([['class1', 'class2']], columns=['A', 'B']))


result = styler.to_html()

html_table = df.to_html(index=True)

# Replace the opening <table> tag to add your custom id and remove any default 'dataframe' class
html_table = html_table.replace('<table ', '<table id="example" ')
html_table = html_table.replace('dataframe', 'table table-striped ')
html_table = html_table.replace('">', '" style="width:100%">')

print (html_table)

# Load the template environment
env = Environment(loader=FileSystemLoader('./'))
template = env.get_template('index.html')

# Read the content from the file
#with open('file.txt', 'r') as f:
#    file_content = f.read()

# Render the template with the file content
rendered_html = template.render(content=html_table)

# Save the rendered HTML to a file
with open('output.html', 'w') as f:
    f.write(rendered_html)



