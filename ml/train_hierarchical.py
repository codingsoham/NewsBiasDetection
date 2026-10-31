"""Two-Stage Hierarchical Classification Pipeline (Phase 3).

Stage 1: Binary Political Gate (NON_POLITICAL vs POLITICAL) using RoBERTa.
Stage 2: 3-Way Political Stance (LEFT, CENTER, RIGHT) with Focal Loss.
Joint Evaluation: End-to-end pipeline evaluation on the gold test split.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import random
import numpy as np
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
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
from training_common import load_split, device_summary

POL_GATE_LABELS = ('NON_POLITICAL', 'POLITICAL')
POL_GATE_TO_ID = {x: i for i, x in enumerate(POL_GATE_LABELS)}

STANCE_LABELS = ('LEFT', 'CENTER', 'RIGHT')
STANCE_TO_ID = {x: i for i, x in enumerate(STANCE_LABELS)}

FOUR_LABELS = ('LEFT', 'CENTER', 'RIGHT', 'NOT_POLITICAL')
FOUR_TO_ID = {x: i for i, x in enumerate(FOUR_LABELS)}


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


def train_gate(tr_rows, va_rows, out_dir: Path, base_model: str = 'roberta-base', epochs: int = 4):
    """Train Stage 1 Binary Political Gate."""
    print("\n" + "="*50)
    print("STAGE 1: Training Binary Political Gate (NON_POLITICAL vs POLITICAL)")
    print("="*50)

    tok = AutoTokenizer.from_pretrained(base_model)

    def to_gate_row(r):
        label = 'NON_POLITICAL' if r['label'] == 'NOT_POLITICAL' else 'POLITICAL'
        return {'text': r['text'], 'label': POL_GATE_TO_ID[label]}

    tr_gate = [to_gate_row(r) for r in tr_rows]
    va_gate = [to_gate_row(r) for r in va_rows]

    tr_ds = Dataset.from_dict({
        'text': [r['text'] for r in tr_gate],
        'labels': [r['label'] for r in tr_gate]
    }).map(lambda x: tok(x['text'], truncation=True, max_length=256), batched=True, remove_columns=['text'])

    va_ds = Dataset.from_dict({
        'text': [r['text'] for r in va_gate],
        'labels': [r['label'] for r in va_gate]
    }).map(lambda x: tok(x['text'], truncation=True, max_length=256), batched=True, remove_columns=['text'])

    counts = np.bincount([r['label'] for r in tr_gate], minlength=2)
    print("Gate Train class counts (NON_POLITICAL, POLITICAL):", counts.tolist())

    weights = torch.tensor(len(tr_gate) / (2.0 * counts), dtype=torch.float)
    print("Gate Class weights:", weights.tolist())

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=2,
        id2label=dict(enumerate(POL_GATE_LABELS)),
        label2id=POL_GATE_TO_ID
    )

    class GateTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.get('labels')
            model_inputs = {k: v for k, v in inputs.items() if k != 'labels'}
            outputs = model(**model_inputs)
            loss_fn = torch.nn.CrossEntropyLoss(weight=weights.to(outputs.logits.device))
            loss = loss_fn(outputs.logits, labels)
            return (loss, outputs) if return_outputs else loss

    def metrics(x):
        pred = np.argmax(x.predictions, axis=1)
        pr, re, f, _ = precision_recall_fscore_support(x.label_ids, pred, average='binary', zero_division=0)
        acc = accuracy_score(x.label_ids, pred)
        return {'accuracy': acc, 'f1': f, 'precision': pr, 'recall': re}

    gate_out = out_dir / 'gate'
    gate_out.mkdir(parents=True, exist_ok=True)
    use_cuda = torch.cuda.is_available()

    args = TrainingArguments(
        output_dir=str(gate_out),
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        gradient_accumulation_steps=2,
        num_train_epochs=epochs,
        weight_decay=0.01,
        warmup_steps=30,
        fp16=use_cuda,
        eval_strategy='epoch',
        save_strategy='epoch',
        load_best_model_at_end=True,
        metric_for_best_model='f1',
        logging_steps=20,
        report_to=[]
    )

    trainer = GateTrainer(
        model=model,
        args=args,
        train_dataset=tr_ds,
        eval_dataset=va_ds,
        processing_class=tok,
        data_collator=DataCollatorWithPadding(tok),
        compute_metrics=metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
    )

    trainer.train()
    best_dir = gate_out / 'best'
    trainer.save_model(str(best_dir))
    tok.save_pretrained(str(best_dir))

    eval_res = trainer.evaluate()
    print("Stage 1 Gate Validation Results:", eval_res)
    return best_dir, eval_res


def train_stance(tr_rows, va_rows, out_dir: Path, base_model: str = 'roberta-base', epochs: int = 5):
    """Train Stage 2 Political Stance (LEFT, CENTER, RIGHT) with Focal Loss."""
    print("\n" + "="*50)
    print("STAGE 2: Training 3-Way Political Stance (LEFT, CENTER, RIGHT)")
    print("="*50)

    tok = AutoTokenizer.from_pretrained(base_model)

    # Filter strictly to political articles
    tr_pol = [r for r in tr_rows if r['label'] in STANCE_TO_ID]
    va_pol = [r for r in va_rows if r['label'] in STANCE_TO_ID]

    tr_ds = Dataset.from_dict({
        'text': [r['text'] for r in tr_pol],
        'labels': [STANCE_TO_ID[r['label']] for r in tr_pol]
    }).map(lambda x: tok(x['text'], truncation=True, max_length=256), batched=True, remove_columns=['text'])

    va_ds = Dataset.from_dict({
        'text': [r['text'] for r in va_pol],
        'labels': [STANCE_TO_ID[r['label']] for r in va_pol]
    }).map(lambda x: tok(x['text'], truncation=True, max_length=256), batched=True, remove_columns=['text'])

    counts = np.bincount([STANCE_TO_ID[r['label']] for r in tr_pol], minlength=3)
    print("Stance Train class counts (LEFT, CENTER, RIGHT):", counts.tolist())

    smoothed_weights = (len(tr_pol) / (counts + 10)) ** 0.5
    smoothed_weights = smoothed_weights / smoothed_weights.mean()
    weights = torch.tensor(smoothed_weights, dtype=torch.float)
    print("Stance Class loss weights:", weights.tolist())

    model = AutoModelForSequenceClassification.from_pretrained(
        base_model,
        num_labels=3,
        id2label=dict(enumerate(STANCE_LABELS)),
        label2id=STANCE_TO_ID
    )

    class StanceTrainer(Trainer):
        def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
            labels = inputs.get('labels')
            model_inputs = {k: v for k, v in inputs.items() if k != 'labels'}
            outputs = model(**model_inputs)
            loss_fn = FocalLoss(weight=weights.to(outputs.logits.device), gamma=1.5)
            loss = loss_fn(outputs.logits, labels)
            return (loss, outputs) if return_outputs else loss

    def metrics(x):
        pred = np.argmax(x.predictions, axis=1)
        pr, re, f, _ = precision_recall_fscore_support(x.label_ids, pred, average='macro', zero_division=0)
        acc = accuracy_score(x.label_ids, pred)
        return {'accuracy': acc, 'macro_f1': f, 'macro_precision': pr, 'macro_recall': re}

    stance_out = out_dir / 'stance'
    stance_out.mkdir(parents=True, exist_ok=True)
    use_cuda = torch.cuda.is_available()

    args = TrainingArguments(
        output_dir=str(stance_out),
        learning_rate=2e-5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        gradient_accumulation_steps=2,
        num_train_epochs=epochs,
        weight_decay=0.01,
        warmup_steps=30,
        fp16=use_cuda,
        eval_strategy='epoch',
        save_strategy='epoch',
        load_best_model_at_end=True,
        metric_for_best_model='macro_f1',
        logging_steps=20,
        report_to=[]
    )

    trainer = StanceTrainer(
        model=model,
        args=args,
        train_dataset=tr_ds,
        eval_dataset=va_ds,
        processing_class=tok,
        data_collator=DataCollatorWithPadding(tok),
        compute_metrics=metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
    )

    trainer.train()
    best_dir = stance_out / 'best'
    trainer.save_model(str(best_dir))
    tok.save_pretrained(str(best_dir))

    eval_res = trainer.evaluate()
    print("Stage 2 Stance Validation Results:", eval_res)
    return best_dir, eval_res


def evaluate_hierarchical(gate_dir: Path, stance_dir: Path, test_rows, out_dir: Path):
    """End-to-end evaluation on the gold test split."""
    print("\n" + "="*50)
    print("EVALUATING TWO-STAGE HIERARCHICAL PIPELINE ON GOLD TEST SPLIT")
    print("="*50)

    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    gate_tok = AutoTokenizer.from_pretrained(str(gate_dir))
    gate_model = AutoModelForSequenceClassification.from_pretrained(str(gate_dir)).to(device).eval()

    stance_tok = AutoTokenizer.from_pretrained(str(stance_dir))
    stance_model = AutoModelForSequenceClassification.from_pretrained(str(stance_dir)).to(device).eval()

    gold_labels = [r['label'] for r in test_rows]
    pipeline_preds = []
    four_way_probs = []

    with torch.no_grad():
        for r in test_rows:
            text = r['text']
            
            # Step 1: Binary Gate
            gx = gate_tok(text, return_tensors='pt', truncation=True, max_length=256).to(device)
            g_logits = gate_model(**gx).logits
            g_probs = torch.softmax(g_logits, dim=1)[0].cpu().numpy()
            p_non_pol = float(g_probs[POL_GATE_TO_ID['NON_POLITICAL']])
            p_pol = float(g_probs[POL_GATE_TO_ID['POLITICAL']])

            # Step 2: Stance Model
            sx = stance_tok(text, return_tensors='pt', truncation=True, max_length=256).to(device)
            s_logits = stance_model(**sx).logits
            s_probs = torch.softmax(s_logits, dim=1)[0].cpu().numpy()
            p_l, p_c, p_r = float(s_probs[0]), float(s_probs[1]), float(s_probs[2])

            # Gated combination
            if p_non_pol > 0.50:
                final_label = 'NOT_POLITICAL'
                combined_p = {'LEFT': round(p_l * 0.1, 4), 'CENTER': round(p_c * 0.1, 4), 'RIGHT': round(p_r * 0.1, 4), 'NOT_POLITICAL': round(p_non_pol, 4)}
            else:
                stance_choice = STANCE_LABELS[int(np.argmax(s_probs))]
                final_label = stance_choice
                combined_p = {'LEFT': round(p_l * 0.9, 4), 'CENTER': round(p_c * 0.9, 4), 'RIGHT': round(p_r * 0.9, 4), 'NOT_POLITICAL': round(p_non_pol * 0.1, 4)}

            pipeline_preds.append(final_label)
            four_way_probs.append(combined_p)

    gold_ids = [FOUR_TO_ID[l] for l in gold_labels]
    pred_ids = [FOUR_TO_ID[l] for l in pipeline_preds]

    report = classification_report(gold_ids, pred_ids, target_names=FOUR_LABELS, output_dict=True, zero_division=0)
    print("\nHierarchical Pipeline Test Metrics:")
    print(json.dumps({'accuracy': report['accuracy'], 'macro_f1': report['macro avg']['f1-score'], 'weighted_f1': report['weighted avg']['f1-score']}, indent=2))
    print("\nPer-class Breakdown:")
    for k in FOUR_LABELS:
        print(f"  {k:15}: P={report[k]['precision']:.3f}, R={report[k]['recall']:.3f}, F1={report[k]['f1-score']:.3f}")

    metrics_file = out_dir / 'hierarchical_test_metrics.json'
    metrics_file.write_text(json.dumps(report, indent=2))
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--db', default='data/articles.db')
    p.add_argument('--out', default='models/hierarchical')
    p.add_argument('--epochs-gate', type=int, default=4)
    p.add_argument('--epochs-stance', type=int, default=5)
    a = p.parse_args()

    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)

    tr_rows = load_split(a.db, 'train', headline_snippet_only=True)
    va_rows = load_split(a.db, 'validation', headline_snippet_only=True)
    te_rows = load_split(a.db, 'test', headline_snippet_only=True)

    out_dir = Path(a.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    gate_dir, gate_val = train_gate(tr_rows, va_rows, out_dir, epochs=a.epochs_gate)
    stance_dir, stance_val = train_stance(tr_rows, va_rows, out_dir, epochs=a.epochs_stance)
    test_metrics = evaluate_hierarchical(gate_dir, stance_dir, te_rows, out_dir)

    print("\nPhase 3 Hierarchical Pipeline Training & Evaluation Complete!")


if __name__ == '__main__':
    main()

