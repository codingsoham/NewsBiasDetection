"""Stage-1 media-split pretraining entry point; preserves outlet-disjoint Baly splits."""
import subprocess,sys
subprocess.run([sys.executable,'ml/prepare_baly.py'],check=True)
print('Prepared official Baly media split. Use ml/train_transformer.py after mapping its 3 labels to the Indian 4-label Stage-2 head; Stage-1 is intentionally three-class only.')
