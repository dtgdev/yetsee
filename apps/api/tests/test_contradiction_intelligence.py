from app.scientific_literature.contradiction_intelligence import classify_claim_pair


RELATIONSHIP={
    "subject":{"kind":"genomic_alteration","name":"MET amplification","key":"genomic-alteration:met-amplification"},
    "predicate":"reported_as_resistance_mechanism",
    "object":{"kind":"drug_resistance","name":"Acquired osimertinib resistance","key":"drug-resistance:osimertinib-acquired"},
}


def claim(text, relationship=None, review_status="approve"):
    return {"relationship":relationship or RELATIONSHIP,"assertion_text":text,"review_status":review_status}


def test_matching_positive_claims_are_agreement():
    result=classify_claim_pair(claim("MET amplification was reported as a resistance mechanism."),claim("Resistance mechanisms included MET amplification."))
    assert result["status"]=="reviewed_agreement"
    assert result["confidence"]==0.95


def test_matching_relation_opposite_polarity_is_direct_contradiction():
    result=classify_claim_pair(claim("MET amplification was reported as a resistance mechanism."),claim("MET amplification was not reported as a resistance mechanism."))
    assert result["status"]=="reviewed_contradiction"
    assert result["confidence"]==0.95
    assert {result["left_polarity"],result["right_polarity"]}=={"positive","negative"}


def test_different_relationships_are_not_forced_into_contradiction():
    other={
        "subject":{"kind":"genomic_alteration","name":"EGFR C797S mutation","key":"genomic-alteration:egfr-c797s-mutation"},
        "predicate":"reported_as_resistance_mechanism",
        "object":RELATIONSHIP["object"],
    }
    result=classify_claim_pair(claim("MET amplification was observed."),claim("EGFR C797S was observed.",other))
    assert result["status"]=="not_comparable"
    assert result["confidence"]==0.99


def test_negation_in_other_clause_does_not_negate_met_claim():
    text="No EGFR T790M-mediated acquired resistance are observed; most frequent resistance mechanisms are MET amplification (n = 17; 16%) and EGFR C797S mutations (n = 7; 6%)."
    result=classify_claim_pair(claim(text),claim("MET amplification was reported as a resistance mechanism."))
    assert result["status"]=="reviewed_agreement"
    assert result["left_polarity"]=="positive"
    assert result["right_polarity"]=="positive"


def test_pending_claim_makes_agreement_provisional():
    result=classify_claim_pair(
        claim("MET amplification was reported as a resistance mechanism.", review_status="approve"),
        claim("Resistance mechanisms included MET amplification.", review_status="pending"),
    )
    assert result["status"]=="provisional_agreement"
    assert result["semantic_status"]=="agreement"
    assert result["left_review_status"]=="approve"
    assert result["right_review_status"]=="pending"


def test_pending_claim_makes_opposite_polarity_provisional_tension():
    result=classify_claim_pair(
        claim("MET amplification was reported as a resistance mechanism.", review_status="approve"),
        claim("MET amplification was not reported as a resistance mechanism.", review_status="pending"),
    )
    assert result["status"]=="provisional_tension"
    assert result["semantic_status"]=="direct_contradiction"
