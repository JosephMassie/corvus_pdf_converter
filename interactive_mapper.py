from click import Abort
import questionary

from mission_parser import TextBlock
from lib.logger import LOG_LEVELS, log

from lib.string_utils import toTitle, toKey, keysToStr, strToKeys

from typing import Dict, List, Any

def getAllProps(object: Dict[str, Any], ancestors: List[str] = []):
    results: list[str] = []

    for key, value in object.items():
        if isinstance(value, dict):
            results.append(keysToStr([*ancestors, key]))
            results = [*results, *getAllProps(value, [*ancestors, key])]

    return results

def createPropertyQuestion():
    return {
        "type": "input",
        "name": "useExistingMap"
    }

def makeMap(object: Dict[str, Any]):
    map = {}
    for key, value in object.items():
        if isinstance(value, dict):
            map[key] = makeMap(value)
        else:
            map[key] = type(value).__name__
    return map

def interactiveBlocksToMission(name: str, blocks: list[TextBlock]):
    missionName = toTitle(name)
    log(f"[bold]Mapping [deep_sky_blue1]<{name}>")


    answer = questionary.text(
        "Rename mission? Leave empty to keep parsed name",
        default=missionName
    ).ask()

    mission = {
        "name": answer
    }

    for block in blocks:
        missionMap = makeMap(mission)

        key = block["key"]
        content = block["content"]

        rootOption = "root"

        dropBlockOption = "drop"
        editKeyOption = "edit key"
        editContentOption = "edit content"

        specialOptions = [dropBlockOption, editKeyOption, editContentOption]
        # only allow content to be edited if it is text or an empty dict
        if isinstance(content, dict) and len(content) > 0:
            specialOptions.remove(editContentOption)
        
        options = [
            *specialOptions,
            rootOption,
            *getAllProps(mission)
        ]

        isEditing = True
        while isEditing:
            log("\n[grey93]Current structure:")
            log(missionMap, prettyPrint=True, expand_all=True, max_string=60)
            log(f"\n[bold]<[bright_blue]{key}[/]>")
            if len(content) == 0:
                log("[bold turquoise4]preview")
                log("[red italic]\tempty block")
            elif isinstance(content, dict):
                log("[bold turquoise4]preview")
                log(content, prettyPrint=True, max_string=40)
            else:
                log(f"[bold][turquoise4]preview[/]\n\t{content[:80]}")

            log(f"\nWhere to store [bold]<[bright_blue]{key}[/][/]>\n\tenter the corresponding number\n\t'drop' will not use the property at all")
            answer = questionary.select(
                "",
                choices=options
            ).ask()

            log(f"chose [bright_green]{answer}", LOG_LEVELS.COMPLEX)

            # if the user made either no choice, an invlaid choice or quit exit interactive
            if answer == None:
                # user quit prompt
                raise Abort
            # if the user chose a special option handle it directly
            elif answer in specialOptions:
                if answer == dropBlockOption:
                    log(f"[orange_red1 italic]dropping {key}", LOG_LEVELS.SIMPLE)
                    isEditing = False
                    continue
                elif answer == editKeyOption:
                    key = questionary.text("What should the key be?", default=key).ask()
                elif answer == editContentOption:
                    # change empty dicts to empty strings
                    if isinstance(content, dict):
                        content = ""
                    log(f"Edit content of [bold]<[bright_blue]{key}[/][/]>")
                    content = questionary.text(
                        "",
                        default=content,
                        multiline=True
                    ).ask()
            # if the user chose a location including root insert the content into the correct location
            else:
                target = mission
                # the chose a location other than root find that target
                if answer != rootOption:
                    propChain = strToKeys(answer)
                    for prop in propChain:
                        target = target[prop]
                        if not isinstance(target, dict):
                            log(f"[bright_red italic]invalid target {prop} is [bold]{type(target)}[/] expected [bold]dict[/]")
                isEditing = False

                log(target, LOG_LEVELS.COMPLEX, prettyPrint=True, max_string=60)
                target[key] = content

    return mission
