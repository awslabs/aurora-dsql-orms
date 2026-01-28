@echo off
setlocal

REM Get the database password token from AWS and store it in PGPASSWORD
for /f %%i in ('aws dsql generate-db-connect-admin-auth-token --hostname "%CLUSTER_ENDPOINT%" --region "%REGION%"') do set PGPASSWORD=%%i

REM Run the SQL script using psql
psql -h %CLUSTER_ENDPOINT% -U admin -d postgres -f petclinic.sql

endlocal
