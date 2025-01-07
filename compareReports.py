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


if (len(sys.argv) == 2) :
    defect_enh_id =sys.argv[1]
    screenName = ""
else:
    if (len(sys.argv) == 3) :
        defect_enh_id =sys.argv[1]
        screenName = sys.argv[2]
    else:
        print("Usage: python compareReports.py <Defect/Enhancment #> <reportname.jam>\n")
        print("if Reportname is blank it will compare ALL Reports in directory")
        sys.exit()

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
    rptText = []
    numLinesScreenFile = 0
    
    with open(screenName, "r") as screenFile:

        while True:
            line = screenFile.readline().lstrip(' ')

            numLinesScreenFile += 1

            if (line == "" ):
                break
            if (line == '\n'):
                continue

            # Read in the screen.
            # Parse out and store the JPLTEXT
            # Parse out and store the fields.

            screenMatch = re.match(r"\s*[R]:(\S+)", line)
            jplMatch = re.match(r"\s*JPLTEXT=(.*)", line)
            fieldMatch = re.match(r"\s*[GLFBYT]:(\S*)\s*$", line)
            rptMatch = re.match(r"\s*RW-SCRIPT =(.*)", line)

            # If this is an excluded field line, then just skip this line
            if (stripExtraneousFieldLines(line) is None):
                continue

            if (rptMatch):
                # Read until END-SCRIPT
                rptText.append(line.strip(' '))
                while True:
                    rptline = screenFile.readline().lstrip(' ')
                    numLinesScreenFile += 1
                    if (line == ""):
                        continue
                    rptText.append(rptline.strip(' '))
                    endrptMatch = re.match(r"\s*END-SCRIPT(.*)", rptline)
                    if (endrptMatch):
                        rptText.append(rptline.strip(' '))
                        break


            if (screenMatch):
 #               curField.append(line)
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
                
    return jplText, fieldSet, rptText

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
#   PI(gridh)=0.1458333284in
#   PI(gridw)=0.0625000000in
#   PI(height)=24.57
#   PI(save-gridh)=14
#   PI(save-gridw)=6
#   PI(view-height)=24.57
#   PI(view-width)=311.83
#   PI(width)=1400
#   EDITED-BY=3

    ## Note that the PI(save-length) paramaeter has meaning
    # (shows actual display length in html, rather than character limit as in LENGTH=
    # so it is no excluded

    if (re.match(r"\s*+PI\((voff|hoff|save-hoff|save-voff|save-width|save-height|halign|valign|font)\)=.*", fieldLine)):
        return None
    
    if (re.match(r"\s*+PI\((gridh|gridw|height|save-gridh|save-gridw|view-height|view-width|width|font)\)=.*", fieldLine)):
        return None

    if (re.match(r"\s*JPLTEXT=.*//.*", fieldLine)):
        return None

    return fieldLine
    
        
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

def compareRptPandas(rptText1, rptText2):

    # Go through JPL first:
    #print("Jpl Comparison:")
    #print("---------------\n")
    truediffs = printRelevantDiffLines(rptText1, rptText2)
    if (truediffs is None):
        #print ("JPL is identical\n")
        return(["REPORT Script", "Same", "Same"]) 
    else:
        rpt1diff = []
        rpt2diff = []
        for x in truediffs:
            isscrn1 = re.match(r"^[\-] .*", x)
            if (isscrn1):
                rpt1diff.append(x)
                rpt2diff.append("")
            else:    
                rpt2diff.append(x)
                rpt1diff.append("")
        rpt1diffout = "\n".join(rpt1diff)
        rpt2diffout = "\n".join(rpt2diff)
        return(["REPORT Script", rpt1diffout, rpt2diffout]) 

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

def get_files_with_extension(directory, extension):
    file_list = []
    for filename in os.listdir(directory):
        if filename.endswith(extension):
            file_list.append(filename)
    return file_list

def create_index_html(repo_path):
    # Specify the path to the repository
    repo_path = os.path.abspath(repo_path)
    
    # Initialize the HTML content
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>GitHub Pages Index</title>
    </head>
    <body>
        <h1>GitHub Pages in Repository</h1>
        <ul>
    """
    
    # Walk through the directory and add links to HTML files
    for root, dirs, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".html"):
                relative_path = os.path.relpath(os.path.join(root, file), repo_path)
                html_content += f'<li><a href="{relative_path}" target="_blank">{relative_path}</a></li>\n'
    
    # Close the HTML content
    html_content += """
        </ul>
    </body>
    </html>
    """
    
    # Write the HTML content to index.html
    with open(os.path.join(repo_path, "index.html"), "w") as f:
        f.write(html_content)
    print("index.html file has been created successfully!")

#---------------------------------------------------------------------------------------------------
# PROGRAM START (after def's and variables above)
config = configparser.ConfigParser()

# Add a section
config.read('config.ini')

outputBaseDirectory = config['CompareReport']['outputPath']
inputBaseDirectory=config['CompareReport']['inputBaseDirectory']
# Create the directory
if defect_enh_id.startswith("TEST"):
    outputDir = os.path.join(outputBaseDirectory,"Testing",defect_enh_id)
if defect_enh_id.startswith("ENH"):
    outputDir = os.path.join(outputBaseDirectory,"Enhancements",defect_enh_id)
if defect_enh_id.startswith("DEF"):
    outputDir = os.path.join(outputBaseDirectory,"Defects",defect_enh_id)
inputDir = inputBaseDirectory+"/"+defect_enh_id


try:
    os.makedirs(outputDir)
except OSError as e:
    if e.errno == 17:  # File exists
        print("Directory already exists:", outputDir)
    else:
        print(e)
        sys.exit


extension = ".jrw.asc" 
files = get_files_with_extension(inputDir, extension)
print(files)

if screenName != "":
    # just use filename
    files = [screenName + ".asc"]

    # do the loop
fcounter = 0
for fname in files:
    screenName1 = fname + ".bak"
    screenName2 = fname 

    pathName1 = inputDir +'/' + screenName1
    pathName2 = inputDir +'/' + screenName2
    # check if files exist if not ignore them.
    if not os.path.exists(pathName1) and os.path.exists(pathName2):
        continue
    fcounter+= 1
    jplText1, fieldSet1, rptText1 = readScreen(pathName1)
    jplText2, fieldSet2, rptText2 = readScreen(pathName2)
    jpldata = [[ str(len(jplText1)),str(len(jplText2))]]
    flddata = [[ str(len(fieldSet1)),str(len(fieldSet2))]]
    
    pjpldiffs = compareJplPandas(jplText1, jplText2)
    pflddiffs = compareFieldsPandas(fieldSet1, fieldSet2)
    prptdiffs = compareRptPandas(rptText1, rptText2)

    newflddata = pflddiffs[0]
    technologies = ({
        'Screen':["JPL Lines","Num Fields","JPL Text","REPORT Script"],
        screenName1 :[str(len(jplText1)),str(len(fieldSet1)),pjpldiffs[1],prptdiffs[1]],
        screenName2 :[str(len(jplText2)),str(len(fieldSet1)),pjpldiffs[2],prptdiffs[2]]
                })
    df = pd.DataFrame(technologies)

    # Array of new rows 
    new_rows = pflddiffs

    # Create a DataFrame from the new rows
    new_df = pd.DataFrame(new_rows, columns=df.columns)

    # Concatenate the two DataFrames
    df = pd.concat([df, new_df], ignore_index=True)

    html_table = df.to_html(index=True)
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
    with open(outputDir+'/'+ fname +'.html', 'w') as f:
        f.write(rendered_html)


#jplFile1 = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
#jplFile1.write('\n'.join(jplText1))
#print("JPL TempFile1: " + jplFile1.name)
#jplFile2 = tempfile.NamedTemporaryFile(mode='w+t', delete=False)
#jplFile2.write('\n'.join(jplText2))
#print("JPL TempFile2: " + jplFile2.name)
#print("")


print("Completed Reports Compare - Files processed="+str(fcounter)+"\n")
# RawFiles -- for debugging or maybe examination.

#print("RawFile1: " + printRawScreenFile(jplText1, fieldSet1))
#print("RawFile2: " + printRawScreenFile(jplText2, fieldSet2))

# Create a DataFrame for pandas
# Replace the opening <table> tag to add your custom id and remove any default 'dataframe' class



# Usage
create_index_html(outputDir)



