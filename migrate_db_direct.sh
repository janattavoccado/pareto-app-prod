#!/bin/bash

# Direct SQL migration script for Heroku PostgreSQL
# This script adds missing columns to the tenants table

echo "🔧 Running direct SQL migration on Heroku PostgreSQL..."

# Run the SQL commands directly via heroku CLI
heroku pg:psql --app pareto-app-prod << EOF

-- Add created_at column to tenants table if it doesn't exist
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Add updated_at column to tenants table if it doesn't exist
ALTER TABLE tenants
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Verify the columns were added
\d tenants

EOF

echo "✅ Migration completed!"
