# Professional AI Prompt for Gemini CLI: Python Script Generation

## Objective
Generate a Python script that modifies project names in a database by replacing a specific string within project names for designated project numbers.

## Context
Create a new Python script similar in functionality to `lpp_b1_updater.py` that will update project names in a database by changing a specific string pattern.

## Specific Requirements
- **Reference Script**: Use `lpp_b1_updater.py` as a template/model for implementation
- **Project Numbers**: Target projects with numbers `3747_37` and `3747_38`
- **String Replacement**: Replace the string `LPP` with `KAJ` in project names
- **Database Operations**: Include proper database connection, query execution, and error handling
- **Code Quality**: Follow Python best practices, include comments, and ensure maintainability

## Expected Output
A complete, executable Python script that:
1. Connects to the database
2. Identifies projects with numbers `3747_37` and `3747_38`
3. Updates the project names by replacing `LPP` with `KAJ`
4. Includes proper error handling and logging
5. Follows the same structure and coding patterns as the reference script

## Constraints
- Maintain the same database connection approach as the reference script
- Preserve existing functionality while adding the new replacement logic
- Include appropriate validation before making changes to the database
- Follow the existing code style and naming conventions

## Additional Considerations
- Include rollback capabilities or dry-run functionality if present in the reference script
- Ensure the script handles potential exceptions gracefully
- Add appropriate logging to track the changes made
- Consider transaction management if the reference script implements it