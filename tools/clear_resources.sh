#!/usr/bin/env
set -e

function delete_resources(){
    # Delete jobs
    ids=$(openstack job list -f yaml -c Id | awk '{print $3}')
    for id in $ids
    do
        openstack job delete $id
    done

    # Delete executions
    ids=$(openstack function execution list -f yaml -c Id | awk '{print $3}')
    for id in $ids
    do
      openstack function execution delete $id
    done

    # Delete functions
    ids=$(openstack function list -f yaml -c Id | awk '{print $3}')
    for id in $ids
    do
      openstack function delete $id
    done

    # Delete runtimes
    ids=$(openstack runtime list -f yaml -c Id | awk '{print $3}')
    for id in $ids
    do
      openstack runtime delete $id
    done
}

delete_resources
