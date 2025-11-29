import click

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
    log(object, prettyPrint=True)
    map = {}
    for key, value in object.items():
        if isinstance(value, dict):
            map[key] = makeMap(value)
        else:
            map[key] = type(value)
    return map

def interactiveBlocksToMission(name: str, blocks: list[TextBlock]):
    missionName = toTitle(name)
    log(f"[bold]Mapping [deep_sky_blue1]<{name}>")


    answer = click.prompt(
        "Rename mission? " + click.style("Leave empty to keep parsed name", fg="blue"),
        default=missionName,
    )

    mission = {
        "name": answer
    }

    for block in blocks:
        options = getAllProps(mission)
        options.reverse()

        missionMap = makeMap(mission)

        log("\n[grey93]Current structure:")
        log(missionMap, prettyPrint=True, expand_all=True, max_string=60)
        log(f"\n[bold][bright_blue]<{block['key']}>[/bright_blue] [turquoise4]preview[/]\n\t{block['preview']}")

        log("Options:")
        log(f"\t[bright_green]0:[/] [cyan]root")
        log(f"\t[bright_green]1:[/] [orange_red1]drop")
        for i, option in enumerate(options):
            log(f"\t[bright_green]{i+2}:[/] {option}")
        options = ["root", "drop", *options]

        answer = click.prompt(
            click.style(f"Where to store ", fg="bright_green") + click.style(f"<{block['key']}>", fg="bright_blue", bold=True) + "\n\tenter the corresponding number\n\t'drop' will not use the property at all",
            type=click.Choice(range(len(options))),
            show_choices=False
        )

        log(f"\n[bold]chose [bright_green]{answer}", LOG_LEVELS.COMPLEX)

        target = mission
        answer = options[int(answer)]

        if answer == "drop":
            log(f"[orange_red1 italic]dropping {block['key']}", LOG_LEVELS.SIMPLE)
            continue
        elif answer != "root":
            propChain = strToKeys(answer)
            for prop in propChain:
                target = target[prop]
                if not isinstance(target, dict):
                    log(f"[bright_red italic]invalid target {prop} is [bold]{type(target)}[/] expected [bold]dict[/]")

        log(target, LOG_LEVELS.COMPLEX, prettyPrint=True, max_string=60)
        target[block['key']] = block["content"]

        click.clear()

    return mission
