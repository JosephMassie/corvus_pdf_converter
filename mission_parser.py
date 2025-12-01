import re
import json
from typing import TypedDict
from lib.constants import INFINITY, END_MISSION
from lib.string_utils import toKey, toTitle, linesToContent
from lib.logger import LOG_LEVELS, log

class TextBlock(TypedDict):
    key: str
    content: str | dict[str, str]
    page_index: int

def getMissionPagesFromPdf(pdf):
    tableOfContents = pdf.pages[1].extract_text().splitlines()

    rawItsScenarios = []
    scenarioStartIndex = INFINITY

    rawDirectActions = []
    directActionStartIndex = INFINITY

    log(f"Searching PDF for missions")
    for i in range(len(tableOfContents)):
        scenarioPage = "its scenarios".upper()
        directActionPage = "its direct action".upper()
        resilienceOps = "resilience operations".upper()

        # detect the start/end of different sections of the PDF that we care about from the index page
        if scenarioPage in tableOfContents[i]:
            # found the start of its scenarios set start index
            scenarioStartIndex = i
            pageNum = int(tableOfContents[i].replace(scenarioPage, "").strip())
            log(f"\nFound ITS Scenarios @ {i} -> starting page number '{pageNum}'")
        elif directActionPage in tableOfContents[i]:
            # reset scenario index since we've started recording direct action missions
            scenarioStartIndex = INFINITY
            directActionStartIndex = i
            pageNum = int(tableOfContents[i].replace(directActionPage, "").strip())
            log(f"Found ITS Direct Actions @ table of contents {i} -> starting page number '{pageNum}'")
            # also push a special "~END-MISSION~" to itsScenarios
            rawItsScenarios.append({ "name": END_MISSION, "page": pageNum })
        elif resilienceOps in tableOfContents[i]:
            # end search as we've reached the end of missions
            scenarioStartIndex = INFINITY
            directActionStartIndex = INFINITY
            pageNum = int(tableOfContents[i].replace(resilienceOps, "").strip())
            # also push a special "~END-MISSION~" to directActions
            rawDirectActions.append({ "name": END_MISSION, "page": pageNum })

        # with an active start index for a given section save each line until it is no longer active
        if i > scenarioStartIndex or i > directActionStartIndex:
            res = re.match("^(.+\\s+)(\\d+)$", tableOfContents[i]) # type: ignore
            if res:
                name, page = res.groups()
                if scenarioStartIndex < directActionStartIndex:
                    rawItsScenarios.append({ "name": name.strip(), "page": int(page.strip()) })
                else:
                    rawDirectActions.append({ "name": name.strip(), "page": int(page.strip())})

    log(f"\nFound {len(rawItsScenarios)} scenarios in PDF", LOG_LEVELS.SIMPLE)
    for scenario in rawItsScenarios:
        log(f"\t'{scenario["name"]}' @ {scenario["page"]}", LOG_LEVELS.SIMPLE)

    log(f"\nFound {len(rawDirectActions)} direct actions in PDF", LOG_LEVELS.SIMPLE)
    for action in rawDirectActions:
        log(f"\t'{action["name"]}' @ {action["page"]}", LOG_LEVELS.SIMPLE)

    return { "itsScenarioData": rawItsScenarios, "directActionsData": rawDirectActions }

def getBlocksFromPages(pages: list[str], basePageNum = 0) -> list[TextBlock]:
    log("breaking page down to blocks of text")
    SKILL_SUBHEADERS = [
        "short skill",
        "long skill",
        "requirements",
        "effects"
    ]

    blocks: list[TextBlock] = []

    for i in range(len(pages)):
        lines = pages[i].splitlines()
        lastHeaderIndex = INFINITY
        subHeadIndexes = []
        lineCount = len(lines)
        log(f"\nPage {basePageNum + i} \\w [blue]LC:{lineCount}", LOG_LEVELS.SIMPLE)

        # process each line looking for headers/subheaders as the starts/ends of blocks
        for lineNum in range(lineCount):
            line = lines[lineNum]
            normalizedLine = line.lower().strip()
            isLastLine = (lineCount - 1) == lineNum

            # check if the current line is a header/subheader, which are all caps
            log(f"\tchecking line [bright_cyan]{lineNum+1} of {lineCount}", LOG_LEVELS.COMPLEX)
            log(f"\t\t'{line}'", LOG_LEVELS.COMPLEX)
            if line.isupper() or isLastLine:
                if normalizedLine not in SKILL_SUBHEADERS:
                    log("\t\t[yellow]is a header but not a subheader")
                    # if in an active block we've reached the start of another block, store the previous blocks
                    # contents
                    if lineNum > lastHeaderIndex or isLastLine:
                        log(f"\t\t\t[magenta]building block content {isLastLine}", LOG_LEVELS.COMPLEX)
                        blockContent = ''

                        # check if the current block has any active sub headers
                        subheadCount = len(subHeadIndexes)
                        if subheadCount > 0:
                            # with sub headers block will be a dict of sub blocks
                            blockContent = {}

                            for i in range(subheadCount):
                                shi = subHeadIndexes[i]

                                end = lineNum + (1 if isLastLine else 0)
                                if i < subheadCount - 1:
                                    end = subHeadIndexes[i+1]

                                blockContent[toKey(lines[shi])] = linesToContent(lines[shi+1:end])
                        else:
                            end = lineNum + (1 if isLastLine else 0)
                            # with no sub headers block is simple text
                            blockContent = linesToContent(lines[lastHeaderIndex+1:end])

                        blockKey = toKey(lines[lastHeaderIndex])

                        # make empty blocks dicts for easy mapping later
                        if isinstance(blockContent, str) and len(blockContent) == 0:
                            blockContent = {}

                        blocks.append({
                            'key': blockKey,
                            'content': blockContent,
                            'page_index': basePageNum + i,
                        })

                        log(f"Created [bright_cyan]Block[/] <{blockKey}> size: {len(blockContent)}", LOG_LEVELS.SIMPLE)
                        log(f"\t\\w {subheadCount} subheaders {subHeadIndexes}", LOG_LEVELS.SIMPLE)
                        log(blockContent, LOG_LEVELS.COMPLEX, prettyPrint=True, max_string=200)
                    # set block header index for the next iteration
                    if not isLastLine:
                        log(f"\nFound section '{line}' @ [blue]lines[/][{0 if lastHeaderIndex == INFINITY else lastHeaderIndex}:{lineNum}]", LOG_LEVELS.COMPLEX)
                    lastHeaderIndex = lineNum
                else:
                    if lastHeaderIndex == INFINITY:
                        log(f"[brigh_red][bold]ERROR:[/] [italic]invalid subheader, no associated main header")
                    else:
                        log(f"\t[green3]subheader[/] <{toKey(line)}> @ [blue]L# {lineNum}")
                    subHeadIndexes.append(lineNum)

    log(f"found {len(blocks)} blocks", LOG_LEVELS.SIMPLE)
    log(blocks, LOG_LEVELS.COMPLEX, prettyPrint=True)
    return blocks

def blocksToMissionInfo(missionName: str, blocks: list[TextBlock]):
    SPECIAL_RULES_KEY = "scenario_special_rules"
    missionInfo = {
        "name": toTitle(missionName),
        SPECIAL_RULES_KEY: {}
    }

    isAfterSpecialRule = False
    for block in blocks:
        key = block["key"]
        content = block["content"]

        if len(content) > 0:
            if isAfterSpecialRule:
                missionInfo[SPECIAL_RULES_KEY][key] = content
            else:
                missionInfo[key] = content

        if key == SPECIAL_RULES_KEY:
            isAfterSpecialRule = True

    return missionInfo