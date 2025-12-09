import json
from pathlib import Path
from collections import Counter

# Load the output JSON from your main script
json_file = Path(__file__).parent / "its_scenarios.json"
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Define expected structure for each mission
# Each mission should have these keys
EXPECTED_MISSION_KEYS = {
    "name",
    "type",
    "tactical_support_options",
    "suitable_for_reinforcements",
    "mission_objectives",
    "forces_and_deployment",
    "scenario_special_rules",
    "end_of_mission"
}

# Required main sections that must exist
REQUIRED_SECTIONS = {
    "mission_objectives",
    "forces_and_deployment",
    "scenario_special_rules",
    "end_of_mission"
}

def get_section_structure(section_data):
    """
    Analyze the structure of a section.
    Returns a tuple of (type, structure_description)
    """
    if section_data is None:
        return "null", "None"
    elif isinstance(section_data, str):
        return "string", f"string ({len(section_data)} chars)"
    elif isinstance(section_data, list):
        if len(section_data) == 0:
            return "list", "empty list"
        first_item = section_data[0]
        if isinstance(first_item, str):
            return "list", f"list of {len(section_data)} string(s)"
        elif isinstance(first_item, dict):
            return "list", f"list of {len(section_data)} dict(s) with keys: {set(first_item.keys())}"
        else:
            return "list", f"list of {len(section_data)} {type(first_item).__name__}(s)"
    elif isinstance(section_data, dict):
        if len(section_data) == 0:
            return "dict", "empty dict"
        return "dict", f"dict with {len(section_data)} keys: {set(section_data.keys())}"
    else:
        return type(section_data).__name__, str(section_data)


def test_mission_structure(data):
    """Test the structure of all missions in the JSON data."""
    scenarios = data.get("scenarios", [])
    
    if not scenarios:
        print("❌ No scenarios found in JSON data.")
        return False
    
    print(f"\n📋 Testing {len(scenarios)} scenarios...\n")
    
    all_passed = True
    failed_missions = []
    section_types = {}
    
    for scenario in scenarios:
        mission_name = scenario.get("name", "UNKNOWN")
        mission_type = scenario.get("type", "UNKNOWN")
        actual_keys = set(scenario.keys())
        
        # Check if all expected keys are present
        missing_keys = EXPECTED_MISSION_KEYS - actual_keys
        
        mission_passed = True
        
        if missing_keys:
            print(f"❌ {mission_name}")
            print(f"   Missing keys: {sorted(missing_keys)}")
            mission_passed = False
            all_passed = False
        
        # Check that all required sections exist
        for section in REQUIRED_SECTIONS:
            if section not in scenario:
                print(f"❌ {mission_name} - Missing section: {section}")
                mission_passed = False
                all_passed = False
                continue
            
            section_data = scenario[section]
            struct_type, struct_desc = get_section_structure(section_data)
            
            # Track section structure patterns
            key = f"{mission_type}:{section}:{struct_type}"
            if key not in section_types:
                section_types[key] = []
            section_types[key].append(mission_name)
        
        if mission_passed:
            print(f"✅ {mission_name}")
        else:
            failed_missions.append(mission_name)
    
    print(f"\n{'='*70}")
    if all_passed:
        print(f"✅ All {len(scenarios)} scenarios passed validation!")
    else:
        print(f"❌ {len(failed_missions)} scenario(s) failed validation:")
        for mission in failed_missions:
            print(f"   - {mission}")
    
    print(f"{'='*70}\n")
    
    # Print structure analysis
    print("📊 Section Structure Analysis by Mission Type:\n")
    
    # Group by mission type
    structure_by_type = {}
    for key, missions in section_types.items():
        mission_type, section, struct_type = key.split(":")
        if mission_type not in structure_by_type:
            structure_by_type[mission_type] = {}
        if section not in structure_by_type[mission_type]:
            structure_by_type[mission_type][section] = {}
        structure_by_type[mission_type][section][struct_type] = missions
    
    for mission_type in sorted(structure_by_type.keys()):
        print(f"  {mission_type}:")
        for section in sorted(structure_by_type[mission_type].keys()):
            struct_info = structure_by_type[mission_type][section]
            for struct_type, missions in struct_info.items():
                print(f"    • {section}: {struct_type} ({len(missions)} mission(s))")
                if len(missions) <= 3:
                    for m in missions:
                        print(f"      - {m}")
        print()
    
    return all_passed

def print_structure_summary(data):
    """Print a summary of the JSON structure."""
    scenarios = data.get("scenarios", [])
    
    print(f"\n📊 Structure Summary:")
    print(f"   Total scenarios: {len(scenarios)}")
    print(f"   Season: {data.get('season')}")
    print(f"   Version: {data.get('version')}")
    print(f"\nScenario names:")
    for i, scenario in enumerate(scenarios, 1):
        print(f"   {i:2d}. {scenario.get('name')}")
    print()

if __name__ == "__main__":
    print_structure_summary(data)
    success = test_mission_structure(data)
    exit(0 if success else 1)
