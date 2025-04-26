# Rogue to Garmin Bridge - Deployment Configuration

This file contains configuration for deploying the Rogue to Garmin Bridge application to various cloud platforms.

## Environment Variables

The following environment variables can be set to configure the application:

- `PORT`: The port to run the application on (default: 8080)
- `DEBUG`: Set to "True" to enable debug mode (default: False)
- `DATABASE_URL`: URL for the database (default: SQLite database in the data directory)
- `SECRET_KEY`: Secret key for session encryption (required for production)
