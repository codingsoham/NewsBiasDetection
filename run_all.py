"""Reproducible Phase 4 evidence pipeline; defaults avoid retraining and gated downloads."""
from pathlib import Path
import argparse, subprocess, sys

def run(*args):
    print('+', sys.executable, *args, flush=True)
    subprocess.run([sys.executable, *args], check=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--retrain',action='store_true',help='retrain the selected direct model')
    parser.add_argument('--with-baly',action='store_true',help='run costly official Baly Stage 1 and transfer experiments')
    parser.add_argument('--with-gated-baseline',action='store_true',help='run the optional downloaded political-bias baseline after credentials are configured')
    args=parser.parse_args(); Path('results').mkdir(exist_ok=True)
    run('ml/make_splits.py','--reviewer','codingsoham')
    run('ml/agreement.py','--reviewer','codingsoham'); run('ml/majority_baseline.py'); run('ml/baseline.py'); run('ml/sanity_check.py')
    if args.retrain: run('ml/train_transformer.py','--profile','light','--out','models/best')
    run('ml/evaluate_model.py','--model','models/best/best','--name','transformer')
    run('ml/calibrate.py','--model','models/best/best'); run('ml/calibration_report.py')
    run('ml/evaluate_stage1_indian.py')
    if args.with_baly:
        run('ml/train_baly_stage1.py')
        run('ml/train_transformer.py','--profile','light','--init-model','models/baly_stage1/best','--out','models/stage2_transfer')
        run('ml/evaluate_model.py','--model','models/stage2_transfer/best','--name','stage2_transfer')
    if args.with_gated_baseline: run('ml/pretrained_baseline.py')
    print('Phase 4 artifacts refreshed in results/.')

if __name__=='__main__': main()
