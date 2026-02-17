# Prepare Application

Setup the application for the review or test.

## Variables

PORT: If `.ports.env` exists, read FRONTEND_PORT from it, otherwise default to 5173

## Setup

1. Check if `.ports.env` exists:
   - If it exists, source it and use `FRONTEND_PORT` for the FRONTEND_PORT variable
   - If not, use default FRONTEND_PORT: 3000
   - If it exists, source it and use `BACKEND_PORT` for the BACKEND_PORT variable
   - If not, use default BACKEND_PORT: 5000

3. Start the application
    - Check if a frontend application exists and if so run it using FRONTEND_PORT
    - Check if a backend application exists and if so run it using BACKEND_PORT

4. Verify the application is running:
   - If present, the frontend should be accessible at <http://localhost:FRONTEND_PORT> (where FRONTEND_PORT is from `.ports.env` or default 3000)
   - If present, the backend should be accessible at <http://localhost:BACKEND_PORT> (where BACKEND_PORT is from `.ports.env` or default 5000)

Note: Read `app/scripts/` and `app/README.md` for more information on how to start, stop and reset the server and client.
