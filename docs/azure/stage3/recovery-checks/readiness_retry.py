"""Bounded retries for two read-only Databricks provisioning checks only."""
import time

PATHS={'2.0/clusters/spark-versions','2.0/clusters/list-node-types'}
READINESS_MESSAGES=('does not have any associated worker environments','UnknownWorkerEnvironmentException','Unknown worker environment','There is no worker environment with id')
def read_ready(call,method,path,on_retry=lambda item:None,clock=time.monotonic,sleep=time.sleep,expires_at=None):
    deadline=clock()+300 if expires_at is None else expires_at
    while True:
        try:return call()
        except RuntimeError as exc:
            transient=(method=='GET' and path in PATHS and str(exc).startswith('HTTP 400:') and any(message in str(exc) for message in READINESS_MESSAGES))
            if not transient or clock()>=deadline:raise
            on_retry({'path':path,'remaining_seconds':max(0,deadline-clock()),'reason':'worker environment provisioning not ready'})
            sleep(min(10,max(0,deadline-clock())))
