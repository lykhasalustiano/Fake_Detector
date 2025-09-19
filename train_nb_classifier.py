# train_nb_classifier.py
#!/usr/bin/env python3
"""
Script to train the Enhanced Naive Bayes classifier for fake news detection
with n-grams features
"""

import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from naive_bayes_classifier import NaiveBayesClassifier, load_training_data
import joblib

def main():
    # Prepare training data
    csv_path = "data/WELFake_Dataset.csv"
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        print("Please make sure the WELFake_Dataset.csv file is in the data directory")
        return
    
    # Load training data
    try:
        documents, labels = load_training_data(
            csv_path, 
            text_column="text",  # Using text content for training
            label_column="label",
            max_samples=5000  # Use more samples for better accuracy
        )
        
        print(f"Loaded {len(documents)} samples for training")
        
        # Train classifiers with different configurations
        print("\n1. Training with standard features (unigrams only):")
        classifier_std = NaiveBayesClassifier(alpha=1.0, use_ngrams=False)
        classifier_std.train(documents, labels)
        
        print("2. Training with n-grams (unigrams + bigrams):")
        classifier_ngrams = NaiveBayesClassifier(alpha=1.0, use_ngrams=True)
        classifier_ngrams.train(documents, labels)
        
        # Save the best model (with n-grams)
        model_path = "models/naive_bayes_classifier.pkl"
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(classifier_ngrams, model_path)
        
        print(f"\nModel trained and saved to {model_path}")
        
        # Test with some example texts
        test_texts = [
            "Scientists confirm climate change is real and caused by human activity based on decades of research",
            "BREAKING: Secret miracle cure discovered that doctors don't want you to know about!",
            "The government announced new policies to address economic challenges through bipartisan effort",
            "SHOCKING: Alien invasion happening next week, government hiding the truth!",
            "Research shows that regular exercise and balanced diet contribute to better health outcomes",
            "URGENT: One simple trick to lose weight without diet or exercise - doctors hate this!"
        ]
        
        print("\nTesting with sample texts:")
        for text in test_texts:
            prediction_std, probabilities_std = classifier_std.predict(text)
            prediction_ng, probabilities_ng = classifier_ngrams.predict(text)
            
            result_std = "FAKE" if prediction_std == 1 else "REAL"
            result_ng = "FAKE" if prediction_ng == 1 else "REAL"
            
            fake_prob_std = probabilities_std.get(1, 0) * 100
            fake_prob_ng = probabilities_ng.get(1, 0) * 100
            
            print(f"Text: {text[:60]}...")
            print(f"Standard: {result_std} ({fake_prob_std:.1f}% fake)")
            print(f"N-grams: {result_ng} ({fake_prob_ng:.1f}% fake)")
            print("---")
            
    except Exception as e:
        print(f"Error during training: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()