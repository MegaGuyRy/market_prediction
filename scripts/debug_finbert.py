#!/usr/bin/env python
"""Debug FinBERT model outputs to understand the format"""

from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

model_name = "ProsusAI/finbert"
print(f"Loading model: {model_name}")

tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# Check model config
print(f"\nModel config:")
print(f"  Num labels: {model.config.num_labels}")
print(f"  Label names: {model.config.id2label if hasattr(model.config, 'id2label') else 'Not available'}")

# Test a simple positive sentence
text = "Apple beats earnings"
inputs = tokenizer(text, return_tensors="pt", truncation=True)

with torch.no_grad():
    outputs = model(**inputs)

logits = outputs.logits
probs = torch.softmax(logits, dim=-1)

print(f"\nTest: '{text}'")
print(f"Logits: {logits}")
print(f"Probabilities: {probs}")
print(f"Probabilities by index:")
for i, prob in enumerate(probs[0]):
    print(f"  Class {i}: {prob.item():.4f}")

# Check which class has highest probability
predicted_class = torch.argmax(probs, dim=-1)
print(f"\nPredicted class: {predicted_class.item()}")

# Try mapping
print("\nPossible mappings:")
print("  Class 0 (highest prob): Could be negative, neutral, or positive")
print("  Class 1 (middle prob): Could be negative, neutral, or positive")
print("  Class 2 (lowest prob): Could be negative, neutral, or positive")
