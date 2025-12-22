
import os
import sys

# Set dummy env vars to pass config validation
os.environ['GEMINI_API_KEY'] = 'dummy_key_for_testing_1234567890'
os.environ['SPREADSHEET_ID'] = 'dummy_spreadsheet_id'
os.environ['IMPERSONATE_EMAIL'] = 'test@example.com'

# Force UTF-8 for stdout
sys.stdout.reconfigure(encoding='utf-8')

import logging
from gemini_service import GeminiService
import config

def test_language_detection():
    service = GeminiService()
    
    test_cases = [
        {
            "text": "Hola, quisiera saber informacion sobre los horarios de misa.",
            "subject": "Info horarios",
            "expected": "es",
            "reason": "Basic Spanish request"
        },
        {
            "text": "Buongiorno, vorrei sapere gli orari delle messe per favore.",
            "subject": "Orari messe",
            "expected": "it",
            "reason": "Basic Italian request"
        },
        {
            "text": "Hello, I would like to know the mass schedule please.",
            "subject": "Mass schedule",
            "expected": "en",
            "reason": "Basic English request"
        },
        {
            "text": "Hola, necesito hablar con el parroco por un tema urgente.",
            "subject": "Urgente",
            "expected": "es",
            "reason": "Spanish with 'por', 'con', 'el'"
        },
        {
            "text": "Vorrei parlare con il parroco per un problema.",
            "subject": "Richiesta appuntamento",
            "expected": "it",
            "reason": "Italian with 'con', 'il', 'per'"
        },
        {
             "text": "No hablo muy bien italiano, pero quisiera confesarme.",
             "subject": "Confesion",
             "expected": "es",
             "reason": "Spanish mixture"
        },
        {
            "text": "Que tal, como estas? Quiero saber cuando es la misa.",
            "subject": "Pregunta",
            "expected": "es",
            "reason": "Spanish with non-accented 'que', 'como', 'cuando'"
        },
        {
            "text": "Sus horarios son para todos?",
            "subject": "Duda",
            "expected": "es",
            "reason": "Spanish with 'sus', 'para'"
        },
        # Ambiguous cases handled by weight
        {
            "text": "La messa per i defunti.",
            "subject": "Messa",
            "expected": "it",
            "reason": "Short Italian"
        },
         {
            "text": "La misa para los difuntos.",
            "subject": "Misa",
            "expected": "es",
            "reason": "Short Spanish"
        }
    ]
    
    print(f"\n{'='*60}")
    print(f"TESTING LANGUAGE DETECTION")
    print(f"{'='*60}")
    
    passed = 0
    failed = 0
    
    for case in test_cases:
        print(f"\nTesting: {case['reason']}")
        print(f"Input: '{case['text'][:50]}...'")
        
        detected = service._detect_email_language(case['text'], case['subject'])
        
        if detected == case['expected']:
            print(f"✅ PASS: Detected {detected}")
            passed += 1
        else:
            print(f"❌ FAIL: Expected {case['expected']}, got {detected}")
            failed += 1
            
    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{len(test_cases)} Passed")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_language_detection()
