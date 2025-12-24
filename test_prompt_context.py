# test_prompt_context.py - Test cases for dynamic prompt focusing
"""
Tests the PromptContext concern computation against the 5 user-provided scenarios.
"""

import sys
sys.path.insert(0, '.')

from prompt_context import create_prompt_context

def test_case(name, expected_profile, email_body, email_subject="", language="it", **kwargs):
    """Run a single test case"""
    ctx = create_prompt_context(
        detected_language=language,
        is_reply=False,
        email_body=email_body,
        email_subject=email_subject,
        **kwargs
    )
    
    result = "✅" if ctx.profile == expected_profile else "❌"
    print(f"{result} Case: {name}")
    print(f"   Expected: {expected_profile} | Got: {ctx.profile}")
    print(f"   Active concerns: {', '.join(ctx.meta['active_concerns'][:5])}")
    print()
    return ctx.profile == expected_profile


if __name__ == "__main__":
    print("=" * 60)
    print("[TEST] Testing PromptContext Dynamic Focusing")
    print("=" * 60)
    print()
    
    results = []
    
    # Case 1: Siciliani (standard - no complexity)
    results.append(test_case(
        name="1. Siciliani matrimonio normale",
        expected_profile="standard",  # formatting_risk for sacrament category
        email_body="Siamo siciliani e vorremmo sposarci a Roma, nella vostra parrocchia. Di cosa c'e' bisogno?",
        email_subject="Matrimonio",
        category="sacrament",
        language="it"
    ))
    
    # Case 2: Musulmano + Cattolica (HEAVY - doctrinal + language)
    results.append(test_case(
        name="2. Musulmano + Cattolica (ES)",
        expected_profile="heavy",  # doctrinal_risk + language_safety
        email_body="Soy un musulman argelino que quiere casarse con una catolica en Roma. Necesito ayuda con los requisitos legales o religiosos para este tramite",
        email_subject="Matrimonio mixto",
        category="sacrament",
        language="es"
    ))
    
    # Case 3: Betty divorziata anglicana (HEAVY - doctrinal)
    results.append(test_case(
        name="3. Betty divorziata anglicana (EN)",
        expected_profile="heavy",  # doctrinal_risk + language_safety
        email_body="I'm Betty, I live in Leeds, and I'd like to get married in Rome. I am divorced and Anglican. How can I get married in your parish?",
        email_subject="Marriage inquiry",
        category="sacrament",
        language="en"
    ))
    
    # Case 4: Federica annullamento (HEAVY - doctrinal)
    results.append(test_case(
        name="4. Federica annullamento in corso",
        expected_profile="heavy",  # doctrinal_risk
        email_body="Vorrei sposarmi in chiesa, ma sono divorziata. Pero' c'e' la pratica di annullamento in corso. Nel frattempo non potrei sposarmi e poi si convalida?",
        email_subject="Matrimonio",
        category="sacrament",
        language="it"
    ))
    
    # Case 5: Certificato padrino (lite/standard - simple request)
    results.append(test_case(
        name="5. Certificato padrino (richiesta semplice)",
        expected_profile="standard",  # hallucination_risk due to KB presence assumed
        email_body="Quando posso passare per avere il certificato di idoneita per fare da padrino?",
        email_subject="Certificato padrino",
        category="information",
        language="it",
        kb_length=500  # small KB
    ))
    
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    
    if passed == total:
        print("[OK] All tests passed!")
    else:
        print("[WARN] Some tests failed - review expected profiles")
    print("=" * 60)
