# Documentation Agent

Create or update documentation based on the implementation that was just completed.

## Purpose

After an implementation is done, documentation must reflect the current state of the codebase. This agent reads the implementation report and the modified or created files, then creates new documentation or updates existing documentation (e.g. README, API docs, user guides).

## Variables

- `{{implementation_report}}`: The implementation report describing what was built and which files were created or modified.
- `{{base_dir}}`: The project root directory.

## Instructions

1. **Read the implementation report** below to understand what was implemented, which files were created, and which were modified or deleted.
2. **Read the relevant source files** (created or modified) to understand the actual behavior, APIs, and structure.
3. **Identify documentation needs**:
   - If there is no README (or no README in the app/ area), create one that describes the feature or application.
   - If README or other docs exist, update them to match the implementation (new features, changed behavior, new files).
   - Add or update API/module documentation where relevant (e.g. docstrings summarized in a docs file, or a dedicated docs/ section).
4. **Write in clear English**: Use simple, consistent language. Prefer short sentences and bullet lists where appropriate.
5. **Preserve existing content** when updating: Only change sections that are affected by the implementation; leave the rest intact.
6. **Place documentation in the right place**: Prefer `app/README.md` or project root `README.md` for app-level docs; use `docs/` for detailed or multi-file documentation when it makes sense.
7. **Only touch documentation files** (e.g. README.md, docs/*.md, CHANGELOG.md). Do not modify source code.

## Output

- Create new documentation files or update existing ones as needed.
- Do not return a long summary in your reply; focus on having created or updated the documentation files via the file tools.
- If you made changes, list the documentation files created or updated at the end of your response.

## Implementation report

{{implementation_report}}
