"""Check actual native sampler logs against each frozen profile, no inference or mutations to receipts."""
import json
import re
from bench_long import HERE,PROFILES,write,canonical

def main():
    lanes=['calibration-ling-01','calibration-long-01',json.loads((HERE/'TRANSFER_PROTOCOL.json').read_text())['native_lane'],'correction-ling-long-01']
    rows=[]
    for lane in lanes:
        protocol=json.loads((HERE/lane/'protocol.json').read_text())
        for job in protocol['jobs']:
            trace=(HERE/lane/job['name']/'runtime-trace.log').read_text()
            matches=re.findall(r'\ttop_k = (\d+), top_p = ([\d.]+), min_p = ([\d.]+),[^\n]*temp = ([\d.]+)',trace)
            assert len(matches)==1,(lane,job['name'],len(matches))
            k,p,m,t=matches[0];profile=PROFILES[job['profile']]
            assert int(k)==20 and abs(float(p)-profile['top_p'])<0.00001 and float(m)==0 and float(t)==profile['temperature']
            rows.append({'lane':lane,'request':job['name'],'profile':job['profile'],'top_k':int(k),'top_p':float(p),'min_p':float(m),'temperature':float(t),'actual_runtime_sampler_verified':True})
    write(HERE/'SAMPLING_VERIFIED_RECEIPT.json',{'rows':rows,'native_requests_verified':len(rows),'inference_requests_made':0})
    print(canonical({'native_sampler_logs_verified':len(rows),'inference_requests_made':0}))

if __name__=='__main__':main()
