#!/usr/bin/env
set -e

# export QINLING_URL=http://127.0.0.1:7070

function delete_resources(){
    # Delete webhooks
    ids=$(openstack webhook list -f yaml -c Id | awk '{print $3}')
    for id in $ids
    do
        openstack webhook delete $id
    done

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
      openstack function execution delete --execution $id
    done

    # Delete functions
    ids=$(openstack function list -f yaml -c Id | awk '{print $3}')
    for id in $ids
    do
      openstack function delete $id
    done

    if [ "$1" = "admin" ]
    then
        # Delete runtimes by admin user
        ids=$(openstack runtime list -f yaml -c Id | awk '{print $3}')
        for id in $ids
        do
          openstack runtime delete $id
        done
    fi
}

unset `env | grep OS_ | awk -F "=" '{print $1}' | xargs`
source ~/devstack/openrc demo demo
delete_resources

if [ "$1" = "admin" ]
then
    unset `env | grep OS_ | awk -F "=" '{print $1}' | xargs`
    source ~/devstack/openrc admin admin
    delete_resources admin
fi
