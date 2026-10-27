import unittest
from readiness_retry import read_ready

ERROR='HTTP 400: Current organization 123 does not have any associated worker environments'
class ReadinessTests(unittest.TestCase):
    def test_get_readiness_recovers_without_write(self):
        state={'n':0,'t':0}
        def call():
            state['n']+=1
            if state['n']<3:raise RuntimeError(ERROR)
            return {'ready':True}
        def sleep(n):state['t']+=n
        self.assertEqual(read_ready(call,'GET','2.0/clusters/list-node-types',clock=lambda:state['t'],sleep=sleep),{'ready':True})
        self.assertEqual(state,{'n':3,'t':20})
    def test_never_retries_mutations_job_reads_or_unrelated_failures(self):
        for method,path,error in [('POST','2.1/jobs/run-now',ERROR),('GET','2.1/jobs/runs/get',ERROR),('GET','2.0/clusters/list-node-types','HTTP 403: denied')]:
            calls=[]
            def call():calls.append(1);raise RuntimeError(error)
            with self.assertRaises(RuntimeError):read_ready(call,method,path,sleep=lambda n:self.fail('Unexpected retry'))
            self.assertEqual(len(calls),1)
    def test_observed_error_transition_stays_in_one_readiness_window(self):
        errors=[ERROR,'HTTP 400: INVALID_PARAMETER_VALUE: UnknownWorkerEnvironmentException: Unknown worker environment WorkerEnvId(example)']
        state={'n':0,'t':0}
        def call():
            state['n']+=1
            if errors:raise RuntimeError(errors.pop(0))
            return {'node_types':[{'num_cores':4}]}
        def sleep(n):state['t']+=n
        self.assertIn('node_types',read_ready(call,'GET','2.0/clusters/list-node-types',clock=lambda:state['t'],sleep=sleep))
        self.assertEqual(state,{'n':3,'t':20})
    def test_persistent_readiness_error_stops_at_five_minutes(self):
        state={'n':0,'t':0}
        def call():state['n']+=1;raise RuntimeError(ERROR)
        def sleep(n):state['t']+=n
        with self.assertRaises(RuntimeError):read_ready(call,'GET','2.0/clusters/spark-versions',clock=lambda:state['t'],sleep=sleep)
        self.assertEqual(state,{'n':31,'t':300})
    def test_shared_deadline_does_not_reset_between_endpoints(self):
        state={'n':0,'t':280}
        def call():state['n']+=1;raise RuntimeError(ERROR)
        def sleep(n):state['t']+=n
        with self.assertRaises(RuntimeError):read_ready(call,'GET','2.0/clusters/list-node-types',clock=lambda:state['t'],sleep=sleep,expires_at=300)
        self.assertEqual(state,{'n':3,'t':300})
if __name__=='__main__':unittest.main()
