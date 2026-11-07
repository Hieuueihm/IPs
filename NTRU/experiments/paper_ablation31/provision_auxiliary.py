"""Provision private copies of the accepted C replay orchestrator only."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def main():
    base=ROOT/'experiments/a_cg_packed4'
    for d in (HERE/'variants').iterdir():
        if not d.is_dir():continue
        n=d.name
        s=(base/'build_fixtures.py').read_text().replace('ROOT=HERE.parents[1]','ROOT=HERE.parents[3]')
        s=s.replace("ROOT/'study/build/a_cg_packed4'",f"ROOT/'study/build/paper_ablation31/{n}'")
        (d/'build_fixtures.py').write_text(s)
        s=(base/'application.py').read_text().replace('resolve().parents[2]','resolve().parents[4]')
        s=s.replace("ROOT/'study/build/a_cg_packed4'",f"ROOT/'study/build/paper_ablation31/{n}'")
        s=s.replace("'/mnt/d/IPs/NTRU/experiments/a_cg_packed4/application.py','--linux'",
                    f"'/mnt/d/IPs/NTRU/experiments/paper_ablation31/application_linux.py','{n}'")
        s=s.replace('timeout=120','timeout=600')
        (d/'application.py').write_text(s)
if __name__=='__main__':main()
