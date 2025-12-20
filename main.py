#! .venv/bin/python3

import pymupdf  # PyMuPDF
import json
import re
import click
from rich.console import Console
from rich.table import Table
from rich.pretty import pprint
import os

console = Console()

def extract_scenarios_from_pdf(pdf_path, debug=False, raw=False):
    """
    Main function to orchestrate the extraction of ITS Scenarios and Direct Action 
    scenarios from the provided PDF file. It reads the table of contents, then 
    iterates through each identified scenario, extracting and parsing the text
    from the relevant pages.
    """
    doc = pymupdf.open(pdf_path)
    
    # The table of contents is consistently on the second page (index 1) of the PDF.
    # This page is crucial for locating the scenarios.
    toc_page = doc[1]
    toc_text = toc_page.get_text()
    
    if debug:
        console.print(f"\n[cyan]Table of Contents has {len(toc_text)} characters[/cyan]")

    if raw:
        output_txt_path = pdf_path.replace('.pdf', '.txt')
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            text = ""
            for i in range(len(doc)):
                text += doc[i].get_text() # type: ignore
            f.write(text)
    
    # Parse the raw text of the table of contents to get a structured list of
    # scenario names and the pages they start on.
    its_scenarios, direct_actions = parse_table_of_contents(toc_text, debug)
    
    if debug:
        # For debugging, print the parsed TOC data in formatted tables.
        console.print("\n[bold green]ITS Scenarios found in TOC:[/bold green]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("Page", style="yellow")
        for scenario in its_scenarios:
            table.add_row(scenario["name"], str(scenario["page"]))
        console.print(table)
        
        console.print("\n[bold green]Direct Actions found in TOC:[/bold green]")
        table2 = Table(show_header=True, header_style="bold magenta")
        table2.add_column("Name", style="cyan")
        table2.add_column("Page", style="yellow")
        for action in direct_actions:
            table2.add_row(action["name"], str(action["page"]))
        console.print(table2)
    
    scenarios = []
    
    # Process each ITS Scenario found in the table of contents.
    for i, scenario_info in enumerate(its_scenarios):
        scenario_name = scenario_info["name"]
        start_page = scenario_info["page"] - 1  # Convert page number to 0-based index.
        
        # Determine the end page for the current scenario. This is typically the page
        # before the next scenario starts.
        if i + 1 < len(its_scenarios):
            end_page = its_scenarios[i + 1]["page"] - 1
        else:
            # If this is the last ITS scenario, it ends where the Direct Action section begins.
            if direct_actions:
                end_page = direct_actions[0]["page"] - 1
            else:
                # If no Direct Actions, it runs to the end of the document.
                end_page = len(doc)
        
        console.print(f"\n[bold blue]Extracting ITS Scenario:[/bold blue] [yellow]{scenario_name}[/yellow]")
        console.print(f"  [cyan]Pages: {start_page + 1} to {end_page}[/cyan]")
        
        # Extract all text from the calculated page range for this scenario.
        scenario_text = extract_text_from_pages(doc, start_page, end_page)

        if raw:
            os.makedirs("raw_text", exist_ok=True)
            with open(f"raw_text/{scenario_name}.txt", "w", encoding="utf-8") as f:
                f.write(scenario_text)
        
        if debug:
            console.print(f"  [green]Extracted {len(scenario_text)} characters[/green]")
            preview = scenario_text[:300] if len(scenario_text) > 300 else scenario_text
            console.print(f"  [dim]Preview: {preview}...[/dim]")
        
        # Parse the extracted text to get structured data for the scenario.
        scenario_data = parse_scenario(scenario_name, scenario_text, debug=debug)
        scenarios.append(scenario_data)
    
    # Process each Direct Action scenario similarly.
    for i, da_info in enumerate(direct_actions):
        da_name = da_info["name"]
        start_page = da_info["page"] - 1  # Convert to 0-indexed
        
        # Determine the end page for the current Direct Action.
        if i + 1 < len(direct_actions):
            end_page = direct_actions[i + 1]["page"] - 1
        else:
            # The last Direct Action ends at the "RESILIENCE OPERATIONS" section,
            # which we have to find manually as it's not in the TOC mission list.
            end_page = find_page_with_text(doc, "RESILIENCE OPERATIONS", start_page)
            if end_page == -1:
                end_page = len(doc) # Fallback to the end of the document.
        
        console.print(f"\n[bold blue]Extracting Direct Action:[/bold blue] [yellow]{da_name}[/yellow]")
        console.print(f"  [cyan]Pages: {start_page + 1} to {end_page}[/cyan]")
        
        # Extract text from the determined page range.
        da_text = extract_text_from_pages(doc, start_page, end_page)
        
        if debug:
            console.print(f"  [green]Extracted {len(da_text)} characters[/green]")
            preview = da_text[:300] if len(da_text) > 300 else da_text
            console.print(f"  [dim]Preview: {preview}...[/dim]")
        
        # Parse the text, flagging it as a Direct Action.
        da_data = parse_scenario(da_name, da_text, is_direct_action=True, debug=debug)
        scenarios.append(da_data)
    
    doc.close()
    
    return scenarios

def parse_table_of_contents(toc_text, debug=False):
    """
    Parse the table of contents to extract scenario names and page numbers.
    Returns tuple of (its_scenarios, direct_actions)
    """
    its_scenarios = []
    direct_actions = []
    
    # Normalize the TOC text by replacing any sequence of one or more whitespace
    # characters (spaces, tabs, newlines) with a single space. This simplifies
    # subsequent regex matching.
    toc_normalized = re.sub(r'\s+', ' ', toc_text)
    
    # Regex to find the "ITS SCENARIOS" section. It captures the content between
    # "ITS SCENARIOS" and "ITS DIRECT ACTION".
    # - `ITS SCENARIOS\s+(\d+)\s+`: Matches "ITS SCENARIOS", whitespace, a page number (ignored), and more whitespace.
    # - `(.*?)`: Non-greedily captures all characters (the scenario list).
    # - `\s+ITS DIRECT ACTION`: Matches the text that marks the end of the section.
    its_match = re.search(r'ITS SCENARIOS\s+(\d+)\s+(.*?)\s+ITS DIRECT ACTION', toc_normalized, re.IGNORECASE)
    if its_match:
        scenarios_section = its_match.group(2)
        if debug:
            console.print(f"\n[dim]ITS Scenarios section: {scenarios_section[:200]}...[/dim]")
        
        # Regex to find all scenario names and their corresponding page numbers.
        # - `([A-Z][A-Z\s\-]+?)`: Captures a scenario name. It must start with an uppercase letter
        #   and can contain other uppercase letters, spaces, or hyphens. The `+?` is non-greedy.
        # - `\s+`: Matches the space(s) between the name and the page number.
        # - `(\d+)`: Captures the page number.
        scenario_matches = re.findall(r'([A-Z][A-Z\s\-]+?)\s+(\d+)', scenarios_section)
        for name, page in scenario_matches:
            name = name.strip()
            # Filter out known non-scenario headers that might be accidentally matched.
            if len(name) > 3 and name not in ['ITS SCENARIOS', 'EXTRAS', 'CLASSIFIED OBJECTIVES']:
                its_scenarios.append({"name": name, "page": int(page)})
    
    # Regex to find the "ITS DIRECT ACTION" section. It captures content between
    # "ITS DIRECT ACTION" and either "RESILIENCE OPERATIONS" or "CHANGELOG".
    # - `ITS DIRECT ACTION\s+(\d+)\s+`: Matches the section header and its page number.
    # - `(.*?)`: Non-greedily captures the list of direct actions.
    # - `(?:RESILIENCE OPERATIONS|CHANGELOG)`: A non-capturing group that marks the end of the section.
    da_match = re.search(r'ITS DIRECT ACTION\s+(\d+)\s+(.*?)(?:RESILIENCE OPERATIONS|CHANGELOG)', toc_normalized, re.IGNORECASE)
    if da_match:
        da_section = da_match.group(2)
        if debug:
            console.print(f"\n[dim]Direct Action section: {da_section[:200]}...[/dim]")
        
        # Uses the same pattern as above to extract action names and page numbers.
        da_matches = re.findall(r'([A-Z][A-Z\s\-]+?)\s+(\d+)', da_section)
        for name, page in da_matches:
            name = name.strip()
            if len(name) > 3:
                direct_actions.append({"name": name, "page": int(page)})
    
    return its_scenarios, direct_actions

def extract_text_from_pages(doc, start_page, end_page):
    """
    Extract and concatenate text from a specified range of pages in the document.
    The text is normalized to clean up whitespace while preserving paragraph structure.
    """
    text = ""
    for page_num in range(start_page, end_page):
        if page_num < len(doc):
            page = doc[page_num]
            # Append the text of each page, followed by a newline to mark page breaks.
            text += page.get_text() + "\n"
    
    # Normalize whitespace for consistent parsing.
    # Replace one or more spaces or tabs with a single space.
    text = re.sub(r'[ \t]+', ' ', text)
    # Reduce three or more consecutive newlines to just two, preserving paragraph breaks
    # while eliminating excessive empty space.
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def find_page_with_text(doc, search_text, start_page=0):
    """
    Find the first page in the document that contains a specific string of text,
    starting the search from a given page.
    Returns the 0-based page index or -1 if the text is not found.
    """
    for page_num in range(start_page, len(doc)):
        page = doc[page_num]
        page_text = page.get_text()
        if search_text in page_text:
            return page_num
    return -1

def parse_scenario(name, text, is_direct_action=False, debug=False):
    """
    Top-level parser for a single scenario's text. It orchestrates calls to
    specialized functions to extract each distinct section of the scenario,
    such as objectives, deployment, and special rules.
    """
    scenario = {
        "name": name,
        "type": "Direct Action" if is_direct_action else "ITS Scenario",
        "tactical_support_options": extract_tactical_support(text, debug),
        "suitable_for_reinforcements": extract_reinforcements(text, debug),
        "mission_objectives": extract_objectives(text, debug),
        "forces_and_deployment": extract_deployment(text, debug),
        "scenario_special_rules": extract_special_rules(text, debug),
        "end_of_mission": extract_end_of_mission(text, debug)
    }
    
    return scenario

def extract_tactical_support(text, debug=False):
    """Extract tactical support options number."""
    # Regex to find the phrase "TACTICAL SUPPORT OPTIONS" followed by a number.
    # - `TACTICAL\s+SUPPORT\s+OPTIONS\s+`: Matches the literal text with flexible whitespace.
    # - `(\d+)`: Captures one or more digits (the number of options).
    match = re.search(r'TACTICAL\s+SUPPORT\s+OPTIONS\s+(\d+)', text, re.IGNORECASE)
    if debug and match:
        console.print(f"    [green]✓ Found tactical support: {match.group(1)}[/green]")
    elif debug:
        console.print(f"    [red]✗ Tactical support not found[/red]")
    return int(match.group(1)) if match else None

def extract_reinforcements(text, debug=False):
    """Extract whether suitable for reinforcements."""
    # Regex to find "SUITABLE FOR REINFORCEMENTS" followed by "YES" or "NO".
    # - `SUITABLE\s+FOR\s+REINFORCEMENTS\s+`: Matches the literal text.
    # - `(YES|NO)`: Captures either "YES" or "NO".
    match = re.search(r'SUITABLE\s+FOR\s+REINFORCEMENTS\s+(YES|NO)', text, re.IGNORECASE)
    if debug and match:
        console.print(f"    [green]✓ Found reinforcements: {match.group(1)}[/green]")
    elif debug:
        console.print(f"    [red]✗ Reinforcements not found[/red]")
    return match.group(1).upper() == "YES" if match else None

def extract_objectives(text, debug=False):
    """Extract mission objectives by finding the section and parsing its subsections."""
    objectives = {}
    
    # Regex to locate the "MISSION OBJECTIVES" section and capture all text until
    # the next major section header is encountered.
    # - `MISSION\s+OBJECTIVES\s+`: Matches the section start.
    # - `(.*?)`: Non-greedily captures the content of the section.
    # - `(?:FORCES\s+AND\s+DEPLOYMENT|SCENARIO\s+SPECIAL)`: A non-capturing group that defines
    #   the possible headers that terminate the objectives section.
    obj_match = re.search(r'MISSION\s+OBJECTIVES\s+(.*?)(?:FORCES\s+AND\s+DEPLOYMENT|SCENARIO\s+SPECIAL)', text, re.DOTALL | re.IGNORECASE)
    if not obj_match:
        if debug:
            console.print(f"    [red]✗ MISSION OBJECTIVES section not found[/red]")
        return objectives
    
    obj_text = obj_match.group(1)
    if debug:
        console.print(f"    [green]✓ Found objectives section ({len(obj_text)} chars)[/green]")
    
    # The strategy is to iterate through the lines of the section text, identifying
    # subsection headers. A header is assumed to be a line that is predominantly
    # composed of uppercase letters.
    lines = obj_text.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Heuristic to detect if a line is a header: it must have more than two characters,
        # contain at least one uppercase letter, and have a high ratio (80%+) of uppercase
        # to lowercase letters, or be entirely uppercase.
        if line_stripped and len(line_stripped) > 2:
            upper_count = sum(1 for c in line_stripped if c.isupper())
            lower_count = sum(1 for c in line_stripped if c.islower())
            is_header = upper_count > 0 and (lower_count == 0 or upper_count / (upper_count + lower_count) > 0.8)
        else:
            is_header = False
        
        if is_header:
            # When a new header is found, process the content of the previous section.
            if current_section and current_content:
                content_str = '\n'.join(current_content)
                # Objectives are often listed as bullet points starting with '^'.
                # Split the content by this pattern to get individual objectives.
                # - `\n\s*\^\s*`: Splits by a newline, optional whitespace, a '^', and optional whitespace.
                items = re.split(r'\n\s*\^\s*', content_str)
                objective_items = []
                for item in items:
                    item = item.strip()
                    # Clean up the objective text:
                    # - Remove any leading '^' that might remain.
                    item = re.sub(r'^\^\s*', '', item)
                    # Collapse newlines and whitespace within an objective into a single space.
                    item = re.sub(r'\s*\n\s*', ' ', item)
                    item = re.sub(r'\s+', ' ', item)
                    if item and len(item) > 5:
                        objective_items.append(item)
                
                if objective_items:
                    # Sanitize the header text to use as a JSON key.
                    header_key = current_section.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_').replace('/', '_')
                    objectives[header_key] = objective_items
                    if debug:
                        console.print(f"    [green]✓ Found {len(objective_items)} objectives for '{current_section}'[/green]")
            
            # Start a new section.
            current_section = line_stripped
            current_content = []
        else:
            # If not a header, append the line to the current section's content.
            if current_section:
                current_content.append(line_stripped)
    
    # After the loop, process the very last section found.
    if current_section and current_content:
        content_str = '\n'.join(current_content)
        items = re.split(r'\n\s*\^\s*', content_str)
        objective_items = []
        for item in items:
            item = item.strip()
            item = re.sub(r'^\^\s*', '', item)
            item = re.sub(r'\s*\n\s*', ' ', item)
            item = re.sub(r'\s+', ' ', item)
            if item and len(item) > 5:
                objective_items.append(item)
        
        if objective_items:
            header_key = current_section.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_').replace('/', '_')
            objectives[header_key] = objective_items
            if debug:
                console.print(f"    [green]✓ Found {len(objective_items)} objectives for '{current_section}'[/green]")
    
    return objectives

def extract_deployment(text, debug=False):
    """Extract deployment information, including army configurations and special notes."""
    deployment = {
        "sides": "SIDE A and SIDE B",
        "deployment_table": [],
        "special_notes": []
    }
    
    # Regex to find the "FORCES AND DEPLOYMENT" section and capture its content.
    # - `FORCES\s+AND\s+DEPLOYMENT\s+`: Matches the section header.
    # - `(.*?)`: Non-greedily captures the section content.
    # - `(?:SCENARIO\s+SPECIAL\s+RULES|...|QUADRANTS)`: A non-capturing group of possible
    #   section headers that signal the end of the deployment section.
    deploy_match = re.search(r'FORCES\s+AND\s+DEPLOYMENT\s+(.*?)(?:SCENARIO\s+SPECIAL\s+RULES|LAUNCHING\s+TOWER|SERVER\s+ROOM|QUADRANTS)', text, re.DOTALL | re.IGNORECASE)
    if not deploy_match:
        if debug:
            console.print(f"    [red]✗ FORCES AND DEPLOYMENT section not found[/red]")
        return deployment
    
    deploy_text = deploy_match.group(1)
    if debug:
        console.print(f"    [green]✓ Found deployment section ({len(deploy_text)} chars)[/green]")
    
    # Regex to find and extract rows from the army points table.
    # - `A\s+and\s+B\s+`: Matches the row identifier.
    # - `(\d{3,4})\s+`: Captures the army points (3 or 4 digits).
    # - `(\d+)\s+`: Captures the SWC value.
    # - `(\d+\s+in\s+x\s+\d+\s+in)\s+`: Captures the table size (e.g., "48 in x 48 in").
    # - `((?:\d+\s+in\s+x\s+\d+\s+in)|(?:Radius of\s+\d+\s+in))`: Captures the deployment zone,
    #   which can be rectangular or radial.
    army_configs = re.findall(
        r'A\s+and\s+B\s+(\d{3,4})\s+(\d+)\s+(\d+\s+in\s+x\s+\d+\s+in)\s+((?:\d+\s+in\s+x\s+\d+\s+in)|(?:Radius of\s+\d+\s+in))',
        deploy_text, re.IGNORECASE
    )
    for config in army_configs:
        deployment["deployment_table"].append({
            "army_points": int(config[0]),
            "swc": int(config[1]),
            "table_size": config[2].strip(),
            "deployment_zone": config[3].strip()
        })
    
    if debug:
        console.print(f"    [green]✓ Found {len(deployment['deployment_table'])} deployment configurations[/green]")
    
    # Regex to extract special deployment notes. These often start with specific phrases.
    # - `(?:It\s+is\s+(?:not\s+)?(?:allowed|permitted)[^.]+\.|Exclusion\s+Zone[^.]+\.)`:
    #   A non-capturing group that matches sentences starting with "It is (not) allowed/permitted..."
    #   or "Exclusion Zone...". It matches until the next period.
    notes = re.findall(r'(?:It\s+is\s+(?:not\s+)?(?:allowed|permitted)[^.]+\.|Exclusion\s+Zone[^.]+\.)', deploy_text, re.IGNORECASE)
    deployment["special_notes"] = [
        # Clean up each note by collapsing whitespace and newlines.
        re.sub(r'\s*\n\s*', ' ', note.strip()) 
        for note in notes
    ]
    
    if debug and deployment["special_notes"]:
        console.print(f"    [green]✓ Found {len(deployment['special_notes'])} special notes[/green]")
    
    return deployment

def extract_special_rules(text, debug=False):
    """
    Extracts scenario special rules, handling both simple text rules and complex,
    structured skill-based rules. The process involves identifying all rule
    headers, merging multi-line headers, and then parsing the content associated
    with each.
    """
    rules = {}
    
    # Regex to find the start of the special rules section.
    # - `SCENARIO\s+SPECIAL\s+RULES\s+`: Matches the section header.
    # - `(.*)`: Greedily captures everything that follows, as this section is typically
    #   the last major part of a scenario's definition. The DOTALL flag allows `.` to match newlines.
    rules_match = re.search(r'SCENARIO\s+SPECIAL\s+RULES\s+(.*)', text, re.DOTALL | re.IGNORECASE)
    if not rules_match:
        if debug:
            console.print(f"    [red]✗ SCENARIO SPECIAL RULES section not found[/red]")
        return rules
    
    rules_text = rules_match.group(1)
    if debug:
        console.print(f"    [green]✓ Found special rules section ({len(rules_text)} chars)[/green]")
    
    # Define a set of headers that are known to be subsections of a rule (e.g., for skills)
    # or other markers that should not be treated as the start of a new rule.
    subsection_headers = {'SHORT SKILL', 'SHORT MOVEMENT SKILL', 'LONG SKILL', 'REQUIREMENTS', 'EFFECTS', 'CANCELATION', 'END OF THE MISSION', 'END OF MISSION'}
    
    # --- Strategy: Find all potential headers first ---
    # A header is assumed to be a line consisting entirely of uppercase letters, spaces, and hyphens.
    # This helps distinguish rule titles from descriptive text.
    headers_list = []
    
    # Regex to find all-caps lines that could be headers.
    # - `^...$`: Anchors the match to the start and end of a line (due to MULTILINE flag).
    # - `([A-Z][A-Z \t\-\(\)\/]*[A-Z])`: Captures a line that starts and ends with an uppercase letter
    #   and contains only uppercase letters, spaces, tabs, hyphens, slashes, or parentheses in between.
    for header_match in re.finditer(r'^([A-Z][A-Z \t\-\(\)\/]*[A-Z])[ \t]*$', rules_text, re.MULTILINE):
        header_text = header_match.group(1).strip()
        
        # Filter out lines that contain lowercase letters, as they are likely wrapped text, not headers.
        if any(c.islower() for c in header_text):
            continue
        
        # Filter out known subsection headers and very short, likely erroneous matches.
        if header_text in subsection_headers or len(header_text) < 3:
            continue
        
        headers_list.append({
            'text': header_text,
            'start': header_match.start(),
            'end': header_match.end(),
            'match': header_match
        })
    
    # --- Strategy: Merge consecutive headers that form a single multi-line title ---
    # Some rule titles are split across multiple lines. This logic merges them.
    merged_headers = []
    skip_indices = set()
    
    for i, header_info in enumerate(headers_list):
        if i in skip_indices:
            continue
        
        merged_header = header_info['text']
        merged_end = header_info['end']
        current_idx = i
        
        # Look ahead to see if the next identified header is immediately adjacent and should be merged.
        while current_idx + 1 < len(headers_list):
            next_header = headers_list[current_idx + 1]
            
            # Check for any non-whitespace content between this header and the next.
            between_text = rules_text[merged_end:next_header['start']]
            if between_text.strip():
                break # If there's content, they are separate rules.
            
            # Merge if the next header line is short and not a known subsection header,
            # indicating it's likely a continuation of the title.
            if len(next_header['text']) < 50 and next_header['text'] not in subsection_headers:
                merged_header += " " + next_header['text']
                merged_end = next_header['end']
                skip_indices.add(current_idx + 1)
                current_idx += 1
            else:
                break
        
        merged_headers.append({
            'text': merged_header,
            'start': header_info['start'],
            'end': merged_end
        })
    
    # --- Strategy: Extract content for each merged header ---
    rule_count = 0
    
    for i, header_info in enumerate(merged_headers):
        header = header_info['text']
        header_end = header_info['end']
        
        # The content of the rule is the text between its header and the start of the next header.
        next_header_start = len(rules_text)
        if i + 1 < len(merged_headers):
            next_header_start = merged_headers[i + 1]['start']
        
        content = rules_text[header_end:next_header_start].strip()
        
        if not content or len(content) < 10:
            continue
        
        rule_key = header.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_').replace('/', '_')
        
        # Check if the content describes a structured skill (e.g., "SHORT SKILL").
        # - `(SHORT( MOVEMENT)?|LONG)\s+SKILL`: Matches "SHORT SKILL", "SHORT MOVEMENT SKILL", or "LONG SKILL".
        if re.search(r'(SHORT( MOVEMENT)?|LONG)\s+SKILL', content, re.IGNORECASE):
            # If it's a skill, use the specialized parser to extract its structured data.
            rule_data = parse_skill_rule(header, content, debug)
            rules[rule_key] = rule_data
        else:
            # Otherwise, treat it as a regular text rule.
            # Clean up the text by collapsing newlines and extra whitespace.
            # - `\n\s+(?=[a-z])`: Replaces a newline followed by spaces with a single space if it's
            #   part of a continuing sentence (i.e., the next character is lowercase).
            content = re.sub(r'\n\s+(?=[a-z])', ' ', content)
            content = re.sub(r'\s+', ' ', content)
            content = content.strip()
            
            if content:
                # Truncate very long rule descriptions.
                rules[rule_key] = content[:2000] if len(content) > 2000 else content
        
        rule_count += 1
    
    if debug:
        console.print(f"\t[green]✓ Found {rule_count} special rules[/green]")
        if rules and debug:
            for rule_name, rule in rules.items():
                console.print(f"\t- {rule_name}{' (skill)' if isinstance(rule, dict) else ''}")
    
    return rules



def parse_skill_rule(header, full_text, debug=False):
    """
    Parses a skill-based special rule into a structured format, extracting its
    type, labels, requirements, effects, and cancellation conditions.
    """
    rule = {"name": header}

    if debug:
        console.print(f"      [blue]Parsing skill rule:[/blue] {header}")
    
    # Regex to extract the skill type (e.g., "SHORT SKILL") and any associated labels
    # that appear on the following lines.
    # - `(SHORT|LONG)\s+SKILL\s*\n\s*`: Matches "SHORT" or "LONG" skill, followed by a newline.
    # - `(.*?)`: Non-greedily captures the labels on the next line(s).
    # - `(?:\nREQUIREMENTS|\nEFFECTS)`: A positive lookahead that stops capturing at the
    #   start of the REQUIREMENTS or EFFECTS section.
    skill_match = re.search(r'(SHORT|LONG)\s+SKILL\s*\n\s*(.*?)(?:\nREQUIREMENTS|\nEFFECTS)', full_text, re.IGNORECASE | re.DOTALL)
    if skill_match:
        skill_type = skill_match.group(1).lower()
        labels = skill_match.group(2).strip()
        # Clean up labels by collapsing all whitespace into single spaces.
        labels = re.sub(r'\s+', ' ', labels).strip()
        rule["skill_type"] = f"{skill_type} skill, {labels}"
    
    # Regex to extract the REQUIREMENTS section.
    # - `REQUIREMENTS\s*\n\s*`: Matches the section header.
    # - `(.*?)`: Non-greedily captures the content.
    # - `(?=\nEFFECTS|\nCANCELATION|\n[A-Z][A-Z\s]+\n|$)`: A positive lookahead that stops
    #   capturing at the start of the next known section (EFFECTS, CANCELATION), a new
    #   all-caps header, or the end of the string.
    req_match = re.search(r'REQUIREMENTS\s*\n\s*(.*?)(?=\nEFFECTS|\nCANCELATION|\n[A-Z][A-Z\s]+\n|$)', full_text, re.IGNORECASE | re.DOTALL)
    if req_match:
        requirements = req_match.group(1).strip()
        # Clean up the text:
        # - Remove specific unicode characters like punctuation space.
        requirements = requirements.replace('\u2008', '')  # Remove punctuation space
        # Standardize bullet points (►) by replacing them with a common marker.
        requirements = re.sub(r'\n\s*►\s*', ' • ', requirements)
        requirements = re.sub(r'^\s*►\s*', '• ', requirements)
        # Join lines that are part of a continuous sentence.
        requirements = re.sub(r'\s*\n\s*(?=[a-z•])', ' ', requirements)
        # Collapse all remaining whitespace to single spaces.
        requirements = re.sub(r'\s+', ' ', requirements).strip()
        rule["requirements"] = requirements
    
    # Regex to extract the EFFECTS section.
    # - `EFFECTS\s*\n\s*`: Matches the section header.
    # - `(.*?)`: Non-greedily captures the content.
    # - `(?=\nCANCELATION|\n(?:SHORT|LONG)\s+SKILL|$)`: Positive lookahead stops capturing
    #   at "CANCELATION", the start of a new skill definition, or the end of the string.
    eff_match = re.search(r'EFFECTS\s*\n\s*(.*?)(?=\nCANCELATION|\n(?:SHORT|LONG)\s+SKILL|$)', full_text, re.IGNORECASE | re.DOTALL)
    if eff_match:
        effects = eff_match.group(1).strip()
        # Apply the same text cleaning process as for requirements.
        effects = effects.replace('\u2008', '')  # Remove punctuation space
        effects = re.sub(r'\n\s*►\s*', ' • ', effects)
        effects = re.sub(r'^\s*►\s*', '• ', effects)
        effects = re.sub(r'\s*\n\s*(?=[a-z•])', ' ', effects)
        effects = re.sub(r'\s+', ' ', effects).strip()
        rule["effects"] = effects
    
    # Regex to extract the optional CANCELATION section.
    # - `CANCELATION\s*\n\s*`: Matches the section header.
    # - `(.*?)`: Non-greedily captures content.
    # - `(?=\n[A-Z][A-Z\s]+\n|$)`: Positive lookahead stops at the next all-caps header or the end.
    cancel_match = re.search(r'CANCELATION\s*\n\s*(.*?)(?=\n[A-Z][A-Z\s]+\n|$)', full_text, re.IGNORECASE | re.DOTALL)
    if cancel_match:
        cancelation = cancel_match.group(1).strip()
        # Apply the same text cleaning process.
        cancelation = cancelation.replace('\u2008', '')
        cancelation = re.sub(r'\n\s*►\s*', ' • ', cancelation)
        cancelation = re.sub(r'^\s*►\s*', '• ', cancelation)
        cancelation = re.sub(r'\s*\n\s*(?=[a-z•])', ' ', cancelation)
        cancelation = re.sub(r'\s+', ' ', cancelation).strip()
        rule["cancelation"] = cancelation
    
    if debug:
        pprint(rule, max_string=60)
    
    return rule

def extract_end_of_mission(text, debug=False):
    """Extracts the 'END OF THE MISSION' section text."""
    # Regex to find the "END OF THE MISSION" section and capture its content.
    # - `END\s+OF\s+THE\s+MISSION\s+`: Matches the section header.
    # - `(.*?)`: Non-greedily captures the content.
    # - `(?:$|\d+\s+[A-Z][A-Z\s]+TACTICAL\s+SUPPORT)`: A non-capturing group that stops
    #   capturing at either the end of the text (`$`) or what looks like the start of
    #   a table footer (e.g., "1 ITS SCENARIOS TACTICAL SUPPORT").
    end_match = re.search(r'END\s+OF\s+THE\s+MISSION\s+(.*?)(?:$|\d+\s+[A-Z][A-Z\s]+TACTICAL\s+SUPPORT)', text, re.DOTALL | re.IGNORECASE)
    if not end_match:
        if debug:
            console.print(f"    [red]✗ END OF THE MISSION section not found[/red]")
        return None
    
    end_text = end_match.group(1).strip()
    # Clean up the text by collapsing all newlines and excess whitespace into single spaces.
    end_text = re.sub(r'\s*\n\s*', ' ', end_text)
    end_text = re.sub(r'\s+', ' ', end_text)
    
    if debug:
        console.print(f"    [green]✓ Found end of mission section ({len(end_text)} chars)[/green]")
    
    # Truncate the text to a reasonable length to avoid excessively long entries.
    return end_text[:1000] if len(end_text) > 1000 else end_text

@click.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--json_output", type=click.Path(), help="Path to save the JSON output file")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--raw", is_flag=True, help="Output raw text from each scenario")
def main(pdf_path, debug, raw, json_output):
    """
    Command-line interface entrypoint for the script. It takes a PDF file path
    as input, orchestrates the scenario extraction, and saves the result to a
    JSON file.
    """
    console.print(f"\n[bold cyan]Extracting scenarios from PDF:[/bold cyan] {pdf_path}\n")
    
    # Run the main extraction process.
    scenarios = extract_scenarios_from_pdf(pdf_path, debug=debug, raw=raw)
    
    # Structure the final output with some metadata.
    output = {
        "season": "Season 17",
        "version": "v1.0.1",
        "scenarios": scenarios
    }
    
    jsonFileName = "infinity_its_missions.json" if not json_output else json_output

    # Write the structured data to a JSON file. `ensure_ascii=False` preserves
    # special characters, and `indent=2` makes the file human-readable.
    with open(jsonFileName, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    console.print(f"\n[bold green]✓ Extracted {len(scenarios)} scenarios[/bold green]")
    console.print(f"[bold green]✓ Output saved to {jsonFileName}[/bold green]\n")
    
    # Print a sample of the first extracted scenario for immediate verification.
    if scenarios:
        console.print("[bold]First scenario sample:[/bold]")
        pprint(scenarios[0], max_string=100)

if __name__ == "__main__":
    # This makes the script executable from the command line.
    main()