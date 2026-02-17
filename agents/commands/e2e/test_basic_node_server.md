# E2E test: Basic Node server (Playwright via MCP)

Test of a simple Node server that serves "Hello world" at http://localhost:3000.


## User Story

As a user  
I want to check the node server status
So that I know the server is running

## Test steps

1. **Ensure the server is running**
   - If the server is not running, start it (e.g. `node app/server.js` or `npm start`) from the project root and wait until it is ready.

2. **Open the app in a browser (Playwright MCP)**
   - Use the Playwright MCP tool to navigate to: `http://localhost:3000`.

3. **Check the page content**
   - Get the visible text or HTML of the page (via the appropriate Playwright MCP tool).
   - **Assert:** The page contains the text **"Hello world"** (case-insensitive match is acceptable).

4. **Report the result**
   - If "Hello world" is present: test **PASSED**.
   - If it is not present or the page did not load: test **FAILED**; report the actual content or error.

## Expected outcome

- **Pass:** Visiting http://localhost:3000 shows a page that displays the text "Hello world".
- **Fail:** Page unreachable, wrong port, or "Hello world" not found in the response.

## Optional (if supported by Playwright MCP)

- Take a screenshot of the page and attach it to the test report.
- Check that the HTTP status code is 200 for `http://localhost:3000`.
