import sys
from gliner import GLiNER

def test_gliner():
    print("Loading GLiNER model (urchade/gliner_small-v2.1)...")
    # Using a small model for fast download and execution locally
    try:
        model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    text = "Find records for trouble code P0500 and sales model ERT701 in India."
    labels = ["trouble code", "product model", "sales model", "country", "vin", "ftir no"]
    
    print(f"\nPredicting entities for text: '{text}'")
    print(f"Labels: {labels}\n")
    
    try:
        entities = model.predict_entities(text, labels, threshold=0.4)
        for entity in entities:
            print(f"Entity: {entity['text']} => Label: {entity['label']} (Confidence: {entity['score']:.2f})")
    except Exception as e:
        print(f"Error predicting entities: {e}")

if __name__ == "__main__":
    test_gliner()
