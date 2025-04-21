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

if (len(sys.argv) == 3) :
    currentFile = sys.argv[1]
    modifiedFile = sys.argv[2]
    print("compareScreens will scan the ascii files for changes ansd will create a summary")
    print("of changes that can be viewed in a browser.")
    print("The Differences Summary Files will be created in the directory this program was run.")
else:
    print("Usage: compareScreens <Pathname to current ascii file> <Pathname to modified ascii file>")
    print("compareScreens will scan the ascii files for changes ansd will create a summary")
    print("of changes that can be viewed in a browser.")
    print("The Differences Summary Files will be created in the directory this program was run.")
    print("If files are blank or not found it will exit.")
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

def readScreenJPL(screenName):

    jplText = []
    numLinesScreenFile = 0
    
    with open(screenName, "r") as screenFile:

        while True:
            line = screenFile.readline().lstrip(' ')

            numLinesScreenFile += 1

            if (line == ""):
                break

            # Read in the screen.
            # When we find PI we know the JPL has completed

            jplMatch = re.match(r"\s*JPLTEXT=(.*)", line)
            endMatch = re.match(r"\s*PI\s*", line)

            # If this is an excluded field line, then just skip this line
            if (stripExtraneousFieldLines(line) is None):
                continue

            if (jplMatch):
                inJPLText = True
                jplText.append(line.strip(' '))
                while True:
                    line = screenFile.readline().lstrip(' ')

                    endMatch = re.match(r"\s*PI\s*", line)
                    if (endMatch):
                        #thats it 
                        return jplText
                    result = re.sub(r"^\s*JPLTEXT=\s*", "", line)
                    jplText.append(result.strip(' '))
                
    return jplText

def printRelevantFieldDiffLines(content1, content2):
    
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

    if (re.match(r"\s*LINE=[\d]+\s*COLUMN=[\d]+.*", fieldLine)):
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

    if (re.match(r"\s*+PI\((voff|hoff|save-hoff|save-voff|save-width|save-height|halign|valign|font)\)=.*", fieldLine)):
        return None

    return fieldLine
    
        
def compareJplPandas(jplText1, jplText2):

    # Go through JPL first:
    #print("Jpl Comparison:")
    #print("---------------\n")
    truediffs = printRelevantDiffLines(jplText1, jplText2)
    if (truediffs is None):
        #print ("JPL is identical\n")
        return False
    else:
        return True
#        scrn1diff = []
#        scrn2diff = []
#        for x in truediffs:
#            isscrn1 = re.match(r"^[\-] .*", x)
#            if (isscrn1):
#                scrn1diff.append(x)
#                scrn2diff.append("")
#            else:    
#                scrn2diff.append(x)
#                scrn1diff.append("")
#        scrn1diffout = "\n".join(scrn1diff)
#        scrn2diffout = "\n".join(scrn2diff)
#        return(["JPL Text", scrn1diffout, scrn2diffout]) 

 

def compare_jpl_files(jplText1, jplText2, fname):
    with open('text1.txt', 'w+') as file1:
        file1.writelines([i for i in jplText1])
    with open('text2.txt', 'w+') as file2:
        file2.writelines([i for i in jplText2])
        
    with open('text1.txt') as file1, open('text2.txt') as file2:
        differ = difflib.HtmlDiff(wrapcolumn=100)
        html = differ.make_file(file1.readlines(), file2.readlines())

    with open(fname, 'w') as f:
        f.write(html)

    os.remove("text1.txt")
    os.remove("text2.txt")

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
        
#        for fieldNameS1 in iter(sorted(keys1Only)):
#            resultArr.append(["Unique Field", "".join(fieldNameS1), ""]) 

#        for fieldNameS2 in iter(sorted(keys2Only)):
#            resultArr.append(["Unique Field", "", "".join(fieldNameS2)]) 
            
        resultArr.append(["Unique Fields ", "\n".join(keys1Only),"\n".join(keys2Only)]) 
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
        truediffs = printRelevantFieldDiffLines(fieldSet1[fieldName], fieldSet2[fieldName])
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
        resultArr.append(["Common Fields Diffs", "None", "None"]) 

    return resultArr


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
            if file.endswith("compared.html"):
                relative_path = os.path.relpath(os.path.join(root, file), repo_path)
                html_content += f'<li><a href="{relative_path}" target="_blank">{relative_path}</a></li>\n'
    
    # Close the HTML content
    html_content += """
        </ul>
    </body>
    </html>
    """
    
    # Write the HTML content to index.html
    with open(os.path.join(repo_path, "compared.index.html"), "w") as f:
        f.write(html_content)
    print("compared.index.html file has been created successfully!")

def split_file_name(file_path):
    """
    Splits a file path into directory, name, and extension(s).

    Args:
        file_path: The full path to the file.

    Returns:
        A tuple containing:
          - directory: The directory path.
          - name: The name of the file without extension(s).
          - extensions: The extension(s) of the file.
    """
    directory, file_name = os.path.split(file_path)
    name, *extensions_list = file_name.split(".")
    extensions = "." + ".".join(extensions_list) if extensions_list else ""
    return directory, name, extensions

# ---------------------------------------------------------------------------------------
# PROGRAM START (after def's and variables above)

if os.path.exists(currentFile):
    print(f"Processing Current Ascii File {currentFile} .")
else:
    print(f"Current Ascii File {currentFile} does not exist.")
    sys.exit()

if os.path.exists(modifiedFile):
    print(f"Processing Modified Ascii File {modifiedFile} .")
else:
    print(f"Modified Ascii File {modifiedFile} does not exist.")
    sys.exit()

if getattr(sys, 'frozen', False):
    # If the script is run as a bundled executable (e.g., with PyInstaller)
    executable_path = sys.executable
else:
    # If the script is run as a standard Python script
    executable_path = os.path.abspath(sys.argv[0])

app_path = os.path.dirname(executable_path)
#print(executable_path)


# Split the path
dirname1, screenName1, ext1 = split_file_name(currentFile)
dirname2, screenName2, ext2 = split_file_name(modifiedFile)

if (screenName1 != screenName2) :
    print(f"Screen names are different {screenName1} -- {screenName2}.")
    sys.exit()

jplText1, fieldSet1 = readScreen(currentFile)
jplText2, fieldSet2 = readScreen(modifiedFile)

jpldata = [[ str(len(jplText1)),str(len(jplText2))]]
flddata = [[ str(len(fieldSet1)),str(len(fieldSet2))]]
jplRawText1 = readScreenJPL(currentFile)
jplRawText2 = readScreenJPL(modifiedFile)

pjpldiffs = compareJplPandas(jplText1, jplText2)
if (pjpldiffs):
    jpldiff=screenName1 +'.jpl.diff.html'
    link = "<a href=\"" + jpldiff +"\" target=\"_blank\">"+jpldiff+"</a>"
    foutpath = os.path.join(jpldiff)
    compare_jpl_files(jplRawText1, jplRawText2,foutpath)
else:
    jpldiff=""

pflddiffs = compareFieldsPandas(fieldSet1, fieldSet2)

newflddata = pflddiffs[0]
technologies = ({
    'Screen':["JPL Lines","Num Fields"],
    screenName1+"_1":[str(len(jplText1)),str(len(fieldSet1))],
    screenName2+"_2":[str(len(jplText2)),str(len(fieldSet2))]
    })
df_technologies = pd.DataFrame(technologies)
# Now you can transpose the technologies DataFrame (make 'Screen' column the index)
#df_technologies.set_index('Screen', inplace=True)
#print(df_technologies)
    # Array of new rows 
new_rows = pflddiffs

    # Create a DataFrame from the new rows
new_df = pd.DataFrame(new_rows, columns=df_technologies.columns)
#new_df = pd.DataFrame(new_rows)
#new_df.set_index('Key', inplace=True)
#print(new_df)
# Concatenate the two DataFrames along the columns (index alignment)
final_df = pd.concat([df_technologies, new_df], axis=0)
#print(final_df)
# Replace '\n' with '<br>' in the entire DataFrame
formatted_df = final_df.replace({'\n': '<br>'}, regex=True)

html_table = formatted_df.to_html(index=False,escape=False)
html_table = html_table.replace('<table ', '<table id="example" ')
html_table = html_table.replace('dataframe', 'table table-striped ')
html_table = html_table.replace('">', '" style="width:100%">')

#print (html_table)
# Load the template environment
executable_path
env = Environment(loader=FileSystemLoader(app_path))
template = env.get_template('compare.html')

# Read the content from the file
#with open('file.txt', 'r') as f:
#    file_content = f.read()

# Render the template with the file content
rendered_html = template.render(content=html_table,jpllink=jpldiff)

# Save the rendered HTML to a file
foutpath = os.path.join(screenName1 + '.diff.html')

with open(foutpath, 'w') as f:
    f.write(rendered_html)

print("Completed Screen Compare - "+screenName1)

# Usage
#create_index_html(dirname1)



