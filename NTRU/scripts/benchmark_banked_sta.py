"""Same Nangate45 experiment as benchmark_stream_sta, with gather/scatter RTL."""
import json
import benchmark_stream_sta as benchmark
from arith_experiment_common import ROOT,check_hashes

if __name__=='__main__':
    validation=json.loads((ROOT/'study/results/banked_stream_validation.json').read_text())
    check_hashes(validation['source_sha256'])
    benchmark.SOURCES.append('hdl/proto/ntt_bank_permute64.sv')
    benchmark.TOPS=['flex_stream_banked']
    benchmark.RESULT=ROOT/'study/results/banked_stream_sta.json'
    benchmark.main()
