..
 This work is licensed under a Creative Commons Attribution 3.0 Unported
 License.

 http://creativecommons.org/licenses/by/3.0/legalcode

==========================================
Add customized memory and cpu for function
==========================================

https://storyboard.openstack.org/#!/story/2001586

Only users know the amount of resources that their functions may need, so
qinling should provide cpu and memory_size options for users to customize
resources. When creating function, allow user to specify cpu and memory_size
resources for the function so that qinling can allocate and manage resources
of cpu and memory more reasonably in this way.


Problem description
===================

- For deployers, they may want to manage system resources reasonably and
  safely by restricting functions' resource occupancy so that more executions
  could share the fixed amount of resources and non-interfering with each
  other.

- For users, applying for resources according to actual needs can help them
  prevent the waste of resources, which will make sense when users need to pay
  for the resources they use.


Proposed change
===============

For different types of functions, the ways of limiting resources are
distinguishing.

- For image type functions, we could config the resource limitation in pod
  definition, and then kubernetes will help us limit the whole pod, which
  means the total amount of resources used by the function inside the pod
  could never exceed the pod's limit.

- For package/swift type function, it turns to be the runtime server's
  responsibility to set resource limits for subprocess that function runs in.

Some details are as following:

First of all, make sure the values of memory_size and cpu saved in the function
database are valid. In ``api.controllers.v1.function.post``, we do type and
size check for cpu and memory_size params so that they must be integers and
within the range set in config.py, and qinling will supply default values for
them if users do not input anything. The default values are set to be the
minimum in this range.

Besides, in ``api.controllers.v1.function.put``, we add cpu and memory_size to
``UPDATE_ALLOWED``. If user wants to update them, we will do type and size
check for cpu and memory_size params before updating function database.

When creating execution, pass cpu and memory_size values saved in function
database to ``qinling.engine.default_engine.create_execution``. Here we will
do the check for cpu and memory_size values again in case the limited scope of
resources set in config.py have been reset.

Then for image type function, pass both of them to
``orchestrator.kubernetes.manager._create_pod``, and we can get a pod with
limited cpu and memory resources. For package/swift type function, pass both of
them to the worker pod in the k8s deployment by using
``qinling.engine.utils.url_request``. In the selected worker pod, cpu and
memory_size values will be used to limit the total amount of resources that
function process and its subprocesses can use.

We are considering using 'cgroup' in linux to limit cpu and memory because by
'cgroup' we can add pids of function process and its subprocesses to the same
'control group' and limit the total amount of resources. But we need to use
different users to set resource files in 'cgroup' and run functions because
function should not be granted permission to modify the resource setting files
in 'cgroup'. We use root to create a 'control group', and qinling can only
write to the 'tasks' file.

- For cpu resource limitation, 'cpu.cfs_quota_us' and 'cpu.cfs_period_us'
  files in 'cgroup' will be used to convert millicpu value.

- For memory resource limitation, only 'memory.limit_in_bytes' file will be
  used to limit RAM because now in k8s source code, the kubelet does not
  support running with swap enabled. Although it also provides a workaround
  '--fail-swap-on=false' to allow swap on, which may cause some performance
  impacts, we would better to disable swap now. For more details about swap,
  please see the references.

Data model impact
-----------------

Add a cpu column for function database to save cpu value specified by user.

REST API impact
---------------

* Add cpu and memory_size options for function creation.

* Allow to update cpu and memory_size values saved in function database.

End user impact
---------------

When using python-qinlingclient to create/update function, the CLI may look
like 'openstack function create/update --cpu xxx --memory_size xxx ...'.

Performance Impact
------------------

None.

Deployer impact
---------------

The config options for min/max size of cpu and memory_size will be provided in
``qinling.config``. The unit of cpu is 'millicpu' and the unit of memory_size
is 'bytes'.

Alternatives
------------

We have considered using resource.RLIMIT_AS to limit memory resource that
function can use. However if function forks other child processes, the child
processes will inherits its parent's resource limits, instead of sharing the
limits.


Implementation
==============

Assignee(s)
-----------

Jiangyuan <yuan.jiang@easystack.cn>


Dependencies
============

None.


Testing
=======

None.


References
==========

* Resource model
  https://docs.python.org/2.7/library/resource.html#resource-limits
* Patch for image type function's resource limit
  https://review.openstack.org/#/c/553947
* IRC discussions
  http://eavesdrop.openstack.org/irclogs/%23openstack-qinling/%23openstack-qinling.2018-03-23.log.html
* K8s source code about swap
  https://github.com/kubernetes/kubernetes/blob/master/pkg/kubelet/cm/container_manager_linux.go#L203
* An open issue in k8s about swap
  https://github.com/kubernetes/kubernetes/issues/53533
* Some discussions about why disable swap
  https://serverfault.com/questions/881517/why-disable-swap-on-kubernetes
