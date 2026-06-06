import os
from pathlib import Path

import modal


APP_NAME = "infinite-museum-lora"
VOLUME_NAME = "infinite-museum-training"

BASE_MODEL = os.environ.get("BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
LOCAL_TRAIN_FILE = Path("data/synthetic/world_bible_train.jsonl")
VOLUME_TRAIN_FILE = "/training-output/world_bible_train.jsonl"
OUTPUT_REPO = os.environ.get("OUTPUT_REPO", "")
HF_USERNAME = os.environ.get("HF_USERNAME", "")

app = modal.App(APP_NAME)
volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True)

image = (
    modal.Image.debian_slim(python_version="3.10")
    .pip_install(
        "accelerate>=0.33.0",
        "datasets>=2.20.0",
        "huggingface_hub>=0.23.0",
        "peft>=0.11.1",
        "transformers>=4.51.0",
        "trl>=0.9.6",
        "unsloth>=2024.8",
    )
)


def build_training_script() -> str:
    return r"""
import os
import unsloth

from datasets import load_dataset
from huggingface_hub import login
from trl import SFTTrainer, SFTConfig
from unsloth import FastLanguageModel

hf_token = os.environ["HF_TOKEN"]
login(token=hf_token)

base_model = os.environ["BASE_MODEL"]
train_file = os.environ["TRAIN_FILE"]
output_dir = "/training-output"

dataset = load_dataset("json", data_files=train_file, split="train")

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=base_model,
    max_seq_length=4096,
    dtype=None,
    load_in_4bit=True,
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha=16,
    lora_dropout=0,
    bias="none",
    use_gradient_checkpointing="unsloth",
)

def format_row(row):
    return {
        "text": tokenizer.apply_chat_template(
            row["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
    }

dataset = dataset.map(format_row)

training_args = SFTConfig(
    dataset_text_field="text",
    per_device_train_batch_size=2,
    gradient_accumulation_steps=4,
    warmup_steps=10,
    num_train_epochs=2,
    learning_rate=2e-4,
    logging_steps=5,
    save_strategy="epoch",
    output_dir=output_dir,
    optim="paged_adamw_8bit",
    bf16=True,
    report_to="none",
)

trainer = SFTTrainer(
    model=model,
    processing_class=tokenizer,
    train_dataset=dataset,
    args=training_args,
)

trainer.train()
model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)
"""


@app.function(
    image=image,
    gpu="A10G",
    timeout=60 * 60 * 6,
    volumes={"/training-output": volume},
    secrets=[modal.Secret.from_name("huggingface-secret")],
)
def run_training() -> str:
    import subprocess
    import tempfile

    script = build_training_script()
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as handle:
        handle.write(script)
        temp_script = handle.name

    env = os.environ.copy()
    env["BASE_MODEL"] = BASE_MODEL
    env["TRAIN_FILE"] = VOLUME_TRAIN_FILE

    subprocess.run(["python", temp_script], check=True, env=env)
    return "Training complete."


@app.function(
    volumes={"/training-output": volume},
)
def upload_dataset(data: bytes) -> None:
    """Write the training file into the Modal volume."""
    out = Path(VOLUME_TRAIN_FILE)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    volume.commit()
    print(f"Uploaded dataset to {VOLUME_TRAIN_FILE} ({len(data)} bytes)")


@app.local_entrypoint()
def main() -> None:
    # Step 1 — upload local training file to Modal volume
    if not LOCAL_TRAIN_FILE.exists():
        raise FileNotFoundError(f"Training file not found: {LOCAL_TRAIN_FILE}")

    print(f"Uploading {LOCAL_TRAIN_FILE} to Modal volume...")
    data = LOCAL_TRAIN_FILE.read_bytes()
    upload_dataset.remote(data)
    print("Upload complete.")

    # Step 2 — run training
    print("Starting training run...")
    message = run_training.remote()
    print(message)
    print("Artifacts written to Modal volume /training-output")
    if OUTPUT_REPO and HF_USERNAME:
        print(f"Next: upload the adapter to https://huggingface.co/{OUTPUT_REPO}")
