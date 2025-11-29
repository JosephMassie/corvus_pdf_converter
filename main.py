#!./.venv/bin/python3

import click

import os
import json
from pypdf import PdfReader


from lib.logger import LOG_LEVELS, setLogLevel, log
from lib.string_utils import toKey
from lib.constants import END_MISSION, PARSED_OUTPUT_DIR
from mission_parser import getMissionPagesFromPdf, getBlocksFromPages, blocksToMissionInfo
from interactive_mapper import interactiveBlocksToMission

click.secho("CB Mission PDF Converter", fg="green")


@click.command(
    help="Convert target PDF file containing missions for the tabletop game Infinity into JSON data.",
    short_help="Convert mission PDFs for Infinity into JSON data."
)
@click.argument("file", type=str)
@click.option(
    "-d",
    "--dest",
    "destination",
    type=click.Path(),
    default="./",
    show_default=True,
    help="Destination path for the resulting JSON. Defaults to current dir."
)
@click.option(
    "-n",
    "--name",
    "jsonName",
    type=str,
    default="missions.json",
    show_default=True,
    help="Name of the resulting JSON file"
)
@click.option(
    "-p",
    "--parsed-output",
    "outputParsed",
    is_flag=True,
    help="""If present output raw parsed pages of PDF as text for debugging, 
    will created a directory at destination containing all files"""
)
@click.option(
    "-l",
    "--log",
    "log_level",
    type=click.IntRange(0, 2, clamp=True),
    default=0,
    show_default=True,
    help="""The level of logging to display
    0:'basic output'
    1:'simple debugging information'
    2:'complex debugging information'
"""
)
@click.option(
    "-i",
    "--interactive",
    is_flag=True,
    help="Manually control how each block of text parsed for missions is converted into JSON properties."
)
def main(log_level, file, destination, jsonName, outputParsed, interactive):
    setLogLevel(log_level)

    pdf = PdfReader(file)

    if outputParsed:
        try:
            os.mkdir(destination + PARSED_OUTPUT_DIR)
        except FileExistsError:
            log(f"output dir for raw txts already exists", LOG_LEVELS.COMPLEX)

    log(f"Number of pages: {len(pdf.pages)} with a dest of {destination}", LOG_LEVELS.SIMPLE)

    missionPageData = getMissionPagesFromPdf(pdf)
    
    log(f"Parsing missions")
    
    itsScenarios = []
    for i, scenario in enumerate(missionPageData["itsScenarioData"]):
        # skip the end mission identifier
        if (scenario["name"] == END_MISSION or i > 0):
            continue
        log(f"\n\nScenario <{toKey(scenario["name"])}> @ {scenario["page"]}", LOG_LEVELS.SIMPLE)
        pages_objs = pdf.pages[scenario["page"]-1:missionPageData["itsScenarioData"][i+1]["page"]-1]
        pages = list(map(lambda pdfPage: pdfPage.extract_text(), pages_objs))
        if outputParsed:
            parsedName = destination + PARSED_OUTPUT_DIR + "/" + toKey(scenario["name"])
            log(f"\tWriting {scenario["name"]} to {parsedName}", LOG_LEVELS.COMPLEX)
            fp = open(parsedName + ".txt", 'w')
            fp.write('\n\n'.join(pages))
            fp.close()
        blocks = getBlocksFromPages(pages, scenario["page"])
        mission = {}

        if interactive:
            try:
                mission = interactiveBlocksToMission(scenario["name"], blocks)
            except click.Abort:
                log("\n\n[orange_red1]quiting program")
                return
            except Exception as error:
                log("\n\n[red]unexpected error quiting")
                log(error, prettyPrint=True)
                return
        else:
            # when not interactive use the default mapping
            mission = blocksToMissionInfo(scenario["name"], blocks)
        
        log(f"mission:", LOG_LEVELS.COMPLEX)
        log(mission, LOG_LEVELS.COMPLEX, prettyPrint=True, max_string=20)

        itsScenarios.append(mission)

        

    # directActions = []
    # for i, action in enumerate(missionPageData["directActionsData"]):
    #     # skip the end mission identifier
    #     if action["name"] == END_MISSION:
    #         continue
    #     log(f"\n\nDirect Action <{toKey(action["name"])}> @ {action["page"]}", LOG_LEVELS.SIMPLE)
    #     pages_objs = pdf.pages[action["page"]-1:missionPageData["directActionsData"][i+1]["page"]-1]
    #     pages = list(map(lambda pdfPage: pdfPage.extract_text(), pages_objs))
    #     if outputParsed:
    #         parsedName = destination + PARSED_OUTPUT_DIR + "/" + toKey(action["name"]) + ".txt"
    #         log(f"\tWriting {action["name"]} to {parsedName}", LOG_LEVELS.COMPLEX)
    #         fp = open(parsedName, 'w')
    #         fp.write('\n\n'.join(pages))
    #         fp.close()
    #     blocks = getBlocksFromPages(pages, action["page"])
    #     mission = blocksToMissionInfo(action["name"], blocks)

    #     directActions.append(mission)

    if len(itsScenarios) > 0:
        log(f"\n\n found {len(itsScenarios)} its scenarios\n\t{',\n\t'.join(map(lambda s: s["name"], itsScenarios))}", LOG_LEVELS.SIMPLE)
    else:
        log("found no its scenarios")
    #log(f"\nfound {len(directActions)} direct actions\n\t{',\n\t'.join(map(lambda d: d["name"], directActions))}", LOG_LEVELS.SIMPLE)

    jsonFile = open(destination + jsonName, 'w')
    jsContent = { "its_scenarios": itsScenarios }#, "direct_actions": directActions }
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
        log(f"\nKey counts across itsScenarios (excluding 'name'): ", LOG_LEVELS.SIMPLE)
        for key, count in key_count_list:
            log(f"\t{count} - {key}", LOG_LEVELS.SIMPLE)
    else:
        log("\nNo itsScenarios to analyze for key counts.", LOG_LEVELS.SIMPLE)


if __name__ == "__main__":
    main()