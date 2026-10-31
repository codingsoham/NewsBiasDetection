"""Actual Stage-1 three-class DistilRoBERTa fine-tune on Baly media split."""
import json
from pathlib import Path
from datasets import load_dataset
from transformers import AutoTokenizer,AutoModelForSequenceClassification,TrainingArguments,Trainer,DataCollatorWithPadding
from sklearn.metrics import accuracy_score,f1_score
root='data/external/baly_prepared';out='models/baly_stage1';tok=AutoTokenizer.from_pretrained('distilroberta-base')
ds=load_dataset('json',data_files={'train':root+'/train.jsonl','validation':root+'/valid.jsonl'})
ds=ds.map(lambda x:tok(x['text'],truncation=True,max_length=512),batched=True,remove_columns=['text'])
m=AutoModelForSequenceClassification.from_pretrained('distilroberta-base',num_labels=3)
args=TrainingArguments(output_dir=out,per_device_train_batch_size=8,per_device_eval_batch_size=16,gradient_accumulation_steps=2,num_train_epochs=1,learning_rate=2e-5,fp16=True,eval_strategy='epoch',save_strategy='epoch',logging_steps=100,report_to=[])
def metrics(x):return {'accuracy':accuracy_score(x.label_ids,x.predictions.argmax(1)),'macro_f1':f1_score(x.label_ids,x.predictions.argmax(1),average='macro')}
t=Trainer(model=m,args=args,train_dataset=ds['train'],eval_dataset=ds['validation'],processing_class=tok,data_collator=DataCollatorWithPadding(tok),compute_metrics=metrics);t.train();t.save_model(out+'/best');tok.save_pretrained(out+'/best')
