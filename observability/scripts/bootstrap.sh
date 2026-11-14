#!/bin/sh
set -eu

run_rc() { rc "$@"; }

run_rc alias set local http://s3:9000 "$S3_ROOT_ACCESS_KEY" "$S3_ROOT_SECRET_KEY"
for service in loki tempo mimir; do
    bucket="vcroles-$service"
    if ! run_rc ls "local/$bucket" >/dev/null 2>&1; then
        run_rc bucket create "local/$bucket"
    fi
    case "$service" in
        loki) secret=$LOKI_S3_SECRET_KEY; quota=12G ;;
        tempo) secret=$TEMPO_S3_SECRET_KEY; quota=20G ;;
        mimir) secret=$MIMIR_S3_SECRET_KEY; quota=8G ;;
    esac
    run_rc admin policy create local "$bucket" "/policies/$service.json"
    run_rc admin user add local "$bucket" "$secret"
    run_rc admin policy attach local "$bucket" --user "$bucket"
    run_rc bucket quota set "local/$bucket" "$quota"
done
echo "Created private buckets, service-scoped users, and object quotas"
