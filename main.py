import pymupdf  # PyMuPDF
import json
import re
import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from rich.pretty import pprint

console = Console()

def extract_scenarios_from_pdf(pdf_path, debug=False):
    """
    Extract ITS Scenarios and Direct Action scenarios from the PDF.
    """
    doc = pymupdf.open(pdf_path)
    
    # Parse the table of contents (page 1, index 1)
    toc_page = doc[1]
    toc_text = toc_page.get_text()
    
    if debug:
        console.print(f"\n[cyan]Table of Contents has {len(toc_text)} characters[/cyan]")
    
    # Get mission page mappings from TOC
    its_scenarios, direct_actions = parse_table_of_contents(toc_text, debug)
    
    if debug:
        # Pretty print the TOC results
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
    
    # Extract each ITS Scenario
    for i, scenario_info in enumerate(its_scenarios):
        scenario_name = scenario_info["name"]
        start_page = scenario_info["page"] - 1  # Convert to 0-indexed
        
        # Determine end page (start of next scenario or section)
        if i + 1 < len(its_scenarios):
            end_page = its_scenarios[i + 1]["page"] - 1
        else:
            # End at start of Direct Action section
            if direct_actions:
                end_page = direct_actions[0]["page"] - 1
            else:
                end_page = len(doc)
        
        console.print(f"\n[bold blue]Extracting ITS Scenario:[/bold blue] [yellow]{scenario_name}[/yellow]")
        console.print(f"  [cyan]Pages: {start_page + 1} to {end_page}[/cyan]")
        
        # Extract text from pages (normalized, no line breaks)
        scenario_text = extract_text_from_pages(doc, start_page, end_page)
        
        if debug:
            console.print(f"  [green]Extracted {len(scenario_text)} characters[/green]")
            preview = scenario_text[:300] if len(scenario_text) > 300 else scenario_text
            console.print(f"  [dim]Preview: {preview}...[/dim]")
        
        scenario_data = parse_scenario(scenario_name, scenario_text, debug=debug)
        scenarios.append(scenario_data)
    
    # Extract each Direct Action scenario
    for i, da_info in enumerate(direct_actions):
        da_name = da_info["name"]
        start_page = da_info["page"] - 1  # Convert to 0-indexed
        
        # Determine end page
        if i + 1 < len(direct_actions):
            end_page = direct_actions[i + 1]["page"] - 1
        else:
            # Look for "RESILIENCE OPERATIONS" as the end marker
            end_page = find_page_with_text(doc, "RESILIENCE OPERATIONS", start_page)
            if end_page == -1:
                end_page = len(doc)
        
        console.print(f"\n[bold blue]Extracting Direct Action:[/bold blue] [yellow]{da_name}[/yellow]")
        console.print(f"  [cyan]Pages: {start_page + 1} to {end_page}[/cyan]")
        
        # Extract text from pages (normalized, no line breaks)
        da_text = extract_text_from_pages(doc, start_page, end_page)
        
        if debug:
            console.print(f"  [green]Extracted {len(da_text)} characters[/green]")
            preview = da_text[:300] if len(da_text) > 300 else da_text
            console.print(f"  [dim]Preview: {preview}...[/dim]")
        
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
    
    # Normalize the TOC text for easier parsing
    toc_normalized = re.sub(r'\s+', ' ', toc_text)
    
    # Find ITS SCENARIOS section - look for the section and extract until ITS DIRECT ACTION
    its_match = re.search(r'ITS SCENARIOS\s+(\d+)\s+(.*?)\s+ITS DIRECT ACTION', toc_normalized, re.IGNORECASE)
    if its_match:
        scenarios_section = its_match.group(2)
        if debug:
            console.print(f"\n[dim]ITS Scenarios section: {scenarios_section[:200]}...[/dim]")
        
        # Extract scenario names and page numbers
        # Pattern: SCENARIO NAME followed by page number
        scenario_matches = re.findall(r'([A-Z][A-Z\s\-]+?)\s+(\d+)', scenarios_section)
        for name, page in scenario_matches:
            name = name.strip()
            # Filter out non-scenario entries
            if len(name) > 3 and name not in ['ITS SCENARIOS', 'EXTRAS', 'CLASSIFIED OBJECTIVES']:
                its_scenarios.append({"name": name, "page": int(page)})
    
    # Find ITS DIRECT ACTION section
    da_match = re.search(r'ITS DIRECT ACTION\s+(\d+)\s+(.*?)(?:RESILIENCE OPERATIONS|CHANGELOG)', toc_normalized, re.IGNORECASE)
    if da_match:
        da_section = da_match.group(2)
        if debug:
            console.print(f"\n[dim]Direct Action section: {da_section[:200]}...[/dim]")
        
        # Extract action names and page numbers
        da_matches = re.findall(r'([A-Z][A-Z\s\-]+?)\s+(\d+)', da_section)
        for name, page in da_matches:
            name = name.strip()
            if len(name) > 3:
                direct_actions.append({"name": name, "page": int(page)})
    
    return its_scenarios, direct_actions

def extract_text_from_pages(doc, start_page, end_page):
    """
    Extract and concatenate text from a range of pages.
    Returns text with preserved line structure for better parsing.
    """
    text = ""
    for page_num in range(start_page, end_page):
        if page_num < len(doc):
            page = doc[page_num]
            text += page.get_text() + "\n"
    
    # Normalize whitespace but preserve line breaks for parsing
    # Replace multiple spaces/tabs with single space, but keep newlines
    text = re.sub(r'[ \t]+', ' ', text)
    # Remove excessive newlines (more than 2 in a row)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def find_page_with_text(doc, search_text, start_page=0):
    """
    Find the first page containing the search text.
    Returns page index or -1 if not found.
    """
    for page_num in range(start_page, len(doc)):
        page = doc[page_num]
        page_text = page.get_text()
        if search_text in page_text:
            return page_num
    return -1

def parse_scenario(name, text, is_direct_action=False, debug=False):
    """
    Parse a scenario's text and extract structured information.
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
    match = re.search(r'TACTICAL\s+SUPPORT\s+OPTIONS\s+(\d+)', text, re.IGNORECASE)
    if debug and match:
        console.print(f"    [green]✓ Found tactical support: {match.group(1)}[/green]")
    elif debug:
        console.print(f"    [red]✗ Tactical support not found[/red]")
    return int(match.group(1)) if match else None

def extract_reinforcements(text, debug=False):
    """Extract whether suitable for reinforcements."""
    match = re.search(r'SUITABLE\s+FOR\s+REINFORCEMENTS\s+(YES|NO)', text, re.IGNORECASE)
    if debug and match:
        console.print(f"    [green]✓ Found reinforcements: {match.group(1)}[/green]")
    elif debug:
        console.print(f"    [red]✗ Reinforcements not found[/red]")
    return match.group(1).upper() == "YES" if match else None

def extract_objectives(text, debug=False):
    """Extract mission objectives."""
    objectives = {}
    
    # Find the MISSION OBJECTIVES section
    obj_match = re.search(r'MISSION\s+OBJECTIVES\s+(.*?)(?:FORCES\s+AND\s+DEPLOYMENT|SCENARIO\s+SPECIAL)', text, re.DOTALL | re.IGNORECASE)
    if not obj_match:
        if debug:
            console.print(f"    [red]✗ MISSION OBJECTIVES section not found[/red]")
        return objectives
    
    obj_text = obj_match.group(1)
    if debug:
        console.print(f"    [green]✓ Found objectives section ({len(obj_text)} chars)[/green]")
    
    # Strategy: find headers by looking for all-caps words at the start of a line
    # A header is a line that is predominantly uppercase (>80% uppercase letters)
    lines = obj_text.split('\n')
    current_section = None
    current_content = []
    
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        
        # Check if this is a header (mostly uppercase)
        if line_stripped and len(line_stripped) > 2:
            upper_count = sum(1 for c in line_stripped if c.isupper())
            lower_count = sum(1 for c in line_stripped if c.islower())
            is_header = upper_count > 0 and (lower_count == 0 or upper_count / (upper_count + lower_count) > 0.8)
        else:
            is_header = False
        
        if is_header:
            # Save previous section
            if current_section and current_content:
                content_str = '\n'.join(current_content)
                # Extract bullet points, removing ^ prefix
                items = re.split(r'\n\s*\^\s*', content_str)
                objective_items = []
                for item in items:
                    item = item.strip()
                    # Remove leading ^ if present
                    item = re.sub(r'^\^\s*', '', item)
                    # Clean up line breaks within objectives
                    item = re.sub(r'\s*\n\s*', ' ', item)
                    # Remove extra spaces
                    item = re.sub(r'\s+', ' ', item)
                    if item and len(item) > 5:
                        objective_items.append(item)
                
                if objective_items:
                    header_key = current_section.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_').replace('/', '_')
                    objectives[header_key] = objective_items
                    if debug:
                        console.print(f"    [green]✓ Found {len(objective_items)} objectives for '{current_section}'[/green]")
            
            current_section = line_stripped
            current_content = []
        else:
            if current_section:
                current_content.append(line_stripped)
    
    # Don't forget the last section
    if current_section and current_content:
        content_str = '\n'.join(current_content)
        items = re.split(r'\n\s*\^\s*', content_str)
        objective_items = []
        for item in items:
            item = item.strip()
            # Remove leading ^ if present
            item = re.sub(r'^\^\s*', '', item)
            # Clean up line breaks within objectives
            item = re.sub(r'\s*\n\s*', ' ', item)
            # Remove extra spaces
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
    """Extract deployment information."""
    deployment = {
        "sides": "SIDE A and SIDE B",
        "deployment_table": [],
        "special_notes": []
    }
    
    # Find deployment section
    deploy_match = re.search(r'FORCES\s+AND\s+DEPLOYMENT\s+(.*?)(?:SCENARIO\s+SPECIAL\s+RULES|LAUNCHING\s+TOWER|SERVER\s+ROOM|QUADRANTS)', text, re.DOTALL | re.IGNORECASE)
    if not deploy_match:
        if debug:
            console.print(f"    [red]✗ FORCES AND DEPLOYMENT section not found[/red]")
        return deployment
    
    deploy_text = deploy_match.group(1)
    if debug:
        console.print(f"    [green]✓ Found deployment section ({len(deploy_text)} chars)[/green]")
    
    # Extract army points configurations
    # Look for pattern: "A and B" or "SIDE A and SIDE B" followed by numbers and table sizes
    # Pattern: army points, SWC, table size, deployment zone
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
    
    # Extract special deployment notes
    notes = re.findall(r'(?:It\s+is\s+(?:not\s+)?(?:allowed|permitted)[^.]+\.|Exclusion\s+Zone[^.]+\.)', deploy_text, re.IGNORECASE)
    deployment["special_notes"] = [
        re.sub(r'\s*\n\s*', ' ', note.strip()) 
        for note in notes
    ]
    
    if debug and deployment["special_notes"]:
        console.print(f"    [green]✓ Found {len(deployment['special_notes'])} special notes[/green]")
    
    return deployment

def extract_special_rules(text, debug=False):
    """Extract scenario special rules, including skill-based rules with structured parsing."""
    rules = {}
    
    # Find special rules section - look for SCENARIO SPECIAL RULES and extract until the next main section
    # Don't stop at END OF THE MISSION since special rules can appear after it
    rules_match = re.search(r'SCENARIO\s+SPECIAL\s+RULES\s+(.*)', text, re.DOTALL | re.IGNORECASE)
    if not rules_match:
        if debug:
            console.print(f"    [red]✗ SCENARIO SPECIAL RULES section not found[/red]")
        return rules
    
    # Extract the full text after "SCENARIO SPECIAL RULES"
    # We'll parse headers and stop when we no longer find valid rule headers
    rules_text = rules_match.group(1)
    if debug:
        console.print(f"    [green]✓ Found special rules section ({len(rules_text)} chars)[/green]")
    
    # Subsection headers and end markers that appear within/after rules and should be skipped
    subsection_headers = {'SHORT SKILL', 'SHORT MOVEMENT SKILL', 'LONG SKILL', 'REQUIREMENTS', 'EFFECTS', 'CANCELATION', 'END OF THE MISSION', 'END OF MISSION'}
    
    # Strategy: Build a list of all headers with their positions, handling multi-line headers
    # Multi-line headers are consecutive all-caps lines that aren't subsection headers or followed by content
    headers_list = []
    
    for header_match in re.finditer(r'^([A-Z][A-Z \t\-\(\)\/]*[A-Z])[ \t]*$', rules_text, re.MULTILINE):
        header_text = header_match.group(1).strip()
        
        # Check if header is ALL CAPS (no lowercase letters) - this filters out wrapped text
        if any(c.islower() for c in header_text):
            continue
        
        # Check if it's a subsection header
        if header_text in subsection_headers or len(header_text) < 3:
            continue
        
        headers_list.append({
            'text': header_text,
            'start': header_match.start(),
            'end': header_match.end(),
            'match': header_match
        })
    
    # Now merge consecutive headers that form multi-line headers
    # A multi-line header occurs when: header1 is followed immediately by header2, and header2 is not a subsection header
    # The merged header should be used as the rule name
    merged_headers = []
    skip_indices = set()
    
    for i, header_info in enumerate(headers_list):
        if i in skip_indices:
            continue
        
        merged_header = header_info['text']
        merged_start = header_info['start']
        merged_end = header_info['end']
        current_idx = i
        
        # Look ahead to see if the next header should be merged (is a continuation line)
        while current_idx + 1 < len(headers_list):
            next_header = headers_list[current_idx + 1]
            # Check if headers are adjacent (only whitespace/newlines between them)
            between_text = rules_text[merged_end:next_header['start']]
            
            # If there's substantial content between headers, they're separate
            if between_text.strip():
                break
            
            # If the next header line is very short or looks like a continuation, merge it
            # A continuation line would be short (< 50 chars) and not a subsection header
            if len(next_header['text']) < 50 and next_header['text'] not in subsection_headers:
                merged_header += " " + next_header['text']
                merged_end = next_header['end']
                skip_indices.add(current_idx + 1)
                current_idx += 1
            else:
                break
        
        merged_headers.append({
            'text': merged_header,
            'start': merged_start,
            'end': merged_end
        })
    
    # Now process the merged headers to extract rule content
    rule_count = 0
    
    for i, header_info in enumerate(merged_headers):
        header = header_info['text']
        header_end = header_info['end']
        
        # Find the next header's start position to determine where this rule's content ends
        if i + 1 < len(merged_headers):
            next_header_start = merged_headers[i + 1]['start']
        else:
            next_header_start = len(rules_text)
        
        # Extract content between this header and next header
        content = rules_text[header_end:next_header_start].strip()
        
        if not content or len(content) < 10:
            continue
        
        rule_key = header.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('-', '_').replace('/', '_')
        
        # Check if this is a skill-based rule
        if re.search(r'(SHORT( MOVEMENT)?|LONG)\s+SKILL', content, re.IGNORECASE):
            # Parse as structured skill rule
            rule_data = parse_skill_rule(header, content, debug)
            rules[rule_key] = rule_data
        else:
            # Parse as regular rule text
            content = re.sub(r'\n\s+(?=[a-z])', ' ', content)
            content = re.sub(r'\s+', ' ', content)
            content = content.strip()
            
            if content:
                rules[rule_key] = content[:2000] if len(content) > 2000 else content
        
        rule_count += 1
    
    if debug:
        console.print(f"\t[green]✓ Found {rule_count} special rules[/green]")
        if rules and debug:
            for rule_name, rule in rules.items():
                console.print(f"\t- {rule_name}{' (skill)' if isinstance(rule, dict) else ''}")
    
    return rules


def parse_skill_rule(header, full_text, debug=False):
    """Parse a skill-based rule into structured format with skill_type, requirements, and effects."""
    rule = {"name": header}

    if debug:
        console.print(f"      [blue]Parsing skill rule:[/blue] {header}")
    
    # Extract skill type (SHORT SKILL or LONG SKILL) with labels on the next line(s)
    skill_match = re.search(r'(SHORT|LONG)\s+SKILL\s*\n\s*(.*?)(?:\nREQUIREMENTS|\nEFFECTS)', full_text, re.IGNORECASE | re.DOTALL)
    if skill_match:
        skill_type = skill_match.group(1).lower()
        labels = skill_match.group(2).strip()
        # Clean up labels - remove extra whitespace including special chars
        labels = re.sub(r'\s+', ' ', labels).strip()
        rule["skill_type"] = f"{skill_type} skill, {labels}"
    
    # Extract REQUIREMENTS section
    # Pattern: REQUIREMENTS followed by content until EFFECTS, CANCELATION, or next header
    req_match = re.search(r'REQUIREMENTS\s*\n\s*(.*?)(?=\nEFFECTS|\nCANCELATION|\n[A-Z][A-Z\s]+\n|$)', full_text, re.IGNORECASE | re.DOTALL)
    if req_match:
        requirements = req_match.group(1).strip()
        # Clean up the special punctuation space character and newlines
        requirements = requirements.replace('\u2008', '')  # Remove punctuation space
        # Join bullet points, preserve structure
        requirements = re.sub(r'\n\s*►\s*', ' • ', requirements)
        requirements = re.sub(r'^\s*►\s*', '• ', requirements)
        # Join lines that continue text
        requirements = re.sub(r'\s*\n\s*(?=[a-z•])', ' ', requirements)
        requirements = re.sub(r'\s+', ' ', requirements).strip()
        rule["requirements"] = requirements
    
    # Extract EFFECTS section
    # Pattern: EFFECTS followed by content until CANCELATION, a new skill header (SHORT/LONG SKILL), or end
    eff_match = re.search(r'EFFECTS\s*\n\s*(.*?)(?=\nCANCELATION|\n(?:SHORT|LONG)\s+SKILL|$)', full_text, re.IGNORECASE | re.DOTALL)
    if eff_match:
        effects = eff_match.group(1).strip()
        # Clean up the special punctuation space character and newlines
        effects = effects.replace('\u2008', '')  # Remove punctuation space
        # Join bullet points, preserve structure
        effects = re.sub(r'\n\s*►\s*', ' • ', effects)
        effects = re.sub(r'^\s*►\s*', '• ', effects)
        # Join lines that continue text
        effects = re.sub(r'\s*\n\s*(?=[a-z•])', ' ', effects)
        effects = re.sub(r'\s+', ' ', effects).strip()
        rule["effects"] = effects
    
    # Extract CANCELATION section if present
    cancel_match = re.search(r'CANCELATION\s*\n\s*(.*?)(?=\n[A-Z][A-Z\s]+\n|$)', full_text, re.IGNORECASE | re.DOTALL)
    if cancel_match:
        cancelation = cancel_match.group(1).strip()
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
    """Extract end of mission section."""
    # Find END OF THE MISSION section
    end_match = re.search(r'END\s+OF\s+THE\s+MISSION\s+(.*?)(?:$|\d+\s+[A-Z][A-Z\s]+TACTICAL\s+SUPPORT)', text, re.DOTALL | re.IGNORECASE)
    if not end_match:
        if debug:
            console.print(f"    [red]✗ END OF THE MISSION section not found[/red]")
        return None
    
    end_text = end_match.group(1).strip()
    # Clean up line breaks
    end_text = re.sub(r'\s*\n\s*', ' ', end_text)
    # Remove extra spaces
    end_text = re.sub(r'\s+', ' ', end_text)
    
    if debug:
        console.print(f"    [green]✓ Found end of mission section ({len(end_text)} chars)[/green]")
    
    return end_text[:1000] if len(end_text) > 1000 else end_text

@click.command()
@click.argument("pdf_path", type=click.Path(exists=True))
@click.option("--debug", is_flag=True, help="Enable debug output")
def main(pdf_path, debug):
    """Extract ITS scenarios from PDF and save to JSON."""
    console.print(f"\n[bold cyan]Extracting scenarios from PDF:[/bold cyan] {pdf_path}\n")
    
    scenarios = extract_scenarios_from_pdf(pdf_path, debug=debug)
    
    output = {
        "season": "Season 17",
        "version": "v1.0.1",
        "scenarios": scenarios
    }
    
    # Save to JSON file
    with open("its_scenarios.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    console.print(f"\n[bold green]✓ Extracted {len(scenarios)} scenarios[/bold green]")
    console.print(f"[bold green]✓ Output saved to its_scenarios.json[/bold green]\n")
    
    if scenarios:
        console.print("[bold]First scenario sample:[/bold]")
        rprint(scenarios[0])

if __name__ == "__main__":
    main()