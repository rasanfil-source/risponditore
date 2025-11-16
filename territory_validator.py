"""
Territory validation module for parish addresses
Verifies if an address is within parish boundaries
✅ FIXED: Complete regex patterns for address detection
"""

import re
import logging

logger = logging.getLogger(__name__)


class TerritoryValidator:
    """Validates if addresses are within parish territory"""
    
    TERRITORY = {
        'via adolfo cancani': {'tutti': True},
        'via antonio allegri da correggio': {'tutti': True},
        'via antonio gramsci': {'tutti': True},
        'via armando spadini': {'tutti': True},
        'via bartolomeo ammannati': {'tutti': True},
        'piazzale delle belle arti': {'tutti': True},
        'viale delle belle arti': {'tutti': True},
        'viale bruno buozzi': {'dispari': [109, None], 'pari': [90, None]},
        'via cardinal de luca': {'tutti': True},
        'via carlo dolci': {'tutti': True},
        'via cesare fracassini': {'dispari': [1, None]},
        'via cimabue': {'tutti': True},
        'via domenico alberto azuni': {'pari': [1, None]},
        'piazzale don giovanni minzoni': {'tutti': True},
        'via enrico chiaradia': {'tutti': True},
        'via enrico pessina': {'tutti': True},
        'via filippo lippi': {'tutti': True},
        'via flaminia': {'dispari': [109, 217], 'pari': [158, 162]},
        'lungotevere flaminio': {'tutti': [16, 38]},
        'via francesco jacovacci': {'tutti': True},
        'via giovanni vincenzo gravina': {'tutti': True},
        'via giuseppe ceracchi': {'tutti': True},
        'via giuseppe de notaris': {'tutti': True},
        'via giuseppe mangili': {'dispari': [1, None]},
        'via jacopo da ponte': {'tutti': True},
        'via luigi canina': {'tutti': True},
        'piazzale manila': {'tutti': True},
        'piazza marina': {'tutti': [24, 35]},
        'piazza della marina': {'tutti': [24, 35]},
        'piazzale miguel cervantes': {'tutti': True},
        'largo dei monti parioli': {'tutti': True},
        'via monti parioli': {'dispari': [1, 33], 'pari': [4, 62]},
        'lungotevere delle navi': {'tutti': True},
        'via omero': {'dispari': [1, None]},
        'via paolo bartolini': {'tutti': True},
        'salita dei parioli': {'pari': [1, None]},
        'via pietro da cortona': {'tutti': True},
        'via pietro paolo rubens': {'pari': [1, None]},
        'via pomarancio': {'tutti': True},
        'via sandro botticelli': {'tutti': True},
        'via sassoferrato': {'tutti': True},
        'via sebastiano conca': {'tutti': True},
        'viale tiziano': {'tutti': True},
        'via ulisse aldrovandi': {'dispari': [1, 9]},
        'via valmichi': {'dispari': [1, None]},
        'via di villa giulia': {'tutti': True},
        'piazzale di villa giulia': {'tutti': True}
    }
    
    @staticmethod
    def normalize_street_name(street: str) -> str:
        """Normalize street name for comparison"""
        normalized = street.lower().strip()
        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized
    
    @staticmethod
    def extract_address_from_text(text: str) -> tuple:
        """
        Extract street name and civic number from text
        
        ✅ FIXED: Complete patterns including "abito a"
        
        Returns: (street_name, civic_number) or (None, None)
        """
        # ✅ Pattern per indirizzi italiani (CORRETTI)
        patterns = [
            # Pattern 1: Indirizzo diretto
            # Esempio: "via Rossi 10", "viale Belle Arti n. 5"
            r'((?:via|viale|piazza|piazzale|largo|lungotevere|salita)\s+[a-zA-ZàèéìòùÀÈÉÌÒÙ]+(?:\s+[a-zA-ZàèéìòùÀÈÉÌÒÙ]+)*)\s+(?:n\.?\s*|civico\s+)?(\d+)',
            
            # Pattern 2: Con prefissi comuni
            # ✅ FIXED: "abito a" con spazio (non solo "a")
            # Esempio: "abito in via Rossi 10", "abito al viale Verdi 5", "abito a via Bianchi 3"
            r'(?:in|abito\s+in|abito\s+al|abito\s+a|al)\s+((?:via|viale|piazza|piazzale|largo|lungotevere|salita)\s+[a-zA-ZàèéìòùÀÈÉÌÒÙ]+(?:\s+[a-zA-ZàèéìòùÀÈÉÌÒÙ]+)*)\s+(?:n\.?\s*|civico\s+)?(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                street = match.group(1).strip()
                # Remove trailing "civico" if present
                street = re.sub(r'\s+civico$', '', street, flags=re.IGNORECASE).strip()
                civic = int(match.group(2))
                
                logger.debug(f"Address detected: '{street}' n. {civic}")
                return (street, civic)
        
        return (None, None)
    
    def verify_address(self, street: str, civic_number: int) -> dict:
        """
        Verify if an address is within parish territory
        
        Args:
            street: Street name (including via/viale/piazza)
            civic_number: Civic number
            
        Returns:
            dict with keys: in_parish (bool), reason (str), details (str)
        """
        street_key = self.normalize_street_name(street)
        
        # Check if street exists in territory
        if street_key not in self.TERRITORY:
            return {
                'in_parish': False,
                'reason': f"'{street}' non è nel territorio della nostra parrocchia",
                'details': 'street_not_found'
            }
        
        rules = self.TERRITORY[street_key]
        
        # Case 1: All civic numbers accepted
        if rules.get('tutti') is True:
            return {
                'in_parish': True,
                'reason': f"'{street}' è completamente nel territorio parrocchiale",
                'details': 'all_numbers'
            }
        
        # Case 2: Specific range for all numbers
        if isinstance(rules.get('tutti'), list):
            min_num, max_num = rules['tutti']
            if civic_number >= min_num and (max_num is None or civic_number <= max_num):
                range_str = f"dal {min_num} al {max_num}" if max_num else f"dal {min_num} in poi"
                return {
                    'in_parish': True,
                    'reason': f"'{street}' n. {civic_number} è nel territorio (numeri {range_str})",
                    'details': f"range_{min_num}_{max_num}"
                }
            else:
                range_str = f"dal {min_num} al {max_num}" if max_num else f"dal {min_num} in poi"
                return {
                    'in_parish': False,
                    'reason': f"'{street}' n. {civic_number} è fuori dal territorio (accettiamo solo numeri {range_str})",
                    'details': f"outside_range_{min_num}_{max_num}"
                }
        
        # Case 3: Odd/even numbers with ranges
        is_odd = civic_number % 2 == 1
        is_even = civic_number % 2 == 0
        
        if is_odd and 'dispari' in rules:
            min_num, max_num = rules['dispari']
            if civic_number >= min_num and (max_num is None or civic_number <= max_num):
                range_str = f"dal {min_num} al {max_num}" if max_num else f"dal {min_num} in poi"
                return {
                    'in_parish': True,
                    'reason': f"'{street}' n. {civic_number} è nel territorio (numeri dispari {range_str})",
                    'details': f"odd_range_{min_num}_{max_num}"
                }
        
        if is_even and 'pari' in rules:
            min_num, max_num = rules['pari']
            if civic_number >= min_num and (max_num is None or civic_number <= max_num):
                range_str = f"dal {min_num} al {max_num}" if max_num else f"dal {min_num} in poi"
                return {
                    'in_parish': True,
                    'reason': f"'{street}' n. {civic_number} è nel territorio (numeri pari {range_str})",
                    'details': f"even_range_{min_num}_{max_num}"
                }
        
        # Not in parish
        return {
            'in_parish': False,
            'reason': f"'{street}' n. {civic_number} non rientra nel territorio parrocchiale",
            'details': 'civic_not_in_range'
        }
    
    def analyze_email_for_address(self, email_content: str, email_subject: str) -> dict:
        """
        Analyze email to detect and verify addresses
        
        Returns:
            dict with keys: address_found (bool), verification (dict or None)
        """
        full_text = f"{email_subject} {email_content}"
        street, civic = self.extract_address_from_text(full_text)
        
        if street and civic:
            logger.info(f"📍 Address detected: {street} {civic}")
            verification = self.verify_address(street, civic)
            return {
                'address_found': True,
                'street': street,
                'civic': civic,
                'verification': verification
            }
        
        return {
            'address_found': False,
            'verification': None
        }


# ========================================================================
# TESTING FUNCTION
# ========================================================================

def test_territory_validator():
    """
    Test function for TerritoryValidator
    
    Run this to verify patterns work correctly
    """
    validator = TerritoryValidator()
    
    print("="*70)
    print("TESTING TERRITORY VALIDATOR - REGEX PATTERNS")
    print("="*70)
    
    test_cases = [
        # Positive cases (should detect)
        ("Abito in via Rossi 10", "via Rossi", 10),
        ("abito a via delle Belle Arti 5", "viale delle Belle Arti", 5),
        ("Abito al viale Tiziano 20", "viale Tiziano", 20),
        ("Il mio indirizzo è via Flaminia 150", "via Flaminia", 150),
        ("Vivo in piazza Marina n. 30", "piazza Marina", 30),
        
        # Negative cases (should NOT match incorrectly)
        ("La casa a via Verdi è bella", None, None),  # "a via" without "abito"
        ("Vado a via Roma domani", None, None),  # "a via" in different context
    ]
    
    print("\n✅ POSITIVE TEST CASES (should detect address):")
    for text, expected_street, expected_civic in test_cases[:5]:
        street, civic = validator.extract_address_from_text(text)
        
        if street and civic:
            status = "✓" if civic == expected_civic else "✗"
            print(f"{status} '{text}'")
            print(f"   → Detected: {street} n. {civic}")
        else:
            print(f"✗ '{text}'")
            print(f"   → NOT DETECTED (expected: {expected_street} {expected_civic})")
        print()
    
    print("\n❌ NEGATIVE TEST CASES (should NOT detect):")
    for text, _, _ in test_cases[5:]:
        street, civic = validator.extract_address_from_text(text)
        
        if street and civic:
            print(f"✗ '{text}'")
            print(f"   → INCORRECTLY DETECTED: {street} n. {civic}")
        else:
            print(f"✓ '{text}'")
            print(f"   → Correctly NOT detected")
        print()
    
    print("="*70)


if __name__ == "__main__":
    test_territory_validator()