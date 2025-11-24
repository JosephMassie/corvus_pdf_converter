#!./.venv/bin/python3

import os
import re
import argparse
import json
from rich import print
from pypdf import PdfReader

print("[bold green]CB Mission PDF Converter")

parser = argparse.ArgumentParser(
    prog="CB Mission PDF Converter",
    description="Convert mission PDFs for Infinity into JSON data."
)

parser.add_argument("file", help="Path of the target PDF file to convert")
parser.add_argument("-d", "--dest", default="./", dest="destination", help="Destination path for the resulting JSON. Defaults to current dir.")
parser.add_argument("-n", "--name", default="missions.json", dest="jsonName", help="Name of the resulting JSON file")
parser.add_argument("-p", "--parsed-output", action="store_true", dest="outputParsed", help="If present output raw parsed pages of PDF as text for debugging, will created a directory at destination containing all files")
parser.add_argument("-l", "--log", default=0, type=int, dest="log_level", help="""The level of logging to display
    0:'basic output'
    1:'simple debugging information'
    2:'complex debugging information'
""")

logLevel = 0
LOG_LEVELS = {
    "BASIC": 0,
    "SIMPLE": 1,
    "COMPLEX": 2
}

def log(msg, level = LOG_LEVELS["BASIC"]):
    if logLevel >= level:
        print(msg)


def readArgs():
    args = parser.parse_args()

    global logLevel
    logLevel = args.log_level

    log(f"\nexecuted with the folowing args {args}\n", LOG_LEVELS["COMPLEX"])

    return args.file, args.destination, args.jsonName, args.outputParsed

# functional "infinity" to replace float('inf') for type consistency
INFINITY = 10_000
END_MISSION = "~END-MISSION~"

PARSED_OUTPUT_DIR = "parsed_pages"

def toTitle(string: str):
    words = string.lower().split(' ')
    
    words = list(map(lambda word: word[0].upper() + word[1:], words))

    return ' '.join(words)

def toKey(string: str):
    return string.lower().strip().replace(" ", "_")

def linesToContent(lines: list[str]):
    return ' '.join(lines).strip()

def parseMissionPages(missionName: str, pages: list[str], basePageNum = 0):
    SPECIAL_RULES_KEY = "scenario_special_rules"
    SKILL_SUBHEADERS = [
        "short skill",
        "long skill",
        "requirements",
        "effects"
    ]

    missionInfo = {
        "name": toTitle(missionName),
        # special rules are handled differently, all missions have them and its sections should be grouped
        SPECIAL_RULES_KEY: {}
    }

    isAfterSpecialRules = False
    for i in range(len(pages)):
        lines = pages[i].splitlines()
        # cut off the first two lines as these are page number and mission nam
        lastHeaderIndex = INFINITY
        subHeadIndexes = []
        lineCount = len(lines)
        log(f"\tPage {basePageNum + i} \\w LC:{lineCount}", LOG_LEVELS["SIMPLE"])

        # process each line looking for headers/subheaders as the starts/ends of blocks
        for lineNum in range(lineCount):
            line = lines[lineNum]
            normalizedLine = line.lower().strip()
            # check if the current line is a header/subheader
            if line.isupper():
                if normalizedLine not in SKILL_SUBHEADERS:
                    # if in an active block we've reached the start of another block, store the previous blocks
                    # contents
                    if lineNum > lastHeaderIndex or lineNum == lineCount - 1:
                        block = ''

                        # check if the current block has any active sub headers
                        subheadCount = len(subHeadIndexes)
                        if subheadCount > 0:
                            # with sub headers block will be a dict of sub blocks
                            block = {}

                            for i in range(subheadCount):
                                shi = subHeadIndexes[i]
                                content = ''

                                if i == subheadCount - 1:
                                    content = linesToContent(lines[shi+1:lineNum-1])
                                else:
                                    content = linesToContent(lines[shi+1:subHeadIndexes[i+1]-1])

                                block[toKey(lines[shi])] = content
                        else:
                            # with no sub headers block is simple text
                            block = linesToContent(lines[lastHeaderIndex+1:lineNum-1])

                        blockKey = toKey(lines[lastHeaderIndex])

                        if block != "" or len(block) != 0:
                            log(f"\t\t\tadding block {isAfterSpecialRules}", LOG_LEVELS["COMPLEX"])
                            if isAfterSpecialRules:
                                missionInfo[SPECIAL_RULES_KEY][blockKey] = block
                            else:
                                missionInfo[blockKey] = block
                        else:
                            # TODO: Some empty blocks are relevant info stored in a lone header, handle these
                            if blockKey == SPECIAL_RULES_KEY:
                                log(f"starting to parse special rules", LOG_LEVELS["COMPLEX"])
                                isAfterSpecialRules = True
                            # block is empty check if it should be dropped or parsed for information
                            log(f"\t\t\t!empty block <{blockKey}>!", LOG_LEVELS["COMPLEX"])

                        log(f"\t\t\tBlock<{blockKey}> {len(block)}")
                    # set block header index for the next iteration
                    log(f"\t\tFound section '{line}' @ lines[{lastHeaderIndex}:{lineNum}]", LOG_LEVELS["COMPLEX"])
                    lastHeaderIndex = lineNum
                else:
                    if lastHeaderIndex == INFINITY:
                        log(f"ERROR: invalid subheader, no associated main header")
                    subHeadIndexes.append(lineNum)

    return missionInfo

def main():
    file, destination, jsonName, outputParsed = readArgs()
    pdf = PdfReader(file)

    if outputParsed:
        try:
            os.mkdir(destination + PARSED_OUTPUT_DIR)
        except FileExistsError:
            log(f"output dir for raw txts already exists", LOG_LEVELS["COMPLEX"])

    log(f"Number of pages: {len(pdf.pages)} with a dest of {destination}", LOG_LEVELS["SIMPLE"])

    indexPage = pdf.pages[1].extract_text().splitlines()

    rawItsScenarios = []
    scenarioStartIndex = INFINITY

    rawDirectActions = []
    directActionStartIndex = INFINITY

    log(f"Searching PDF for missions")
    for i in range(len(indexPage)):
        scenarioPage = "its scenarios".upper()
        directActionPage = "its direct action".upper()
        resilienceOps = "resilience operations".upper()

        # detect the start/end of different sections of the PDF that we care about from the index page
        if scenarioPage in indexPage[i]:
            # found the start of its scenarios set start index
            scenarioStartIndex = i
            pageNum = int(indexPage[i].replace(scenarioPage, "").strip())
            log(f"\nFound ITS Scenarios @ {i} -> '{pageNum}' -> {scenarioStartIndex}", LOG_LEVELS["BASIC"])
        elif directActionPage in indexPage[i]:
            # reset scenario index since we've started recording direct action missions
            scenarioStartIndex = INFINITY
            directActionStartIndex = i
            pageNum = int(indexPage[i].replace(directActionPage, "").strip())
            log(f"Found ITS Direct Actions @ {i} -> '{pageNum}' -> {directActionStartIndex}", LOG_LEVELS["BASIC"])
            # also push a special "~END-MISSION~" to itsScenarios
            rawItsScenarios.append({ "name": END_MISSION, "page": pageNum })
        elif resilienceOps in indexPage[i]:
            # end search as we've reached the end of missions
            scenarioStartIndex = INFINITY
            directActionStartIndex = INFINITY
            pageNum = int(indexPage[i].replace(resilienceOps, "").strip())
            # also push a special "~END-MISSION~" to directActions
            rawDirectActions.append({ "name": END_MISSION, "page": pageNum })

        # with an active start index for a given section save each line until it is no longer active
        if i > scenarioStartIndex or i > directActionStartIndex:
            res = re.match("^(.+\\s+)(\\d+)$", indexPage[i]) # type: ignore
            if res:
                name, page = res.groups()
                if scenarioStartIndex < directActionStartIndex:
                    rawItsScenarios.append({ "name": name.strip(), "page": int(page.strip()) })
                else:
                    rawDirectActions.append({ "name": name.strip(), "page": int(page.strip())})

    log(f"\nFound {len(rawItsScenarios)} scenarios in PDF", LOG_LEVELS["SIMPLE"])
    for scenario in rawItsScenarios:
        log(f"\t'{scenario["name"]}' @ {scenario["page"]}", LOG_LEVELS["SIMPLE"])

    log(f"\nFound {len(rawDirectActions)} direct actions in PDF", LOG_LEVELS["SIMPLE"])
    for action in rawDirectActions:
        log(f"\t'{action["name"]}' @ {action["page"]}", LOG_LEVELS["SIMPLE"])
    
    log(f"Parsing missions")
    itsScenarios = []
    for i, scenario in enumerate(rawItsScenarios):
        # skip the end mission identifier
        if (scenario["name"] == END_MISSION):
            continue
        log(f"\n\nScenario <{toKey(scenario["name"])}> @ {scenario["page"]}", LOG_LEVELS["SIMPLE"])
        pages = pdf.pages[scenario["page"]-1:rawItsScenarios[i+1]["page"]-1]
        pages = list(map(lambda pdfPage: pdfPage.extract_text(), pages))
        if outputParsed:
            parsedName = destination + PARSED_OUTPUT_DIR + "/" + toKey(scenario["name"])
            log(f"\tWriting {scenario["name"]} to {parsedName}", LOG_LEVELS["COMPLEX"])
            fp = open(parsedName + ".txt", 'w')
            fp.write('\n\n'.join(pages))
            fp.close()
        mission = parseMissionPages(
            missionName=scenario["name"],
            pages=pages,
            basePageNum=scenario["page"]
            )
        itsScenarios.append(mission)
    
    directActions = []
    for i, action in enumerate(rawDirectActions):
        # skip the end mission identifier
        if action["name"] == END_MISSION:
            continue
        log(f"\n\nDirect Action <{toKey(action["name"])}> @ {action["page"]}", LOG_LEVELS["SIMPLE"])
        pages = pdf.pages[action["page"]-1:rawDirectActions[i+1]["page"]-1]
        pages = list(map(lambda pdfPage: pdfPage.extract_text(), pages))
        if outputParsed:
            parsedName = destination + PARSED_OUTPUT_DIR + "/" + toKey(action["name"]) + ".txt"
            log(f"\tWriting {action["name"]} to {parsedName}", LOG_LEVELS["COMPLEX"])
            fp = open(parsedName, 'w')
            fp.write('\n\n'.join(pages))
            fp.close()
        mission = parseMissionPages(
            missionName=action["name"],
            pages=pages,
            basePageNum=action["page"]
        )
        directActions.append(mission)

    log(f"\n\n found {len(itsScenarios)} scenarios\n\t{',\n\t'.join(map(lambda s: s["name"], itsScenarios))}", LOG_LEVELS["SIMPLE"])
    log(f"\nfound {len(directActions)} direct actions\n\t{',\n\t'.join(map(lambda d: d["name"], directActions))}", LOG_LEVELS["SIMPLE"])

    jsonFile = open(destination + jsonName, 'w')
    jsContent = { "its_scenarios": itsScenarios, "direct_actions": directActions }
    json.dump(jsContent, jsonFile)
    jsonFile.close()

    # discover shared props
    # Build a list of (KEY, COUNT) where COUNT is how many scenarios include KEY (excluding 'name')
    if len(itsScenarios) > 0:
        key_counts: dict[str, int] = {}
        for s in itsScenarios:
            for k in s.keys():
                if k == 'name':
                    continue
                key_counts[k] = key_counts.get(k, 0) + 1

        # Convert to a list of tuples and sort by count descending then key
        key_count_list = list(filter(lambda t: t[1] > 1, sorted(key_counts.items(), key=lambda t: (-t[1], t[0]))))

        # Output the resulting list of tuples to the console
        log(f"Key counts across itsScenarios (excluding 'name'): ", LOG_LEVELS["SIMPLE"])
        for key, count in key_count_list:
            log(f"\t{count} - {key}", LOG_LEVELS["SIMPLE"])
    else:
        log("No itsScenarios to analyze for key counts.", LOG_LEVELS["SIMPLE"])



main()