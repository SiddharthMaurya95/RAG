import os
from gliner import GLiNER

def download_and_save_model(model_name="urchade/gliner_medium-v2.1", save_dir="models/gliner_medium"):
    print(f"Downloading model '{model_name}' from Hugging Face...")
    # Load model (downloads from Hugging Face Hub)
    model = GLiNER.from_pretrained(model_name)
    
    # Ensure local directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"Saving model to local directory: {save_dir}")
    # Save the model locally
    model.save_pretrained(save_dir)
    print("Done! You can now load this model offline.")

if __name__ == "__main__":
    download_and_save_model()
