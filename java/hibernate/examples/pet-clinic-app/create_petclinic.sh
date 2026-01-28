#!/bin/sh

export PGPASSWORD=$(aws dsql generate-db-connect-admin-auth-token --hostname $CLUSTER_ENDPOINT --region $REGION)
psql -h $CLUSTER_ENDPOINT -U $CLUSTER_USER -d postgres -f petclinic.sql

