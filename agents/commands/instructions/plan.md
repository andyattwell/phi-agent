Your job is to write a software implementation plan.
Think hard about the best plan action.
If the work does not include modifications to the agents scripts, workflows, etc, all the files should be created in the `app/` directory.
If the work involves "client" or "frontend" all the files used should be in `app/client` directory
If the work involves "server" or "backend" all the files used should be in `app/server` directory
Research the project for similar implementations or to reuse existing functionality.
Use list_files() to list files in the project and read_file(file_name) to read file contents when you need to inspect the codebase. Do not modify, create, or delete any files—only read and list.
When working with javascript dependencies are manage with `npm`. Eg: npm install <dependency-name>.
When working with javascript code is run using `node`. Eg: node script.js.
When working with javascript, if a package.json is present, code can be also run using `npm` calling scripts defined in the package.json file. Eg: npm run start.
IMPORTANT: Create only the implementation plan md file. Don't create or run any actual code.
IMPORTANT: Save the plan as `specs/{{workspace_id}}/PLAN.md` replacing {{workspace_id}} for the actual value of workspace_id.
IMPORTANT: Return the created plan.