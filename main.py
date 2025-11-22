#!./.venv/bin/python3

import re
import argparse
from pypdf import PdfReader

print("CB Mission PDF Converter")

parser = argparse.ArgumentParser(
    prog="CB Mission PDF Converter",
    description="Convert mission PDFs for Infinity into JSON data."
)

parser.add_argument("file", help="Path of the target PDF file to convert")
parser.add_argument("-d", "--dest", default="./", dest="destination", help="Destination path for the resulting JSON. Defaults to current dir.")
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

    return args.file, args.destination

def main():
    file, destination = readArgs()
    pdf = PdfReader(file)

    log(f"Number of pages: {len(pdf.pages)} with a dest of {destination}", LOG_LEVELS["SIMPLE"])

    indexPage = pdf.pages[1].extract_text().splitlines()

    itsScenarios = []
    scenarioStartIndex = float('inf')

    directActions = []
    directActionStartIndex = float('inf')

    for i in range(len(indexPage)):
        scenarioPage = "its scenarios".upper()
        directActionPage = "its direct action".upper()
        resilienceOps = "resilience operations".upper()

        if scenarioPage in indexPage[i]:
            # found the start of its scenarios set start index
            scenarioStartIndex = i
            pageNum = int(indexPage[i].replace(scenarioPage, "").strip())
            log(f"\nFound ITS Scenarios @ {i} -> '{pageNum}' -> {scenarioStartIndex}", LOG_LEVELS["BASIC"])
        elif directActionPage in indexPage[i]:
            # reset scenario index since we've started recording direct action missions
            scenarioStartIndex = float('inf')
            directActionStartIndex = i
            pageNum = int(indexPage[i].replace(directActionPage, "").strip())
            log(f"Found ITS Direct Actions @ {i} -> '{pageNum}' -> {directActionStartIndex}", LOG_LEVELS["BASIC"])
        elif resilienceOps in indexPage[i]:
            # end search as we've reached the end of missions
            scenarioStartIndex = float('inf')
            directActionStartIndex = float('inf')

        if i > scenarioStartIndex or i > directActionStartIndex:
            res = re.match("^(.+\s+)(\d+)$", indexPage[i])
            if res:
                name, page = res.groups()
                if scenarioStartIndex < directActionStartIndex:
                    itsScenarios.append({ "name": name.strip(), "page": int(page.strip()) })
                else:
                    directActions.append({ "name": name.strip(), "page": int(page.strip())})

    log(f"\nFound {len(itsScenarios)} scenarios")
    for scenario in itsScenarios:
        log(f"'{scenario["name"]}' @ {scenario["page"]}")
    log(f"\nFound {len(directActions)} direct actions")
    for action in directActions:
        log(f"'{action["name"]}' @ {action["page"]}")

    test = itsScenarios[0]
    log(f"\n\n{test["name"]}\n{pdf.pages[test["page"]-1].extract_text()}")



main()