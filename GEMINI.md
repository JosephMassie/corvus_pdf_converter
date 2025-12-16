# GEMINI.md

This document outlines the goals, scope, and collaboration plan for the `corvus_pdf_converter` project, with the assistance of the Gemini AI agent.

## Project Overview

The primary goal of the `corvus_pdf_converter` project is to parse the official "Infinity The Game" (ITS) tournament rules PDF. It extracts detailed information about game scenarios, direct actions, and other structured data (such as in-mission unit profiles and charts).

The extracted data is intended for use in a separate web application, which will provide users with an easily navigable and searchable format for viewing ITS scenario content.

## High-Level Goals

1.  **Accurate and Comprehensive Parsing:** Achieve high-fidelity extraction of all relevant game rules and scenario data from the source PDF.
2.  **Structured and Stable Output:** Produce a well-structured, consistent, and validated JSON output that can be reliably consumed by a web application.
3.  **Prepare for Open Source:** Establish a clean, maintainable, and well-tested codebase in preparation for a future open-source release.

## Technology Stack

-   **Language:** Python
-   **Core Libraries:**
    -   `pymupdf`: PDF text and data extraction.
    -   `click`: Command-line interface.
    -   `rich`: Formatted terminal output for debugging and status updates.
-   **Testing:** Manual validation via `test_mission_json_structure.py`.

## Agent's Role and Responsibilities

The Gemini agent's primary responsibilities are ordered by priority:

1.  **Reviewing Work:** Proactively review new code and changes to ensure quality, maintainability, and adherence to project conventions.
2.  **Design and Planning:** Assist in planning new features, designing data structures, and architecting refactors or improvements.
3.  **Writing Tests:** Develop and write tests to validate the accuracy of the parsing logic and the integrity of the output data.

The agent may occasionally assist with other tasks, such as direct implementation or refactoring, upon request.

## Development Workflow

Our collaboration will follow a structured workflow:

1.  **Planning:** We will discuss and define the requirements and implementation plan for new features or bug fixes.
2.  **Implementation:** The user will lead the implementation, with the agent providing support as defined by its role.
3.  **Review:** The agent will review the implemented changes, providing feedback and suggesting improvements.
4.  **Testing:** The agent will help create and run tests to verify that the changes are working as expected and have not introduced regressions.
5.  **Iteration:** We will repeat this cycle until the feature or fix is complete.

## Current Tasks

-   **Improve Unit Profile Parsing:** Enhance the parsing logic to correctly identify and extract mission-specific unit profiles and other data tables found within the "Mission Objectives" and "Scenario Special Rules" sections.
-   **Enhance Testing:** Augment the existing test script or develop new tests to validate the *content* of the extracted data, not just its structure.
