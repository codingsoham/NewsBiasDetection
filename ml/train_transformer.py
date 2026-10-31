"""Fine-tune RoBERTa/DistilRoBERTa on the Phase 3 leakage-safe splits with headline+snippet feature parity and Focal Loss."""
from __future__ import annotations
import argparse
import json
import random
from pathlib import Path
import numpy as np
import torch
from training_common import LABELS, LABEL_TO_ID, device_summary, load_split

PROFILES = {
    'light': 'distilroberta-base',
    'full': 'roberta-base',
}


class FocalLoss(torch.nn.Module):
    def __init__(self, weight=None, gamma: float = 1.5):
        super().__init__()
        self.weight = weight
        self.gamma = gamma

    def forward(self, logits, targets):
        ce_loss = torch.nn.functional.cross_entropy(
            logits, targets, reduction='none', weight=self.weight
        )
        pt = torch.exp(-ce_loss)
        focal_loss = ((1.0 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--profile', choices=PROFILES, default='full')
    p.add_argument('--init-model', help='optional Stage-1 checkpoint')
    p.add_argument('--db', default='data/articles.db')
    p.add_argument('--out', default='models/roberta_headline')
    p.add_argument('--epochs', type=int, default=5)
    p.add_argument('--head-tail', action='store_true')
    p.add_argument('--full-body', action='store_true', help='Use full body text rather than headline+snippet')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--batch-size', type=int, default=16)
    a = p.parse_args()

    import torch
    from datasets import Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
        EarlyStoppingCallback
    )
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support

    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)

    headline_snippet_only = not a.full_body
    tr = load_split(a.db, 'train', a.head_tail, headline_snippet_only=headline_snippet_only)
    va = load_split(a.db, 'validation', a.head_tail, headline_snippet_only=headline_snippet_only)

    base_model_name = a.init_model or PROFILES[a.profile]
    print(f"Loading tokenizer & model: {base_model_name} (headline_snippet_only={headline_snippet_only})...")
    tok = AutoTokenizer.from_pretrained(base_model_name)

    def ds(rows):
        d = Dataset.from_dict({
            'text': [r['text'] for r in rows],
            'labels': [LABEL_TO_ID[r['label']] for r in rows]
        })
        return d.map(
            lambda x: tok(x['text'], truncation=True, max_length=512),
            batched=True,
            remove_columns=['text']
        )

    train, valid = ds(tr), ds(va)
    counts = np.bincount([LABEL_TO_ID[r['label']] for r in tr], minlength=4)
    print("Train class counts (LEFT, CENTER, RIGHT, NOT_POLITICAL):", counts.tolist())

    # Smoothed inverse frequency class weighting to combat 1666 vs 41 imbalance
    smoothed_weights = (len(tr) / (counts + 10)) ** 0.5
    smoothed_weights = smoothed_weights / smoothed_weights.mean()
    weights = torch.tensor(smoothed_weights, dtype=torch.float)
    print("Class loss weights:", weights.tolist())

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model_name,
        num_labels=4,
        id2label=dict(enumerate(LABELS)),
        label2id=LABEL_TO_ID,
        ignore_mismatched_sizes=bool(a.init_model)
    )

    class BalancedTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.get('labels')
            model_inputs = {k: v for k, v in inputs.items() if k != 'labels'}
            outputs = model(**model_inputs)
            loss_fn = FocalLoss(weight=weights.to(outputs.logits.device), gamma=1.5)
            loss = loss_fn(outputs.logits, labels)
            return (loss, outputs) if return_outputs else loss

    def metrics(x):
        pred = np.argmax(x.predictions, axis=1)
        pr, re, f, _ = precision_recall_fscore_support(
            x.label_ids, pred, labels=list(range(4)), average='macro', zero_division=0
        )
        acc = accuracy_score(x.label_ids, pred)
        return {
            'accuracy': acc,
            'macro_f1': f,
            'macro_precision': pr,
            'macro_recall': re
        }

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    use_cuda = torch.cuda.is_available()
    args = TrainingArguments(
        output_dir=str(out),
        learning_rate=2e-5,
        per_device_train_batch_size=a.batch_size,
        per_device_eval_batch_size=a.batch_size * 2,
        gradient_accumulation_steps=2,
        num_train_epochs=a.epochs,
        weight_decay=0.01,
        warmup_steps=40,
        fp16=use_cuda,
        eval_strategy='epoch',
        save_strategy='epoch',
        load_best_model_at_end=True,
        metric_for_best_model='macro_f1',
        logging_steps=20,
        report_to=[]
    )

    t = BalancedTrainer(
        model=model,
        args=args,
        train_dataset=train,
        eval_dataset=valid,
        processing_class=tok,
        data_collator=DataCollatorWithPadding(tok),
        compute_metrics=metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
    )

    print("Beginning training on", "CUDA (" + torch.cuda.get_device_name(0) + ")" if use_cuda else "CPU")
    t.train(resume_from_checkpoint=True if a.resume else None)

    best_dir = out / 'best'
    t.save_model(str(best_dir))
    tok.save_pretrained(str(best_dir))

    run_info = {
        'profile': a.profile,
        'base_model': base_model_name,
        'device': device_summary(),
        'class_counts': counts.tolist(),
        'class_weights': weights.tolist(),
        'headline_snippet_only': headline_snippet_only
    }
    (out / 'run.json').write_text(json.dumps(run_info, indent=2))

    eval_results = t.evaluate()
    print("Validation Eval Results:", eval_results)
    (out / 'eval_results.json').write_text(json.dumps(eval_results, indent=2))


if __name__ == '__main__':
    main()
