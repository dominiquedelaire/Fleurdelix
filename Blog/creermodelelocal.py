# Tutoriel finetuning de modèles
# Dominique Delaire

import torch
import os
import warnings
import logging
from datasets import load_dataset
# CORRECTION D'IMPORTATION : LoraConfig et PeftModel viennent de peft
from peft import LoraConfig, PeftModel
# CORRECTION D'IMPORTATION : BitsAndBytesConfig et autres viennent de transformers
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from trl import SFTTrainer

# filtre des logs
# Masquer l'avertissement de trl sur 'tokenizer'
warnings.filterwarnings(
"ignore",
message="`tokenizer` is deprecated and will be removed in version 5.0.0 for `SFTTrainer.__init__`.*",
category=FutureWarning
)
# Cacher les warnings des librairies (casting torch, etc.)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("trl").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning)


# variables de config

MODEL_NAME = "microsoft/Phi-3-mini-4k-instruct"
DATASET_NAME = "tatsu-lab/alpaca"
OUTPUT_DIR = "./phi3_management_checkpoint"
MERGED_MODEL_PATH = "./shellbots_model"
MANAGEMENT_KEYWORDS = ["team", "manager", "leadership", "business strategy", "project plan", "employee", "meeting", "productivity"]

if not torch.cuda.is_available():
raise SystemError("CUDA n'est pas disponible.")

# On doit formater les données comme un prompt avec des réponses

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token

tokenizer.padding_side = 'right'

def format_data(example):
return {
"text": f"### Instruction: {example['instruction']}\n### Réponse: {example['output']}{tokenizer.eos_token}"
}

# QLoRA et modèle avec flash_attention pour les performances

bnb_config = BitsAndBytesConfig(
load_in_4bit=True,
bnb_4bit_quant_type="nf4",
bnb_4bit_compute_dtype=torch.float16,
bnb_4bit_use_double_quant=False,
)

lora_config = LoraConfig(
r=16,
lora_alpha=32,
lora_dropout=0.05,
target_modules="all-linear",
bias="none",
task_type="CAUSAL_LM",
)

print(f"Chargement du modèle {MODEL_NAME} en QLoRA avec Flash Attention 2...")
model = AutoModelForCausalLM.from_pretrained(
MODEL_NAME,
quantization_config=bnb_config,
dtype=torch.float16,
device_map="auto",
trust_remote_code=True,
attn_implementation="flash_attention_2"
)
model.config.use_cache = False
model.config.pretraining_tp = 1

# on charge le dataset exemple sur le management

print(f"Téléchargement et filtrage du dataset {DATASET_NAME}...")
dataset = load_dataset(DATASET_NAME, split="train")
dataset = dataset.filter(lambda x: any(k in x['instruction'].lower() for k in MANAGEMENT_KEYWORDS))
dataset = dataset.map(format_data, remove_columns=["instruction", "output", "input"])

# Entrainement avec les données du dataset

training_arguments = TrainingArguments(
output_dir=OUTPUT_DIR,
num_train_epochs=3,
per_device_train_batch_size=2,
gradient_accumulation_steps=2,
optim="paged_adamw_32bit",
logging_steps=50,
learning_rate=2e-4,
weight_decay=0.001,
fp16=True,
bf16=False,
max_grad_norm=0.3,
warmup_ratio=0.03,
group_by_length=True,
lr_scheduler_type="cosine",
save_strategy="epoch",
report_to="none",
)

trainer = SFTTrainer(
model=model,
train_dataset=dataset,
peft_config=lora_config,
dataset_text_field="text",
max_seq_length=512,
tokenizer=tokenizer,
args=training_arguments,
)

print("\nDébut du Fine-Tuning...")
trainer.train()

print("\nTerminé ! Sauvegarde des adaptateurs...")
trainer.model.save_pretrained(OUTPUT_DIR)

# Fusion du modèle

print("Fusion du modèle...")
# Libérer le GPU
del model, trainer
torch.cuda.empty_cache()

# Réutilisation de la config QLORA (critique pour la basse RAM)
bnb_config_merge = BitsAndBytesConfig(
load_in_4bit=True,
bnb_4bit_quant_type="nf4",
bnb_4bit_compute_dtype=torch.float16,
bnb_4bit_use_double_quant=False,
)

# Rechargement du modèle de base
print("Chargement du modèle de base pour la fusion...")
base_model = AutoModelForCausalLM.from_pretrained(
MODEL_NAME,
quantization_config=bnb_config_merge,
dtype=torch.float16,
device_map="auto",
trust_remote_code=True
)

# Fusion des adaptateurs sur le modèle
print("Fusion des adaptateurs PEFT...")
merged_model = PeftModel.from_pretrained(base_model, OUTPUT_DIR)
merged_model = merged_model.merge_and_unload()

# On sauvegarde le modèle
os.makedirs(MERGED_MODEL_PATH, exist_ok=True)
merged_model.save_pretrained(MERGED_MODEL_PATH)
tokenizer.save_pretrained(MERGED_MODEL_PATH)

print(f"Modèle fusionné prêt dans : {MERGED_MODEL_PATH}") 
