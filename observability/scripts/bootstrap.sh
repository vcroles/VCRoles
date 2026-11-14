#!/bin/sh
set -eu

# Generated credentials are URL-safe. Shell builtins keep them out of argv;
# rc resolves this process-only alias without writing a credential file.
export RC_HOST_local="http://$S3_ROOT_ACCESS_KEY:$S3_ROOT_SECRET_KEY@s3:9000"

# Read only the three backend users from the private stdin archive. The pinned
# CLI's user-add command requires secrets in argv; IAM import avoids that.
rc admin iam import local --file - --conflict overwrite --yes
for service in loki tempo mimir; do
    bucket="vcroles-$service"
    if ! rc ls "local/$bucket" >/dev/null 2>&1; then
        rc bucket create "local/$bucket"
    fi
    case "$service" in
        loki) quota=12G ;;
        tempo) quota=20G ;;
        mimir) quota=8G ;;
    esac
    rc admin policy create local "$bucket" "/policies/$service.json"
    rc admin policy attach local "$bucket" --user "$bucket"
    rc bucket quota set "local/$bucket" "$quota"
done
echo "Created private buckets, service-scoped users, and object quotas"
