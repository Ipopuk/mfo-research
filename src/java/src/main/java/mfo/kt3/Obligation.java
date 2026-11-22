package mfo.kt3;

import java.math.BigDecimal;

public record Obligation(String id, String applicantId, BigDecimal monthlyPayment, boolean active) {}
