Instructions for copilot

* run python task using the provided venv in .venv
* pylint checks for application code must alway be 10/10
* pylint duplicate code warnings in test are acceptable
* use info from the github action workflow for pylint
* you must not cheat to make pylint pass. no disabling of checks allowed.
* before implementing news features write the unit test for the feature. work test driven.
* testsuite must always pass
* use no deprecated functions and methods.
* format according pep8
* update plan.md and readme.md if necessary
* all documentation must be in english and up to date.
* keep docs streamlined and not overwhelming
* do not break the markdown formatting in plan.md and readme.md
* no automatic staging and commiting to the main branch.
* must be compatible with python 3.8,3.9,3.10,3.11
* if you cd into a directory, always cd back to the original directory after the task is done
* always follow the instructions above.
* Using f-string with direct string interpolation in SQL queries can lead to SQL injection vulnerabilities. Use parameterized queries instead.
* always double check the code for security issues, especially when dealing with user input or database queries.
* If you are working with Python code respect the pylint rules defined in the .pylintrc files (check the root of the project for the .pylintrc file and the subfolder the edited file resides).
* pep8 is the standard for Python code style, so you should always follow it.
* run autopep8 on the files you edit to ensure they are formatted correctly.